"""
Leaf photo -> disease prediction pipeline for AgriGuide.

Pipeline (each step can reject the image):

  1. Open + sanitise the image (EXIF rotation, size limit).
  2. COLOUR GATE   - a cheap check that the picture contains plant-coloured pixels.
                     (A red/white logo has almost none, so it is rejected here.)
  3. CLIP GATE     - zero-shot "is this a plant leaf?" with OpenAI CLIP (pre-trained).
                     Rejects logos, screenshots, people, animals, objects, etc.
  4. CLASSIFIERS   - a small "model zoo" of pre-trained image classifiers (all CPU-friendly):
                       a) MobileNetV2 on PlantVillage, 38 classes, 14 crops (tomato, potato, apple, ...)
                       b) ViT-tiny on rice / wheat / corn / potato field images (5.5 M params)
                       c) any extra Hugging Face models listed in AGRI_EXTRA_MODELS
                     * if the user picked a crop, only models/classes for that crop are used
                     * without a crop, the most confident model wins
                     * flip test-time-augmentation
                     * low confidence -> "not sure, retake photo" instead of a guess
  5. If torch/transformers or the model files are unavailable, falls back to the
     older colour-based quick scan (clearly labelled as a rough hint).

Models are downloaded from Hugging Face on first use (~10 MB classifier,
~600 MB CLIP) and cached in ~/.cache/huggingface. Run `python download_models.py`
once to pre-fetch them.

Environment variables:
    AGRI_MODEL_ID        PlantVillage classifier (default linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification)
    AGRI_CROP_MODEL_ID   rice/wheat/corn/potato ViT (default wambugu71/crop_leaf_diseases_vit)
    AGRI_EXTRA_MODELS    comma-separated extra Hugging Face image-classification repos, e.g. a cotton model
    AGRI_USE_CLIP   "0" to disable the CLIP gate (saves ~600 MB, colour gate only)
    AGRI_MIN_CONF   minimum classifier confidence, default 0.55
"""
import io
import os
import threading

import numpy as np
from PIL import Image, ImageOps

from .knowledge import SUPPORTED_CROPS, find_crop, parse_label

MODEL_ID = os.environ.get("AGRI_MODEL_ID", "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification")
CROP_MODEL_ID = os.environ.get("AGRI_CROP_MODEL_ID", "wambugu71/crop_leaf_diseases_vit")
EXTRA_MODEL_IDS = [m.strip() for m in os.environ.get("AGRI_EXTRA_MODELS", "").split(",") if m.strip()]
MODEL_IDS = [MODEL_ID, CROP_MODEL_ID] + EXTRA_MODEL_IDS
CLIP_ID = os.environ.get("AGRI_CLIP_ID", "openai/clip-vit-base-patch32")
USE_CLIP = os.environ.get("AGRI_USE_CLIP", "1") != "0"
MIN_CONF = float(os.environ.get("AGRI_MIN_CONF", "0.55"))
SURE_CONF = 0.75
CLIP_THRESHOLD = 0.5
PLANT_PIXEL_MIN = 0.10

_lock = threading.Lock()
_state = {"models": {}, "errors": {}, "clip": None, "clip_err": None}

CLIP_POSITIVE = [
    "a close-up photo of a plant leaf",
    "a photo of a diseased plant leaf",
    "a photo of a green leaf with spots",
    "a photo of a crop plant",
]
CLIP_NEGATIVE = [
    "a logo or icon", "a screenshot of an app or website", "a cartoon or illustration",
    "a photo of a person", "a photo of an animal", "a photo of a building",
    "a photo of food on a plate", "a photo of a document with text", "a photo of a vehicle",
    "a photo of a room interior", "a photo of an everyday object", "a photo of the sky",
]


# ------------------------------------------------------------------- image io
def open_image(file_or_bytes):
    if isinstance(file_or_bytes, (bytes, bytearray)):
        file_or_bytes = io.BytesIO(file_or_bytes)
    img = Image.open(file_or_bytes)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):  # flatten transparency onto white
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("RGB")
    img.thumbnail((1024, 1024))
    return img


# ---------------------------------------------------------------- colour gate
def plant_pixel_fraction(img):
    """Fraction of pixels with green / yellow-green / yellow-brown leaf colours."""
    small = img.resize((128, 128))
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360.0 / 255.0
    s, v = hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    plant = (h >= 20) & (h <= 170) & (s > 0.20) & (v > 0.15)
    return float(plant.mean())


