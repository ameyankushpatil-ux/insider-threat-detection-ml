import sys
import json
import time
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    RESULTS_DIR,
    TABLES_DIR,
    PREDICTIONS_DIR,
    RANDOM_STATE,
)

TRAIN_FILE = PROCESSED_DATA_DIR / "train_scaled.csv"
TEST_FILE = PROCESSED_DATA_DIR / "test_scaled.csv"

OCSVM_SAMPLE_SIZE = 10000
OCSVM_BATCH_SIZE = 5000
CONTAMINATION = 0.01
N_ESTIMATORS = 300


def score_in_batches(model, X, batch_size):
    """Score a dataset in batches to control memory usage."""
    scores = []

    for start in range(0, len(X), batch_size):
        end = min(start + batch_size, len(X))
        batch = X[start:end]

        scores.extend(
            -model.decision_function(batch)
        )

        print(f"  Scored {end:,} / {len(X):,} records")

    return np.asarray(scores)


def main():
    print("=" * 75)
    print("STEP 06: UNSUPERVISED ANOMALY MODEL TRAINING")
    print("=" * 75)

    start_time = time.time()

    if not TRAIN_FILE.exists() or not TEST_FILE.exists():
        raise FileNotFoundError(
            "Training or testing dataset not found. Run Step 05 first."
        )

    train = pd.read_csv(TRAIN_FILE, low_memory=False)
    test = pd.read_csv(TEST_FILE, low_memory=False)

    metadata = ["user", "date_only"]
    features = [c for c in train.columns if c not in metadata]

    if features != [c for c in test.columns if c not in metadata]:
        raise ValueError("Training and testing feature columns differ.")

    X_train = train[features].to_numpy(dtype=np.float64)
    X_test = test[features].to_numpy(dtype=np.float64)

    if not np.isfinite(X_train).all() or not np.isfinite(X_test).all():
        raise ValueError("Non-finite values found in model inputs.")

    print(f"\nTraining records: {len(train):,}")
    print(f"Testing records: {len(test):,}")
    print(f"Features: {len(features)}")

    # ---------------------------------------------------------
    # MODEL 1: ISOLATION FOREST
    # ---------------------------------------------------------
    print("\n[1] TRAINING ISOLATION FOREST")

    isolation_forest = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    isolation_forest.fit(X_train)

    print("Isolation Forest training completed.")

    iso_test_prediction = isolation_forest.predict(X_test)
    iso_test_score = -isolation_forest.decision_function(X_test)

    iso_model_path = MODELS_DIR / "isolation_forest.joblib"
    joblib.dump(isolation_forest, iso_model_path)

    # ---------------------------------------------------------
    # MODEL 2: ONE-CLASS SVM
    # ---------------------------------------------------------
    print("\n[2] TRAINING ONE-CLASS SVM")

    rng = np.random.default_rng(RANDOM_STATE)

    sample_size = min(OCSVM_SAMPLE_SIZE, len(X_train))

    sample_indices = rng.choice(
        len(X_train),
        size=sample_size,
        replace=False,
    )

    X_ocsvm_train = X_train[sample_indices]

    print(f"OCSVM training sample: {sample_size:,}")

    one_class_svm = OneClassSVM(
        kernel="rbf",
        gamma="scale",
        nu=CONTAMINATION,
        cache_size=1024,
    )

    one_class_svm.fit(X_ocsvm_train)

    print("One-Class SVM training completed.")

    ocsvm_sample_prediction = one_class_svm.predict(
        X_ocsvm_train
    )

    ocsvm_test_prediction = []

    print("\nScoring testing dataset in batches:")

    for start in range(0, len(X_test), OCSVM_BATCH_SIZE):
        end = min(start + OCSVM_BATCH_SIZE, len(X_test))

        batch = X_test[start:end]

        ocsvm_test_prediction.extend(
            one_class_svm.predict(batch)
        )

        print(f"  Predicted {end:,} / {len(X_test):,} records")

    ocsvm_test_prediction = np.asarray(
        ocsvm_test_prediction
    )

    ocsvm_test_score = score_in_batches(
        one_class_svm,
        X_test,
        OCSVM_BATCH_SIZE,
    )

    ocsvm_model_path = MODELS_DIR / "one_class_svm.joblib"
    joblib.dump(one_class_svm, ocsvm_model_path)

    # ---------------------------------------------------------
    # SAVE TEST PREDICTIONS
    # ---------------------------------------------------------
    print("\n[3] SAVING TEST PREDICTIONS")

    predictions = test[metadata].copy()

    predictions["isolation_forest_prediction"] = (
        iso_test_prediction
    )

    predictions["isolation_forest_anomaly"] = (
        iso_test_prediction == -1
    ).astype(int)

    predictions["isolation_forest_score"] = (
        iso_test_score
    )

    predictions["ocsvm_prediction"] = (
        ocsvm_test_prediction
    )

    predictions["ocsvm_anomaly"] = (
        ocsvm_test_prediction == -1
    ).astype(int)

    predictions["ocsvm_score"] = (
        ocsvm_test_score
    )

    prediction_path = (
        PREDICTIONS_DIR / "test_model_predictions.csv"
    )

    predictions.to_csv(prediction_path, index=False)

    # ---------------------------------------------------------
    # DESCRIPTIVE MODEL RESULTS
    # ---------------------------------------------------------
    iso_count = int(
        predictions["isolation_forest_anomaly"].sum()
    )

    ocsvm_count = int(
        predictions["ocsvm_anomaly"].sum()
    )

    both_count = int(
        (
            (predictions["isolation_forest_anomaly"] == 1)
            & (predictions["ocsvm_anomaly"] == 1)
        ).sum()
    )

    metrics = {
        "training_records": int(len(train)),
        "testing_records": int(len(test)),
        "feature_count": len(features),
        "isolation_forest": {
            "n_estimators": N_ESTIMATORS,
            "contamination": CONTAMINATION,
            "training_scope": "Full chronological training partition",
            "test_anomalies": iso_count,
            "test_anomaly_percentage": round(
                iso_count / len(test) * 100, 4
            ),
        },
        "one_class_svm": {
            "kernel": "rbf",
            "gamma": "scale",
            "nu": CONTAMINATION,
            "training_scope": "Random sample from training partition",
            "training_sample_size": int(sample_size),
            "training_sample_anomalies": int(
                (ocsvm_sample_prediction == -1).sum()
            ),
            "test_anomalies": ocsvm_count,
            "test_anomaly_percentage": round(
                ocsvm_count / len(test) * 100, 4
            ),
        },
        "both_models_flagged": both_count,
        "both_models_flagged_percentage": round(
            both_count / len(test) * 100, 4
        ),
        "score_definition": (
            "Negative decision_function; higher values indicate "
            "greater anomaly score."
        ),
        "random_state": RANDOM_STATE,
    }

    metrics_path = TABLES_DIR / "model_training_summary.json"

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)

    # ---------------------------------------------------------
    # CONSOLE SUMMARY
    # ---------------------------------------------------------
    print("\n[4] TEST-PERIOD RESULTS")

    print(
        f"Isolation Forest anomalies: {iso_count:,} "
        f"({iso_count / len(test) * 100:.2f}%)"
    )

    print(
        f"One-Class SVM anomalies: {ocsvm_count:,} "
        f"({ocsvm_count / len(test) * 100:.2f}%)"
    )

    print(
        f"Both models flagged: {both_count:,} "
        f"({both_count / len(test) * 100:.2f}%)"
    )

    print("\n[5] SAVED ARTIFACTS")
    print(iso_model_path)
    print(ocsvm_model_path)
    print(prediction_path)
    print(metrics_path)

    print(
        f"\nElapsed time: {(time.time() - start_time) / 60:.2f} minutes"
    )

    print("\nSTEP 06 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
