import sys
import json
import numpy as np
import pandas as pd

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    FINAL_DATASET,
    TABLES_DIR,
    REPORTS_DIR,
    PROCESSED_DATA_DIR,
)

METADATA = ["user", "date_only"]

SELECTED_FEATURES = [
    "login_count",
    "logoff_count",
    "unique_pc_count",
    "after_hours_login_count",
    "after_hours_logoff_count",
    "device_activity_count",
    "after_hours_device_activity",
    "file_access_count",
    "after_hours_file_access",
    "zip_file_count",
    "exe_file_count",
    "pdf_file_count",
    "email_count",
    "attachment_count",
    "total_email_size",
    "after_hours_email_count",
    "unique_recipients",
    "web_activity_count",
    "unique_domains",
    "after_hours_web_activity",
]

EXCLUDED_FEATURES = {
    "device_connect_count": "Highly redundant with device_activity_count",
    "device_disconnect_count": "Highly redundant with device_activity_count",
    "unique_file_extensions": "Highly correlated with file_access_count",
    "after_hours_email_ratio": "Nearly identical rank ordering to after_hours_email_count",
    "unique_urls": "Highly correlated with unique_domains",
}


def main():
    print("=" * 75)
    print("STEP 04: FEATURE ENGINEERING AND TRANSFORMATION")
    print("=" * 75)

    if not FINAL_DATASET.exists():
        raise FileNotFoundError(FINAL_DATASET)

    df = pd.read_csv(FINAL_DATASET, low_memory=False)

    required = METADATA + SELECTED_FEATURES
    missing = sorted(set(required) - set(df.columns))

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"\nOriginal dataset shape: {df.shape}")

    # Keep identifiers and chronological information.
    output = df[METADATA].copy()

    output["date_only"] = pd.to_datetime(
        output["date_only"],
        errors="raise"
    )

    # Convert selected features to numeric.
    numeric = df[SELECTED_FEATURES].apply(
        pd.to_numeric,
        errors="coerce"
    )

    if numeric.isna().any().any():
        raise ValueError(
            "Missing or non-numeric values found in selected features."
        )

    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Infinite values found in selected features.")

    if (numeric < 0).any().any():
        raise ValueError(
            "Negative values found. log1p cannot be applied safely."
        )

    # Apply log1p to count and volume features.
    # No ratio feature remains in this selected set.
    transformed = np.log1p(numeric)

    output[SELECTED_FEATURES] = transformed

    # Sort chronologically and then by user.
    output = output.sort_values(
        ["date_only", "user"]
    ).reset_index(drop=True)

    # Save transformed model input dataset.
    output_path = (
        PROCESSED_DATA_DIR /
        "user_day_model_features_log1p.csv"
    )

    output.to_csv(output_path, index=False)

    # Transformation documentation.
    transformation_report = pd.DataFrame({
        "feature": SELECTED_FEATURES,
        "transformation": ["log1p(x)"] * len(SELECTED_FEATURES),
        "original_mean": [
            numeric[c].mean() for c in SELECTED_FEATURES
        ],
        "original_skewness": [
            numeric[c].skew() for c in SELECTED_FEATURES
        ],
        "transformed_mean": [
            transformed[c].mean() for c in SELECTED_FEATURES
        ],
        "transformed_skewness": [
            transformed[c].skew() for c in SELECTED_FEATURES
        ],
        "zero_percentage": [
            (numeric[c] == 0).mean() * 100
            for c in SELECTED_FEATURES
        ],
    })

    transformation_path = (
        TABLES_DIR / "feature_transformation_summary.csv"
    )

    transformation_report.to_csv(
        transformation_path,
        index=False
    )

    # Save feature selection documentation.
    feature_summary = {
        "input_dataset": str(FINAL_DATASET),
        "output_dataset": str(output_path),
        "original_candidate_features": 25,
        "selected_features": len(SELECTED_FEATURES),
        "excluded_features": EXCLUDED_FEATURES,
        "transformation": (
            "Natural logarithm transformation using log1p "
            "on all selected non-negative count and volume features."
        ),
        "scaling": (
            "Not applied at this stage. Scaling will be fitted "
            "using training data only during temporal evaluation."
        ),
        "selected_feature_names": SELECTED_FEATURES,
        "rows": int(len(output)),
    }

    json_path = TABLES_DIR / "feature_engineering_summary.json"

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(feature_summary, file, indent=4)

    # Human-readable report.
    report_path = REPORTS_DIR / "feature_engineering_report.txt"

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("FEATURE ENGINEERING REPORT\n")
        file.write("=" * 65 + "\n\n")

        file.write("Selected features:\n")
        for feature in SELECTED_FEATURES:
            file.write(f"- {feature}\n")

        file.write("\nExcluded features and reasons:\n")
        for feature, reason in EXCLUDED_FEATURES.items():
            file.write(f"- {feature}: {reason}\n")

        file.write(
            "\nTransformation: log1p(x) applied to selected "
            "non-negative count and volume features.\n"
        )

        file.write(
            "\nScaling is intentionally deferred until after "
            "the chronological training/test split.\n"
        )

    print("\n[1] FEATURE SELECTION")
    print(f"Selected features: {len(SELECTED_FEATURES)}")
    print(f"Excluded features: {len(EXCLUDED_FEATURES)}")

    print("\n[2] TRANSFORMATION")
    print("Applied log1p to all 20 selected features.")
    print("No scaler fitted at this stage.")

    print("\n[3] OUTPUT DATASET")
    print(f"Shape: {output.shape}")
    print(f"File: {output_path}")

    print("\n[4] OUTPUT DOCUMENTATION")
    print(transformation_path)
    print(json_path)
    print(report_path)

    print("\nSTEP 04 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
