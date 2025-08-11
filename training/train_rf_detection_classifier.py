import argparse
import os
import random
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib
import ast


def set_all_seeds(seed: int):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def parse_box(box_str: str):
    """
    Parse stringified list of coordinates: '[[x1, y1], [x2, y2], ...]'
    Returns list of (x, y) tuples as floats.
    """
    try:
        points = ast.literal_eval(box_str)
        return [tuple(map(float, pt)) for pt in points]
    except Exception:
        return None


def load_and_prepare(path_in: Path):
    df = pd.read_csv(path_in)

    df["_box"] = df["box_points"].map(parse_box)

    # Drop rows with missing label
    df = df.dropna(subset=["is_detection"]).copy()

    # Convert is_detection to int (handles TRUE/FALSE, 1/0, etc.)
    df["is_detection"] = df["is_detection"].astype(str).str.upper().map(
        {"TRUE": 1, "FALSE": 0, "1": 1, "0": 0}).astype(int)
    # Convert orientation_mismatch to int (handles TRUE/FALSE, 1/0, etc.)
    df["orientation_mismatch"] = df["orientation_mismatch"].astype(
        str).str.upper().map({"TRUE": 1, "FALSE": 0, "1": 1, "0": 0}).astype(int)

    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", type=str, default="./data/rf-data.csv")
    ap.add_argument("--outfile_model", type=str,
                    default="./models/rf_detection_classifier.joblib")
    ap.add_argument("--outfile_features", type=str,
                    default="./models/rf_detection_classifier.txt")
    ap.add_argument("--test_size", type=float, default=0.25)
    ap.add_argument("--random_state", type=int, default=42)
    ap.add_argument("--balanced", action="store_true",
                    help="Use class_weight='balanced' in RF.")
    args = ap.parse_args()

    set_all_seeds(args.random_state)

    path_in = Path(args.infile)
    df = load_and_prepare(path_in)

    FEATURES = [
        "orientation_mismatch",
        "long_side_angle",
        "aspect_ratio",
        "corner_proximity",
        "area",
        "length",
    ]

    X = df[FEATURES].copy()
    X["orientation_mismatch"] = X["orientation_mismatch"].astype(int)
    for col in ["long_side_angle", "aspect_ratio", "corner_proximity", "area", "length"]:
        X[col] = X[col].astype(float)

    y = df["is_detection"].astype(int)

    # Simple holdout split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, stratify=y, test_size=args.test_size, random_state=args.random_state
    )

    rf = RandomForestClassifier(
        random_state=args.random_state,
        class_weight=("balanced" if args.balanced else None)
    )
    pipe = Pipeline([("scaler", StandardScaler()), ("rf", rf)])

    # tighter grid (small data)
    param_grid = {
        "rf__n_estimators": [200, 400],
        "rf__max_depth": [None, 10],
        "rf__min_samples_split": [2, 5],
        "rf__min_samples_leaf": [1, 2],
        # "rf__max_features": ["sqrt", None],  # optional
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True,
                         random_state=args.random_state)

    grid = GridSearchCV(
        pipe, param_grid, cv=cv, scoring="accuracy", n_jobs=-1, refit=True
    )
    grid.fit(X_train, y_train)

    best = grid.best_estimator_
    print("Best params:", grid.best_params_)
    print("CV accuracy (mean):", grid.best_score_)

    y_pred = best.predict(X_test)
    print("\nHoldout classification report:")
    print(classification_report(y_test, y_pred, digits=3))
    print("Holdout confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    cv_all = cross_val_score(
        best, X, y, cv=cv, scoring="accuracy", n_jobs=-1).mean()
    print("\n5-fold CV accuracy on all data (post-refit):", round(cv_all, 4))

    joblib.dump(best, args.outfile_model)
    with open(args.outfile_features, "w") as f:
        for feat in FEATURES:
            f.write(f"{feat}\n")

    print(f"\nSaved model to: {args.outfile_model}")
    print(f"Saved feature list to: {args.outfile_features}")


if __name__ == "__main__":
    main()
