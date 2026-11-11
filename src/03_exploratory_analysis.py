import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    FINAL_DATASET,
    TABLES_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
)

FEATURES = [
    "login_count",
    "logoff_count",
    "unique_pc_count",
    "after_hours_login_count",
    "after_hours_logoff_count",
    "device_activity_count",
    "device_connect_count",
    "device_disconnect_count",
    "after_hours_device_activity",
    "file_access_count",
    "unique_file_extensions",
    "after_hours_file_access",
    "zip_file_count",
    "exe_file_count",
    "pdf_file_count",
    "email_count",
    "attachment_count",
    "total_email_size",
    "after_hours_email_count",
    "after_hours_email_ratio",
    "unique_recipients",
    "web_activity_count",
    "unique_urls",
    "unique_domains",
    "after_hours_web_activity",
]

# Features that represent counts or non-negative quantities.
# These will be log1p-transformed for distribution visualization.
COUNT_FEATURES = [
    col for col in FEATURES
    if col != "after_hours_email_ratio"
]


def load_data():
    if not FINAL_DATASET.exists():
        raise FileNotFoundError(FINAL_DATASET)

    df = pd.read_csv(FINAL_DATASET, low_memory=False)

    df["date_only"] = pd.to_datetime(
        df["date_only"],
        errors="raise"
    )

    return df


def save_descriptive_statistics(df):
    stats = df[FEATURES].describe().T

    stats["zero_percentage"] = (
        (df[FEATURES] == 0).mean() * 100
    )

    stats["skewness"] = df[FEATURES].skew()

    stats.to_csv(
        TABLES_DIR / "descriptive_statistics.csv"
    )

    skewness = pd.DataFrame({
        "feature": FEATURES,
        "raw_skewness": [
            df[col].skew() for col in FEATURES
        ],
        "log1p_skewness": [
            np.log1p(df[col]).skew()
            if col in COUNT_FEATURES
            else df[col].skew()
            for col in FEATURES
        ],
        "zero_percentage": [
            (df[col] == 0).mean() * 100
            for col in FEATURES
        ],
    })

    skewness.to_csv(
        TABLES_DIR / "feature_skewness.csv",
        index=False
    )

    return stats, skewness


def plot_zero_activity(df):
    zero_percentage = (
        (df[FEATURES] == 0).mean() * 100
    ).sort_values()

    plt.figure(figsize=(12, 9))

    sns.barplot(
        x=zero_percentage.values,
        y=zero_percentage.index
    )

    plt.title(
        "Percentage of User-Days with Zero Activity",
        fontsize=16,
        fontweight="bold"
    )
    plt.xlabel("Zero Activity (%)")
    plt.ylabel("Behavioural Feature")
    plt.grid(axis="x", alpha=0.25)
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "01_zero_activity_analysis.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()


def plot_feature_distributions(df):
    n_cols = 3
    n_rows = int(np.ceil(len(FEATURES) / n_cols))

    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(17, n_rows * 3.5)
    )

    axes = axes.flatten()

    for i, feature in enumerate(FEATURES):
        values = df[feature].dropna()

        if feature in COUNT_FEATURES:
            values = np.log1p(values)

            label = "log(1 + activity)"
        else:
            label = "Activity ratio"

        sns.histplot(
            values,
            bins=40,
            kde=False,
            ax=axes[i]
        )

        axes[i].set_title(feature, fontsize=10)
        axes[i].set_xlabel(label)
        axes[i].set_ylabel("User-day frequency")

    for j in range(len(FEATURES), len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "Distribution of Behavioural Features",
        fontsize=17,
        fontweight="bold",
        y=1.002
    )

    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "02_feature_distributions.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()


def plot_correlation_matrix(df):
    correlation = df[FEATURES].corr(
        method="spearman"
    )

    correlation.to_csv(
        TABLES_DIR / "spearman_correlation_matrix.csv"
    )

    plt.figure(figsize=(18, 14))

    sns.heatmap(
        correlation,
        cmap="coolwarm",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.3,
        annot=False,
        cbar_kws={
            "label": "Spearman correlation"
        }
    )

    plt.title(
        "Spearman Correlation Between Behavioural Features",
        fontsize=16,
        fontweight="bold"
    )

    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "03_spearman_correlation.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()


