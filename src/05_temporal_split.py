import sys
import json
import joblib
import pandas as pd

from pathlib import Path
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PROCESSED_DATA_DIR,
    TABLES_DIR,
    MODELS_DIR,
    REPORTS_DIR,
    RANDOM_STATE,
)

INPUT_FILE = (
    PROCESSED_DATA_DIR /
    "user_day_model_features_log1p.csv"
)

TRAIN_RATIO = 0.80

METADATA = ["user", "date_only"]


def main():
    print("=" * 75)
    print("STEP 05: CHRONOLOGICAL TRAIN/TEST SPLIT")
    print("=" * 75)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE, low_memory=False)

    df["date_only"] = pd.to_datetime(
        df["date_only"],
        errors="raise"
    )

    feature_columns = [
        col for col in df.columns
        if col not in METADATA
    ]

    if len(feature_columns) != 20:
        raise ValueError(
            f"Expected 20 features, found {len(feature_columns)}"
        )

    df = df.sort_values(
        ["date_only", "user"]
    ).reset_index(drop=True)

    # Split on unique dates, not individual rows.
    unique_dates = sorted(df["date_only"].unique())

    split_index = int(len(unique_dates) * TRAIN_RATIO)

    if split_index <= 0 or split_index >= len(unique_dates):
        raise ValueError("Invalid chronological split index.")

    train_dates = unique_dates[:split_index]
    test_dates = unique_dates[split_index:]

    train_end = pd.Timestamp(train_dates[-1])
    test_start = pd.Timestamp(test_dates[0])

    train_df = df[df["date_only"].isin(train_dates)].copy()
    test_df = df[df["date_only"].isin(test_dates)].copy()

    # Confirm there is no temporal overlap.
    if train_df["date_only"].max() >= test_df["date_only"].min():
        raise ValueError("Temporal overlap detected.")

    X_train = train_df[feature_columns].astype("float64")
    X_test = test_df[feature_columns].astype("float64")

    # Fit scaler on training data only.
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Preserve metadata in the scaled outputs.
    train_scaled = train_df[METADATA].reset_index(drop=True)
    test_scaled = test_df[METADATA].reset_index(drop=True)

    train_scaled = pd.concat(
        [
            train_scaled,
            pd.DataFrame(
                X_train_scaled,
                columns=feature_columns
            )
        ],
        axis=1
    )

    test_scaled = pd.concat(
        [
            test_scaled,
            pd.DataFrame(
                X_test_scaled,
                columns=feature_columns
            )
        ],
        axis=1
    )

    # Save original log-transformed partitions.
    train_path = (
        PROCESSED_DATA_DIR / "train_log1p.csv"
    )
    test_path = (
        PROCESSED_DATA_DIR / "test_log1p.csv"
    )

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    # Save scaled partitions.
    train_scaled_path = (
        PROCESSED_DATA_DIR / "train_scaled.csv"
    )
    test_scaled_path = (
        PROCESSED_DATA_DIR / "test_scaled.csv"
    )

    train_scaled.to_csv(train_scaled_path, index=False)
    test_scaled.to_csv(test_scaled_path, index=False)

    # Save the fitted scaler.
    scaler_path = MODELS_DIR / "standard_scaler.joblib"
    joblib.dump(scaler, scaler_path)

    # Verify scaling parameters.
    train_means = X_train_scaled.mean(axis=0)
    train_stds = X_train_scaled.std(axis=0)

    test_user_overlap = (
        set(train_df["user"].unique())
        & set(test_df["user"].unique())
    )

    manifest = {
        "input_file": str(INPUT_FILE),
        "random_state": RANDOM_STATE,
        "split_method": "Chronological split by unique date",
        "train_ratio_by_dates": TRAIN_RATIO,
        "total_records": int(len(df)),
        "total_unique_dates": int(len(unique_dates)),
        "training_records": int(len(train_df)),
        "testing_records": int(len(test_df)),
        "training_unique_dates": int(len(train_dates)),
        "testing_unique_dates": int(len(test_dates)),
        "training_start_date": str(pd.Timestamp(train_dates[0]).date()),
        "training_end_date": str(train_end.date()),
        "testing_start_date": str(test_start.date()),
        "testing_end_date": str(pd.Timestamp(test_dates[-1]).date()),
        "training_unique_users": int(train_df["user"].nunique()),
        "testing_unique_users": int(test_df["user"].nunique()),
        "users_present_in_both_periods": int(len(test_user_overlap)),
        "feature_count": len(feature_columns),
        "features": feature_columns,
        "scaler": "StandardScaler",
        "scaler_fit_on": "Training data only",
        "scaled_training_mean_max_abs": float(abs(train_means).max()),
        "scaled_training_std_min": float(train_stds.min()),
        "scaled_training_std_max": float(train_stds.max()),
    }

    manifest_path = (
        TABLES_DIR / "temporal_split_manifest.json"
    )

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    report_path = (
        REPORTS_DIR / "temporal_split_report.txt"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("CHRONOLOGICAL TRAIN/TEST SPLIT REPORT\n")
        file.write("=" * 65 + "\n\n")

        for key, value in manifest.items():
            file.write(f"{key}: {value}\n")

    print("\n[1] CHRONOLOGICAL PARTITION")
    print(f"Total records: {len(df):,}")
    print(f"Unique dates: {len(unique_dates):,}")
    print(f"Training records: {len(train_df):,}")
    print(f"Testing records: {len(test_df):,}")

    print("\n[2] DATE BOUNDARIES")
    print(f"Training: {train_dates[0]} to {train_end}")
    print(f"Testing:  {test_start} to {test_dates[-1]}")

    print("\n[3] USER COVERAGE")
    print(f"Training users: {train_df['user'].nunique():,}")
    print(f"Testing users: {test_df['user'].nunique():,}")
    print(f"Users in both periods: {len(test_user_overlap):,}")

    print("\n[4] SCALING VALIDATION")
    print("Scaler: StandardScaler")
    print("Scaler fitted on training data only.")
    print(
        "Maximum absolute training mean:",
        round(float(abs(train_means).max()), 8)
    )
    print(
        "Minimum training standard deviation:",
        round(float(train_stds.min()), 8)
    )

    print("\n[5] OUTPUT FILES")
    for path in [
        train_path,
        test_path,
        train_scaled_path,
        test_scaled_path,
        scaler_path,
        manifest_path,
        report_path,
    ]:
        print(path)

    print("\nSTEP 05 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
