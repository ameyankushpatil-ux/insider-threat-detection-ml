import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PREDICTIONS_DIR,
    TABLES_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
)

INPUT_FILE = (
    PREDICTIONS_DIR / "test_evaluation_with_consensus.csv"
)


def main():
    print("=" * 75)
    print("STEP 08: USER-LEVEL BEHAVIOURAL ANALYSIS")
    print("=" * 75)

    df = pd.read_csv(INPUT_FILE)
    df["date_only"] = pd.to_datetime(df["date_only"])

    required = [
        "user",
        "date_only",
        "consensus_candidate",
        "consensus_score",
        "isolation_forest_anomaly",
        "ocsvm_anomaly",
    ]

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # User-level aggregation.
    candidates = df[df["consensus_candidate"] == 1].copy()

    user_summary = (
        candidates.groupby("user")
        .agg(
            consensus_anomaly_days=("date_only", "nunique"),
            first_anomaly_date=("date_only", "min"),
            last_anomaly_date=("date_only", "max"),
            mean_consensus_score=("consensus_score", "mean"),
            maximum_consensus_score=("consensus_score", "max"),
            isolation_forest_flags=(
                "isolation_forest_anomaly", "sum"
            ),
            ocsvm_flags=("ocsvm_anomaly", "sum"),
        )
        .reset_index()
        .sort_values(
            ["consensus_anomaly_days", "maximum_consensus_score"],
            ascending=False
        )
    )

    user_summary.to_csv(
        TABLES_DIR / "user_consensus_summary.csv",
        index=False
    )

    # Daily rates using the number of records on each date.
    daily = (
        df.groupby("date_only")
        .agg(
            records=("user", "size"),
            isolation_forest_flags=(
                "isolation_forest_anomaly", "sum"
            ),
            ocsvm_flags=("ocsvm_anomaly", "sum"),
            consensus_flags=("consensus_candidate", "sum"),
        )
        .reset_index()
    )

    for col in [
        "isolation_forest",
        "ocsvm",
        "consensus",
    ]:
        daily[f"{col}_rate_percent"] = (
            daily[f"{col}_flags"] / daily["records"] * 100
        )

    daily.to_csv(
        TABLES_DIR / "daily_anomaly_rates.csv",
        index=False
    )

    # Repeated anomaly users.
    repeated = user_summary[
        user_summary["consensus_anomaly_days"] >= 2
    ].copy()

    repeated.to_csv(
        TABLES_DIR / "repeated_anomaly_users.csv",
        index=False
    )

    # Summary.
    print("\n[1] USER-LEVEL SUMMARY")
    print(f"Users with consensus anomalies: {len(user_summary):,}")
    print(f"Users with repeated anomalous days: {len(repeated):,}")
    print(f"Maximum anomalous days for one user: "
          f"{user_summary['consensus_anomaly_days'].max()}")

    print("\nTop 15 users:")
    print(user_summary.head(15).to_string(index=False))

    # Graph 1: repeated anomaly days.
    plt.figure(figsize=(12, 7))

    top = user_summary.head(15).sort_values(
        "consensus_anomaly_days"
    )

    sns.barplot(
        data=top,
        x="consensus_anomaly_days",
        y="user"
    )

    plt.title(
        "Top Users by Consensus Anomalous Days",
        fontsize=15,
        fontweight="bold"
    )
    plt.xlabel("Number of consensus-anomalous days")
    plt.ylabel("User")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "09_top_anomalous_users.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Graph 2: daily anomaly rates.
    plt.figure(figsize=(15, 7))

    plt.plot(
        daily["date_only"],
        daily["isolation_forest_rate_percent"],
        label="Isolation Forest"
    )

    plt.plot(
        daily["date_only"],
        daily["ocsvm_rate_percent"],
        label="One-Class SVM"
    )

    plt.plot(
        daily["date_only"],
        daily["consensus_rate_percent"],
        label="Both models"
    )

    plt.title(
        "Daily Anomaly Rates During Test Period",
        fontsize=15,
        fontweight="bold"
    )
    plt.xlabel("Date")
    plt.ylabel("Flagged records (%)")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "10_daily_anomaly_rates.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # Report.
    with open(
        REPORTS_DIR / "user_behavior_analysis.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write("USER-LEVEL BEHAVIOURAL ANALYSIS\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"Consensus candidates: {len(candidates)}\n")
        f.write(f"Users with consensus anomalies: {len(user_summary)}\n")
        f.write(f"Users with repeated anomalous days: {len(repeated)}\n\n")
        f.write(
            "Repeated anomalous days are prioritization signals. "
            "They do not establish malicious intent.\n"
        )

    print("\n[2] OUTPUT FILES")
    print(TABLES_DIR / "user_consensus_summary.csv")
    print(TABLES_DIR / "repeated_anomaly_users.csv")
    print(TABLES_DIR / "daily_anomaly_rates.csv")
    print(FIGURES_DIR / "09_top_anomalous_users.png")
    print(FIGURES_DIR / "10_daily_anomaly_rates.png")
    print(REPORTS_DIR / "user_behavior_analysis.txt")

    print("\nSTEP 08 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