def plot_monthly_activity(df):
    monthly = df.copy()

    monthly["month"] = (
        monthly["date_only"].dt.to_period("M").astype(str)
    )

    monthly_summary = (
        monthly.groupby("month")
        .agg(
            user_day_records=("user", "size"),
            active_users=("user", "nunique"),
            total_logins=("login_count", "sum"),
            total_file_access=("file_access_count", "sum"),
            total_emails=("email_count", "sum"),
            total_web_activity=("web_activity_count", "sum"),
        )
        .reset_index()
    )

    monthly_summary.to_csv(
        TABLES_DIR / "monthly_activity_summary.csv",
        index=False
    )

    fig, axes = plt.subplots(
        2, 1,
        figsize=(15, 10)
    )

    axes[0].plot(
        monthly_summary["month"],
        monthly_summary["user_day_records"],
        marker="o"
    )

    axes[0].set_title(
        "Monthly User-Day Record Coverage",
        fontweight="bold"
    )
    axes[0].set_ylabel("User-day records")
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].grid(alpha=0.3)

    activity_columns = [
        "total_logins",
        "total_file_access",
        "total_emails",
        "total_web_activity",
    ]

    for col in activity_columns:
        axes[1].plot(
            monthly_summary["month"],
            monthly_summary[col],
            marker="o",
            label=col.replace("total_", "").replace("_", " ").title()
        )

    axes[1].set_title(
        "Monthly Behavioural Activity Trends",
        fontweight="bold"
    )
    axes[1].set_ylabel("Total activity events")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "04_monthly_activity_trends.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()


def main():
    print("=" * 75)
    print("STEP 03: EXPLORATORY DATA ANALYSIS")
    print("=" * 75)

    sns.set_theme(
        style="whitegrid",
        context="notebook"
    )

    df = load_data()

    print(f"\nDataset records: {len(df):,}")
    print(f"Candidate features: {len(FEATURES)}")

    print("\n[1] DESCRIPTIVE STATISTICS")

    stats, skewness = save_descriptive_statistics(df)

    print(stats[["mean", "std", "min", "max", "zero_percentage", "skewness"]].round(3).to_string())

    print("\n[2] GENERATING ZERO-ACTIVITY GRAPH")
    plot_zero_activity(df)

    print("\n[3] GENERATING FEATURE DISTRIBUTION GRAPH")
    plot_feature_distributions(df)

    print("\n[4] GENERATING CORRELATION HEATMAP")
    plot_correlation_matrix(df)

    print("\n[5] GENERATING MONTHLY ACTIVITY TRENDS")
    plot_monthly_activity(df)

    print("\n[6] HIGHLY SKEWED FEATURES")
    print(
        skewness.sort_values(
            "raw_skewness",
            ascending=False
        ).head(10).round(3).to_string(index=False)
    )

    report = REPORTS_DIR / "eda_interpretation.txt"

    with open(report, "w", encoding="utf-8") as f:
        f.write("EXPLORATORY DATA ANALYSIS REPORT\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"Total user-day records: {len(df):,}\n")
        f.write(f"Behavioural features analysed: {len(FEATURES)}\n\n")

        f.write(
            "The analysis includes descriptive statistics, "
            "zero-activity prevalence, feature distributions, "
            "Spearman correlation and monthly activity trends.\n\n"
        )

        f.write(
            "Log1p transformations are used for count-feature "
            "visualization to make highly skewed distributions "
            "easier to inspect. They do not modify the source dataset.\n\n"
        )

        f.write(
            "Correlation indicates association, not causation. "
            "Feature selection decisions must consider behavioural "
            "meaning and model requirements.\n"
        )

    print("\nOUTPUTS")
    print("Tables:", TABLES_DIR)
    print("Figures:", FIGURES_DIR)
    print("Report:", report)

    print("\nSTEP 03 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