# ------------------------------------------------------------------ CLIP gate
def _load_clip():
    with _lock:
        if _state["clip"] is None and _state["clip_err"] is None:
            try:
                from transformers import CLIPModel, CLIPProcessor
                _state["clip"] = (CLIPProcessor.from_pretrained(CLIP_ID), CLIPModel.from_pretrained(CLIP_ID).eval())
            except Exception as e:  # missing library, offline, etc.
                _state["clip_err"] = str(e)
    return _state["clip"]


def clip_leaf_score(img):
    """Probability (0-1) that the image is a plant leaf, or None if CLIP is unavailable."""
    if not USE_CLIP:
        return None
    bundle = _load_clip()
    if bundle is None:
        return None
    import torch
    proc, model = bundle
    texts = CLIP_POSITIVE + CLIP_NEGATIVE
    inputs = proc(text=texts, images=img, return_tensors="pt", padding=True)
    with torch.no_grad():
        probs = model(**inputs).logits_per_image.softmax(dim=1)[0]
    return float(probs[: len(CLIP_POSITIVE)].sum())


# ----------------------------------------------------------------- classifiers
def _load_model(model_id):
    """Load one Hugging Face image-classification model (cached). Returns bundle or None."""
    with _lock:
        if model_id in _state["models"]:
            return _state["models"][model_id]
        if model_id in _state["errors"]:
            return None
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification
            proc = AutoImageProcessor.from_pretrained(model_id)
            model = AutoModelForImageClassification.from_pretrained(model_id).eval()
            labels = [str(model.config.id2label[i]) for i in range(len(model.config.id2label))]
            bundle = {
                "id": model_id, "proc": proc, "model": model, "labels": labels,
                "crops": [parse_label(l)["crop"] for l in labels],
                # labels like "Invalid" / "Unknown" / "Background" are not real classes
                "skip": {i for i, l in enumerate(labels) if l.strip().lower() in ("invalid", "unknown", "background", "other", "none")},
            }
            _state["models"][model_id] = bundle
            return bundle
        except Exception as e:  # missing library, offline, bad repo id...
            _state["errors"][model_id] = str(e)
            return None


def classify_all(img):
    """Run every available model. Returns list of dicts with probs/labels/crops/skip/id."""
    out = []
    for mid in MODEL_IDS:
        b = _load_model(mid)
        if b is None:
            continue
        import torch
        batch = b["proc"](images=[img, ImageOps.mirror(img)], return_tensors="pt")  # original + flipped
        with torch.no_grad():
            probs = b["model"](**batch).logits.softmax(dim=1).mean(dim=0).numpy()
        out.append({**{k: b[k] for k in ("id", "labels", "crops", "skip")}, "probs": probs})
    return out


def covered_crops():
    """Crops the loaded/built-in models can recognise."""
    crops = set(SUPPORTED_CROPS)
    for b in _state["models"].values():
        crops |= {c for c in b["crops"] if c}
    return sorted(crops)


def models_status():
    """Used by the app to tell the user which models are active."""
    return {"loaded": list(_state["models"]), "errors": _state["errors"], "configured": MODEL_IDS,
            "clip_ok": _state["clip"] is not None, "clip_error": _state["clip_err"],
            "crops": covered_crops()}


def _evaluate(r, hint):
    """Score one model for this image. Returns dict or None if the model can't speak about `hint`."""
    probs, labels, crops, skip = r["probs"], r["labels"], r["crops"], r["skip"]
    valid = [i for i in range(len(labels)) if i not in skip]
    if hint:
        idx = [i for i in valid if crops[i] == hint]
        if not idx:
            return None                          # this model doesn't know that crop
        mass = float(probs[idx].sum())
        p = np.zeros_like(probs)
        if mass > 0:
            p[idx] = probs[idx] / mass
    else:
        mass = 1.0
        p = np.zeros_like(probs)
        p[valid] = probs[valid]                  # raw probs: "Invalid" mass lowers confidence
    order = [i for i in np.argsort(p)[::-1] if i in valid]
    best = order[0]
    masked = probs.copy()
    masked[list(skip)] = -1.0
    seen = crops[int(np.argmax(masked))]
    return {"id": r["id"], "labels": labels, "p": p, "order": order, "best": best,
            "conf": float(p[best]), "mass": mass, "seen_crop": seen}


def _fmt(label, p):
    parsed = parse_label(label)
    return {"label": label, "display": parsed["display"], "percent": round(float(p) * 100, 1)}


