"""
Pre-download the AI models so the first photo scan is fast.

    python download_models.py

Needs internet once. Files are cached in ~/.cache/huggingface.
"""
from ml.predictor import CLIP_ID, MODEL_IDS, USE_CLIP

from transformers import AutoImageProcessor, AutoModelForImageClassification

for mid in MODEL_IDS:
    print("Downloading plant-disease classifier:", mid)
    try:
        AutoImageProcessor.from_pretrained(mid)
        AutoModelForImageClassification.from_pretrained(mid)
    except Exception as e:
        print("  FAILED:", e)

if USE_CLIP:
    from transformers import CLIPModel, CLIPProcessor
    print("Downloading leaf/non-leaf checker (CLIP, ~600 MB):", CLIP_ID)
    CLIPProcessor.from_pretrained(CLIP_ID)
    CLIPModel.from_pretrained(CLIP_ID)
print("Done. Start the app with: python app.py")
