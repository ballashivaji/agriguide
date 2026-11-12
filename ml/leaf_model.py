"""
Leaf photo -> disease prediction for AgriGuide.

Two modes (chosen automatically):

1. TRAINED MODE  - if models/leaf_disease.joblib exists (created by
   train_model.py from a PlantVillage-style image folder) a RandomForest
   classifier predicts the disease class from the photo.

2. QUICK-SCAN MODE - if no trained model file exists, a colour/shape image
   analysis detects visible symptoms (yellowing, brown spots, yellow stripes,
   wilting/dry patches) and maps them to the symptoms in the diseases table.
   This is a heuristic, NOT a trained classifier - treat results as a hint.
"""
import os
import warnings

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import color, measure, morphology

warnings.filterwarnings("ignore", category=FutureWarning, module="skimage")
warnings.filterwarnings("ignore", category=FutureWarning, module="ml")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "leaf_disease.joblib")
IMG_SIZE = 192
_model_cache = {}


def load_image(file_or_path):
    img = Image.open(file_or_path).convert("RGB")
    img.thumbnail((IMG_SIZE, IMG_SIZE))
    return np.asarray(img.resize((IMG_SIZE, IMG_SIZE)), dtype=np.float32) / 255.0


def _masks(rgb):
    """Return hsv image + boolean masks (leaf, green, yellow, brown, dark)."""
    hsv = color.rgb2hsv(rgb)
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    # Background = very bright & unsaturated (white paper) or very dark.
    leaf = (s > 0.18) & (v > 0.12)
    leaf = morphology.remove_small_objects(leaf, 80)
    green = leaf & (h >= 70) & (h < 170)
    yellow = leaf & (h >= 38) & (h < 70) & (v > 0.45)
    brown = leaf & (h >= 5) & (h < 38) & (v < 0.75)
    dark = leaf & (v < 0.28)
    return hsv, leaf, green, yellow, brown, dark


def extract_features(rgb):
    """Fixed-length feature vector used for trained mode."""
    hsv, leaf, green, yellow, brown, dark = _masks(rgb)
    n = max(leaf.sum(), 1)
    feats = [green.sum() / n, yellow.sum() / n, brown.sum() / n, dark.sum() / n,
             leaf.mean()]
    for ch, bins in ((0, 18), (1, 8), (2, 8)):
        vals = hsv[..., ch][leaf] if leaf.any() else hsv[..., ch].ravel()
        hist, _ = np.histogram(vals, bins=bins, range=(0, 1), density=False)
        feats.extend(hist / max(hist.sum(), 1))
    spots = brown | dark
    lab = measure.label(spots)
    props = measure.regionprops(lab)
    areas = [p.area for p in props if p.area >= 6]
    feats.extend([len(areas) / 50.0, (np.mean(areas) / n) if areas else 0.0,
                  (max(areas) / n) if areas else 0.0])
    gray = color.rgb2gray(rgb)
    feats.extend([gray[leaf].std() if leaf.any() else 0.0])
    return np.array(feats, dtype=np.float32)


# ---------------------------------------------------------------- quick scan
def quick_scan(rgb):
    """Heuristic symptom detection. Returns dict with symptom + confidence."""
    hsv, leaf, green, yellow, brown, dark = _masks(rgb)
    n = leaf.sum()
    if n < 400:
        return {"label": None, "confidence": 0.0, "mode": "quick-scan",
                "note": "No clear leaf found. Use a close, well-lit photo of a single leaf on a plain background."}
    g, y, b, d = (m.sum() / n for m in (green, yellow, brown, dark))
    spots = (brown | dark) & ~ndi.binary_dilation(~leaf, morphology.disk(2))
    spots = morphology.remove_small_objects(spots, 6)
    sp = measure.regionprops(measure.label(spots))
    n_spots = len(sp)
    spot_frac = spots.sum() / n
    ylab = measure.regionprops(measure.label(morphology.remove_small_objects(yellow, 25)))
    elong = [p for p in ylab if p.area > 40 and p.axis_minor_length > 0
             and p.axis_major_length / p.axis_minor_length > 3.0]
    scores = {
        "Yellow Leaves": min(1.0, y * 2.2) if not elong else y * 0.8,
        "Yellow Stripes": min(1.0, 0.45 + len(elong) * 0.12) if len(elong) >= 2 and y > 0.04 else 0.0,
        "Brown Spots": min(1.0, spot_frac * 9) if n_spots >= 3 else 0.0,
        "Leaf Blast Spots": min(1.0, spot_frac * 6) if 1 <= n_spots < 3 and spot_frac > 0.02 else 0.0,
        "Wilting": min(1.0, (b + d) * 1.6) if spot_frac > 0.25 and n_spots < 3 else 0.0,
    }
    issue = max(scores.values())
    # Healthy wins only when no symptom score is meaningful.
    scores["Healthy"] = max(0.0, min(1.0, g)) if issue < 0.2 else max(0.0, 0.4 - issue)
    label = max(scores, key=scores.get)
    top = scores[label]
    total = sum(scores.values()) or 1.0
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    return {
        "label": label, "confidence": round(float(min(0.95, 0.35 + 0.6 * top / max(total, top))) * 100, 1),
        "mode": "quick-scan",
        "alternatives": [(k, round(v / total * 100, 1)) for k, v in ranked[1:3] if v > 0],
        "stats": {"green": round(g * 100), "yellow": round(y * 100), "brown": round(b * 100),
                  "dark": round(d * 100), "spots": n_spots},
    }


# -------------------------------------------------------------- trained mode
def _load_model():
    if "m" not in _model_cache:
        if os.path.exists(MODEL_PATH):
            import joblib
            _model_cache["m"] = joblib.load(MODEL_PATH)
        else:
            _model_cache["m"] = None
    return _model_cache["m"]


def predict(file_or_path):
    rgb = load_image(file_or_path)
    bundle = _load_model()
    if bundle is None:
        return quick_scan(rgb)
    clf, classes = bundle["clf"], bundle["classes"]
    proba = clf.predict_proba(extract_features(rgb)[None, :])[0]
    order = np.argsort(proba)[::-1]
    return {
        "label": classes[order[0]], "confidence": round(float(proba[order[0]]) * 100, 1),
        "mode": "trained",
        "alternatives": [(classes[i], round(float(proba[i]) * 100, 1)) for i in order[1:3] if proba[i] > 0.01],
    }