# ---------------------------------------------------------------- main entry
def analyze(file_or_bytes, crop_hint=""):
    """
    Returns dict: status in {ok, not_leaf, uncertain, crop_mismatch, unsupported_crop, error}
    plus message, mode, confidence, parsed (crop/disease/info), top (top-3 list), checks.
    """
    out = {"status": "ok", "message": "", "mode": None, "confidence": 0.0, "parsed": None,
           "top": [], "checks": {}}
    try:
        img = open_image(file_or_bytes)
    except Exception:
        out.update(status="error", message="Could not read that file. Please upload a JPG or PNG photo.")
        return out

    # 2. colour gate ---------------------------------------------------------
    frac = plant_pixel_fraction(img)
    out["checks"]["plant_pixels"] = round(frac * 100, 1)
    if frac < PLANT_PIXEL_MIN:
        out.update(status="not_leaf", message=(
            "This doesn't look like a plant leaf (almost no leaf-coloured pixels). "
            "Please upload a close, well-lit photo of a single leaf."))
        return out

    # 3. CLIP gate -----------------------------------------------------------
    leaf = clip_leaf_score(img)
    if leaf is not None:
        out["checks"]["leaf_score"] = round(leaf * 100, 1)
        if leaf < CLIP_THRESHOLD:
            out.update(status="not_leaf", message=(
                "This image doesn't appear to be a plant leaf (it looks like a logo, screenshot, "
                "person or other object). Please upload a clear photo of a crop leaf."))
            return out
    out["checks"]["leaf_check"] = "CLIP + colour" if leaf is not None else "colour only"

    # 4. pre-trained classifiers --------------------------------------------
    crop_hint = (crop_hint or "").strip()
    hint_key = find_crop(crop_hint) if crop_hint else None
    if crop_hint and (hint_key is None or hint_key not in covered_crops()):
        out.update(status="unsupported_crop", message=(
            f"No installed AI model covers {crop_hint} yet. Covered crops: {', '.join(covered_crops())}. "
            f"Use the symptom checker below, or add a {crop_hint} model with AGRI_EXTRA_MODELS (see README)."))
        return out

    results = classify_all(img)
    evals = [e for e in (_evaluate(r, hint_key) for r in results) if e]
    if evals:
        if hint_key:
            ok = [e for e in evals if e["mass"] >= 0.25]
            if not ok:
                best_seen = max(evals, key=lambda e: e["mass"])
                other = max(results, key=lambda r: float(r["probs"].max()))
                seen = _evaluate(other, None)["seen_crop"] or "another plant"
                out.update(status="crop_mismatch", mode="pretrained", message=(
                    f"The models think this looks more like {seen} than {hint_key}. "
                    f"Check the crop selection or upload a clearer {hint_key} leaf."))
                out["top"] = [_fmt(best_seen["labels"][i], best_seen["p"][i]) for i in best_seen["order"][:3]]
                return out
            chosen = max(ok, key=lambda e: e["conf"])
        else:
            chosen = max(evals, key=lambda e: e["conf"])
        conf = chosen["conf"]
        labels, p, order = chosen["labels"], chosen["p"], chosen["order"]
        out.update(mode="pretrained", confidence=round(conf * 100, 1), parsed=parse_label(labels[chosen["best"]]),
                   model=chosen["id"], models_used=len(evals),
                   top=[_fmt(labels[i], p[i]) for i in order[:3] if p[i] >= 0.01])
        # do two models agree? (same crop + same disease name)
        others = [e for e in evals if e is not chosen]
        agree = [e for e in others
                 if parse_label(e["labels"][e["best"]])["display"] == out["parsed"]["display"]]
        if agree:
            out["checks"]["agreement"] = f"{len(agree) + 1} models agree"
        if conf < MIN_CONF:
            out.update(status="uncertain", message=(
                "The models aren't confident about this photo. Retake it closer, in daylight, with the "
                "affected part of one leaf in focus and a plain background. If you know the crop, select it above."))
        elif conf < SURE_CONF and not agree:
            out["message"] = "Moderate confidence - compare with the other possibilities and confirm with an expert."
        return out

    # 5. fallbacks -----------------------------------------------------------
    from .leaf_model import predict as legacy_predict
    legacy = legacy_predict(io.BytesIO(_to_png_bytes(img)))
    if not legacy.get("label"):
        out.update(status="not_leaf", message=legacy.get("note", "No clear leaf found."))
        return out
    out.update(mode=legacy["mode"], confidence=legacy["confidence"],
               top=[{"label": legacy["label"], "display": legacy["label"], "percent": legacy["confidence"]}] +
                   [{"label": n, "display": n, "percent": p} for n, p in legacy.get("alternatives", [])])
    if legacy["mode"] == "trained":
        out["parsed"] = parse_label(legacy["label"])
    else:
        out["symptom"] = legacy["label"]
        out["message"] = ("The AI model is not installed, so this is only a rough colour check. "
                          "Run: pip install -r requirements.txt  then restart for accurate results.")
    return out


def _to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
