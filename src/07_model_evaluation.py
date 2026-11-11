import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path
from sklearn.metrics import jaccard_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PREDICTIONS_DIR,
    TABLES_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
)

INPUT_FILE = PREDICTIONS_DIR / "test_model_predictions.csv"


def main():
    print("=" * 75)
    print("STEP 07: MODEL EVALUATION AND ANOMALY CONSENSUS")
    print("=" * 75)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE, low_memory=False)
    df["date_only"] = pd.to_datetime(df["date_only"], errors="raise")

    required = [
        "user",
        "date_only",
        "isolation_forest_anomaly",
        "isolation_forest_score",
        "ocsvm_anomaly",
        "ocsvm_score",
    ]

    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing prediction columns: {missing}")

    # -----------------------------------------------------
    # 1. MODEL FLAG COMPARISON
    # -----------------------------------------------------
    print("\n[1] MODEL FLAG COMPARISON")

    df["isolation_forest_anomaly"] = (
        df["isolation_forest_anomaly"].astype(int)
    )
    df["ocsvm_anomaly"] = df["ocsvm_anomaly"].astype(int)

    iso = df["isolation_forest_anomaly"]
    svm = df["ocsvm_anomaly"]

    both = (iso == 1) & (svm == 1)
    iso_only = (iso == 1) & (svm == 0)
    svm_only = (iso == 0) & (svm == 1)
    neither = (iso == 0) & (svm == 0)

    agreement = pd.DataFrame({
        "category": [
            "Both models flagged",
            "Isolation Forest only",
            "One-Class SVM only",
            "Neither model flagged",
        ],
        "records": [
            int(both.sum()),
            int(iso_only.sum()),
            int(svm_only.sum()),
            int(neither.sum()),
        ],
    })

    agreement["percentage"] = (
        agreement["records"] / len(df) * 100
    )

    agreement.to_csv(
        TABLES_DIR / "model_agreement_summary.csv",
        index=False
    )

    iso_count = int(iso.sum())
    svm_count = int(svm.sum())
    both_count = int(both.sum())

    union_count = int(((iso == 1) | (svm == 1)).sum())

    jaccard = (
        both_count / union_count if union_count else 0.0
    )

    comparison = pd.DataFrame([
        {
            "model": "Isolation Forest",
            "anomalies": iso_count,
            "anomaly_percentage": iso_count / len(df) * 100,
        },
        {
            "model": "One-Class SVM",
            "anomalies": svm_count,
            "anomaly_percentage": svm_count / len(df) * 100,
        },
        {
            "model": "Two-model consensus",
            "anomalies": both_count,
            "anomaly_percentage": both_count / len(df) * 100,
        },
    ])

    comparison.to_csv(
        TABLES_DIR / "model_comparison.csv",
        index=False
    )

    print(comparison.round(3).to_string(index=False))
    print(f"\nJaccard similarity: {jaccard:.4f}")

    # -----------------------------------------------------
    # 2. NORMALIZED ANOMALY SCORES
    # -----------------------------------------------------
    print("\n[2] NORMALIZING ANOMALY SCORES")

    # Percentile ranks provide a common relative scale.
    # Higher values mean more anomalous relative to this test set.
    df["if_score_percentile"] = (
        df["isolation_forest_score"].rank(pct=True)
    )

    df["ocsvm_score_percentile"] = (
        df["ocsvm_score"].rank(pct=True)
    )

    df["consensus_score"] = (
        df["if_score_percentile"]
        + df["ocsvm_score_percentile"]
    ) / 2

    # This rank is relative to the test dataset only.
    df["consensus_rank"] = (
        df["consensus_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    df["agreement_category"] = np.select(
        [
            both,
            iso_only,
            svm_only,
        ],
        [
            "Both models flagged",
            "Isolation Forest only",
            "One-Class SVM only",
        ],
        default="Neither model flagged",
    )

    df["consensus_candidate"] = both.astype(int)

    # -----------------------------------------------------
    # 3. RANKED INVESTIGATION CANDIDATES
    # -----------------------------------------------------
    print("\n[3] RANKING INVESTIGATION CANDIDATES")

    candidates = df[df["consensus_candidate"] == 1].copy()

    candidates = candidates.sort_values(
        "consensus_score",
        ascending=False
    )

    candidate_columns = [
        "user",
        "date_only",
        "isolation_forest_score",
        "ocsvm_score",
        "if_score_percentile",
        "ocsvm_score_percentile",
        "consensus_score",
        "consensus_rank",
    ]

    candidates[candidate_columns].to_csv(
        PREDICTIONS_DIR / "consensus_investigation_candidates.csv",
        index=False
    )

    print(f"Consensus candidates: {len(candidates):,}")

    print("\nTop 10 investigation candidates:")
    print(
        candidates[candidate_columns]
        .head(10)
        .round(4)
        .to_string(index=False)
    )

    # Save the full evaluation dataset.
    full_path = (
        PREDICTIONS_DIR / "test_evaluation_with_consensus.csv"
    )

    df.to_csv(full_path, index=False)

    # -----------------------------------------------------
    # 4. DAILY ANOMALY TREND
    # -----------------------------------------------------
    print("\n[4] DAILY ANOMALY TREND")

    daily = (
        df.groupby("date_only")
        .agg(
            test_records=("user", "size"),
            isolation_forest_anomalies=(
                "isolation_forest_anomaly", "sum"
            ),
            ocsvm_anomalies=("ocsvm_anomaly", "sum"),
            consensus_candidates=("consensus_candidate", "sum"),
        )
        .reset_index()
    )

    daily.to_csv(
        TABLES_DIR / "daily_anomaly_summary.csv",
        index=False
    )

    # -----------------------------------------------------
    # 5. VISUALIZATIONS
    # -----------------------------------------------------
    print("\n[5] GENERATING EVALUATION GRAPHS")

    sns.set_theme(style="whitegrid", context="notebook")

    # Figure 1: Model anomaly rates.
    plt.figure(figsize=(10, 6))

    sns.barplot(
        data=comparison,
        x="model",
        y="anomaly_percentage",
    )

    plt.title(
        "Anomaly Detection Rate by Model",
        fontsize=15,
        fontweight="bold"
    )
    plt.xlabel("Detection model")
    plt.ylabel("Flagged test records (%)")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "05_model_anomaly_rates.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Figure 2: Model agreement.
    plt.figure(figsize=(11, 6))

    sns.barplot(
        data=agreement,
        x="category",
        y="records",
    )

    plt.title(
        "Agreement Between Unsupervised Models",
        fontsize=15,
        fontweight="bold"
    )
    plt.xlabel("Agreement category")
    plt.ylabel("Number of user-day records")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "06_model_agreement.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Figure 3: Daily anomaly counts.
    plt.figure(figsize=(15, 7))

    plt.plot(
        daily["date_only"],
        daily["isolation_forest_anomalies"],
        label="Isolation Forest"
    )

    plt.plot(
        daily["date_only"],
        daily["ocsvm_anomalies"],
        label="One-Class SVM"
    )

    plt.plot(
        daily["date_only"],
        daily["consensus_candidates"],
        label="Both models"
    )

    plt.title(
        "Daily Anomaly Detection During Test Period",
        fontsize=15,
        fontweight="bold"
    )
    plt.xlabel("Date")
    plt.ylabel("Flagged user-day records")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "07_daily_anomaly_trends.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Figure 4: Anomaly score distributions.
    sample = df.sample(
        n=min(20000, len(df)),
        random_state=42
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.histplot(
        sample["isolation_forest_score"],
        bins=50,
        kde=True,
        ax=axes[0]
    )
    axes[0].set_title("Isolation Forest Anomaly Scores")
    axes[0].set_xlabel("Anomaly score (higher = more anomalous)")

    sns.histplot(
        sample["ocsvm_score"],
        bins=50,
        kde=True,
        ax=axes[1]
    )
    axes[1].set_title("One-Class SVM Anomaly Scores")
    axes[1].set_xlabel("Anomaly score (higher = more anomalous)")

    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "08_anomaly_score_distributions.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # -----------------------------------------------------
    # 6. SUMMARY REPORT
    # -----------------------------------------------------
    summary = {
        "test_records": int(len(df)),
        "isolation_forest_anomalies": iso_count,
        "isolation_forest_rate_percent": round(
            iso_count / len(df) * 100, 4
        ),
        "ocsvm_anomalies": svm_count,
        "ocsvm_rate_percent": round(
            svm_count / len(df) * 100, 4
        ),
        "both_models_flagged": both_count,
        "consensus_rate_percent": round(
            both_count / len(df) * 100, 4
        ),
        "isolation_forest_only": int(iso_only.sum()),
        "ocsvm_only": int(svm_only.sum()),
        "neither_model_flagged": int(neither.sum()),
        "jaccard_similarity": round(jaccard, 6),
        "candidate_score_method": (
            "Mean of the two test-set anomaly score percentile ranks"
        ),
        "ground_truth_available": False,
        "interpretation": (
            "Consensus candidates are model-flagged investigation "
            "priorities, not confirmed insider threats."
        ),
    }

    summary_path = TABLES_DIR / "model_evaluation_summary.json"

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    report_path = REPORTS_DIR / "model_evaluation_report.txt"

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("MODEL EVALUATION AND CONSENSUS REPORT\n")
        file.write("=" * 65 + "\n\n")

        for key, value in summary.items():
            file.write(f"{key}: {value}\n")

        file.write(
            "\nNo accuracy, precision, recall or F1-score is reported "
            "because confirmed ground-truth labels are unavailable.\n"
        )

    print("\n[6] OUTPUT FILES")
    print(full_path)
    print(PREDICTIONS_DIR / "consensus_investigation_candidates.csv")
    print(TABLES_DIR / "model_comparison.csv")
    print(TABLES_DIR / "model_agreement_summary.csv")
    print(TABLES_DIR / "daily_anomaly_summary.csv")
    print(summary_path)
    print(report_path)

    print("\nFIGURES")
    for name in [
        "05_model_anomaly_rates.png",
        "06_model_agreement.png",
        "07_daily_anomaly_trends.png",
        "08_anomaly_score_distributions.png",
    ]:
        print(FIGURES_DIR / name)

    print("\nSTEP 07 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
