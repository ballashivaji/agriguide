"""
Train the leaf-disease classifier used by the Disease page.

Usage:
    pip install scikit-learn scikit-image pillow joblib numpy
    python train_model.py path/to/dataset

The dataset folder must contain one sub-folder per class, each full of leaf
photos, e.g. the free PlantVillage dataset
(https://github.com/spMohanty/PlantVillage-Dataset  ->  raw/color):

    dataset/Tomato___Early_blight/*.jpg
    dataset/Tomato___healthy/*.jpg
    dataset/Rice___Leaf_blast/*.jpg ...

Creates models/leaf_disease.joblib. Restart the app and it switches to
trained mode automatically.
"""
import os
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from ml.leaf_model import MODEL_PATH, extract_features, load_image

MAX_PER_CLASS = 400  # keeps training fast; raise for better accuracy


def main(root):
    X, y = [], []
    classes = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    for c in classes:
        files = [f for f in os.listdir(os.path.join(root, c))
                 if f.lower().endswith((".jpg", ".jpeg", ".png"))][:MAX_PER_CLASS]
        print(f"{c}: {len(files)} images")
        for f in files:
            try:
                X.append(extract_features(load_image(os.path.join(root, c, f))))
                y.append(c)
            except Exception as e:
                print("  skipped", f, e)
    X, y = np.array(X), np.array(y)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    clf = RandomForestClassifier(n_estimators=300, n_jobs=-1, class_weight="balanced", random_state=42)
    clf.fit(Xtr, ytr)
    print(classification_report(yte, clf.predict(Xte)))
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"clf": clf, "classes": list(clf.classes_)}, MODEL_PATH)
    print("Saved", MODEL_PATH)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
