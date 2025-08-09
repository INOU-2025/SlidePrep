import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib


def parse_box(box_str: str):
    """
    Parse 'x1, y1|x2, y2|x3, y3|x4, y4' -> [(x1,y1),...,(x4,y4)] as floats.
    Returns None if parsing fails.
    """
    if not isinstance(box_str, str) or "|" not in box_str:
        return None
    try:
        return [tuple(map(float, pair.strip().split(","))) for pair in box_str.split("|")]
    except Exception:
        return None

def parse_min_area_rect(rect_str: str):
    """
    Parse string like '((cx, cy), (w, h), angle)' to tuple.
    Returns None if parsing fails.
    """
    try:
        # Remove outer quotes and parentheses
        rect_str = rect_str.strip().replace('"', '')
        # Split into three parts
        parts = rect_str.split('), (')
        if len(parts) != 2 and len(parts) != 3:
            return None
        # First part: center
        center = tuple(map(float, parts[0].replace('(', '').split(',')))
        # Second part: size
        size_angle = parts[1].split('), ')
        size = tuple(map(float, size_angle[0].replace('(', '').split(',')))
        # Third part: angle
        angle = float(size_angle[1].replace(')', '')) if len(size_angle) > 1 else float(parts[2].replace(')', ''))
        return (center, size, angle)
    except Exception:
        return None

def load_and_prepare(path_in: Path):
    # Load CSV instead of Excel
    df = pd.read_csv(path_in)

    # Parse box_points column (string to list of tuples)
    df["_box"] = df["box_points"].map(parse_box)

    # Use is_detection column (boolean) as label
    df["is_detection"] = df["is_detection"].astype(float)

    # Drop rows with missing label
    df = df.dropna(subset=["is_detection"]).copy()

    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", type=str, default="detection_analysis.csv")
    ap.add_argument("--outfile_model", type=str, default="rf_detector_model.joblib")
    ap.add_argument("--outfile_features", type=str, default="rf_detector_features.txt")
    ap.add_argument("--test_size", type=float, default=0.25)
    ap.add_argument("--random_state", type=int, default=42)
    args = ap.parse_args()

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

    X = df[FEATURES].astype(float)
    y = df["is_detection"].astype(int)

    # Simple holdout split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, stratify=y, test_size=args.test_size, random_state=args.random_state
    )

    # Pipeline: scale + RF
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestClassifier(random_state=args.random_state))
    ])

    # Modest hyperparameter search (expand if you want)
    param_grid = {
        "rf__n_estimators": [100, 200, 400],
        "rf__max_depth": [None, 5, 10],
        "rf__min_samples_split": [2, 5],
        "rf__min_samples_leaf": [1, 2],
    }

    grid = GridSearchCV(
        pipe, param_grid, cv=5, scoring="accuracy", n_jobs=-1, refit=True
    )
    grid.fit(X_train, y_train)

    best = grid.best_estimator_
    print("Best params:", grid.best_params_)
    print("CV accuracy (mean):", grid.best_score_)

    # Evaluate on holdout
    y_pred = best.predict(X_test)
    print("\nHoldout classification report:")
    print(classification_report(y_test, y_pred, digits=3))
    print("Holdout confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Optional: cross-validated accuracy on all data with best model
    cv_all = cross_val_score(best, X, y, cv=5, scoring="accuracy", n_jobs=-1).mean()
    print("\n5-fold CV accuracy on all data (post-refit):", round(cv_all, 4))

    # Save model + features
    joblib.dump(best, args.outfile_model)
    with open(args.outfile_features, "w") as f:
        for feat in FEATURES:
            f.write(f"{feat}\n")

    print(f"\nSaved model to: {args.outfile_model}")
    print(f"Saved feature list to: {args.outfile_features}")

if __name__ == "__main__":
    main()