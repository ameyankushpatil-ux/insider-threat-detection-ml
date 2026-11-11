import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"

USER = "PWS0219"
CASE_DATE = "2011-02-15"


def main():
    print("=" * 75)
    print("STEP 10: DFIR VISUALIZATION AND EVIDENCE CORRELATION")
    print("=" * 75)

    timeline_path = (
        PROCESSED / "PWS0219_2011-02-15_DFIR_full_timeline.csv"
    )
    baseline_path = (
        TABLES / "PWS0219_historical_baseline.csv"
    )

    events = pd.read_csv(timeline_path)
    baseline = pd.read_csv(baseline_path)

    events["timestamp"] = pd.to_datetime(events["timestamp"])
    events = events.sort_values("timestamp")

    sns.set_theme(style="whitegrid", context="talk")

    # --------------------------------------------------
    # FIGURE 1: EVENT TIMELINE
    # --------------------------------------------------
    print("\n[1] GENERATING EVENT TIMELINE")

    source_order = ["LOGON", "DEVICE", "FILE", "EMAIL", "HTTP"]
    source_y = {name: i for i, name in enumerate(source_order)}

    fig, ax = plt.subplots(figsize=(16, 8))

    for source in source_order:
        subset = events[events["source"] == source]

        if subset.empty:
            continue

        ax.scatter(
            subset["timestamp"],
            [source_y[source]] * len(subset),
            s=55,
            label=source,
            alpha=0.75
        )

    ax.set_yticks(range(len(source_order)))
    ax.set_yticklabels(source_order)
    ax.set_title(
        "PWS0219 Digital Activity Timeline — 15 February 2011",
        fontweight="bold"
    )
    ax.set_xlabel("Time")
    ax.set_ylabel("Event source")
    ax.legend(title="Telemetry source", loc="upper left")
    ax.grid(True, axis="x", alpha=0.3)

    fig.autofmt_xdate()
    plt.tight_layout()

    plt.savefig(
        FIGURES / "11_PWS0219_event_timeline.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # --------------------------------------------------
    # FIGURE 2: EVENT COUNTS BY HOUR
    # --------------------------------------------------
    print("[2] GENERATING HOURLY ACTIVITY GRAPH")

    events["hour"] = events["timestamp"].dt.hour

    hourly = (
        events.groupby(["hour", "source"])
        .size()
        .unstack(fill_value=0)
    )

    hourly = hourly.reindex(range(24), fill_value=0)

    hourly.to_csv(
        TABLES / "PWS0219_hourly_event_counts.csv"
    )

    ax = hourly.plot(
        kind="bar",
        figsize=(16, 7),
        width=0.85
    )

    ax.set_title(
        "PWS0219 Event Volume by Hour",
        fontweight="bold"
    )
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Number of recorded events")
    ax.legend(title="Event source")

    plt.tight_layout()
    plt.savefig(
        FIGURES / "12_PWS0219_hourly_activity.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # --------------------------------------------------
    # FIGURE 3: HISTORICAL BASELINE DEVIATION
    # --------------------------------------------------
    print("[3] GENERATING HISTORICAL BASELINE GRAPH")

    plot_data = baseline.copy()

    plot_data["deviation_from_median"] = (
        plot_data["case_value"]
        - plot_data["historical_median"]
    )

    plot_data = plot_data.sort_values(
        "empirical_percentile",
        ascending=True
    )

    plot_data.to_csv(
        TABLES / "PWS0219_baseline_deviation.csv",
        index=False
    )

    fig, ax = plt.subplots(figsize=(13, 10))

    ax.barh(
        plot_data["feature"],
        plot_data["empirical_percentile"]
    )

    ax.axvline(
        95,
        linestyle="--",
        linewidth=2,
        label="95th percentile threshold"
    )

    ax.set_xlim(0, 105)
    ax.set_xlabel("Empirical historical percentile (%)")
    ax.set_ylabel("Behavioural feature")
    ax.set_title(
        "PWS0219 Behaviour Compared with Historical Baseline",
        fontweight="bold"
    )
    ax.legend()

    plt.tight_layout()
    plt.savefig(
        FIGURES / "13_PWS0219_historical_percentiles.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # --------------------------------------------------
    # FIGURE 4: CASE VS HISTORICAL VALUES
    # --------------------------------------------------
    print("[4] GENERATING CASE-VERSUS-HISTORY GRAPH")

    selected = [
        "after_hours_login_count",
        "after_hours_logoff_count",
        "after_hours_device_activity",
        "file_access_count",
        "after_hours_file_access",
        "zip_file_count",
        "exe_file_count",
        "email_count",
        "web_activity_count",
    ]

    comparison = baseline[
        baseline["feature"].isin(selected)
    ].copy()

    comparison.to_csv(
        TABLES / "PWS0219_key_feature_comparison.csv",
        index=False
    )

    x = np.arange(len(comparison))
    width = 0.25

    fig, ax = plt.subplots(figsize=(15, 8))

    ax.bar(
        x - width,
        comparison["historical_median"],
        width,
        label="Historical median"
    )

    ax.bar(
        x,
        comparison["historical_95th_percentile"],
        width,
        label="Historical 95th percentile"
    )

    ax.bar(
        x + width,
        comparison["case_value"],
        width,
        label="Investigation day"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        comparison["feature"],
        rotation=55,
        ha="right"
    )

    ax.set_title(
        "Key Behavioural Features: Case vs Historical Baseline",
        fontweight="bold"
    )
    ax.set_ylabel("Feature value")
    ax.legend()

    plt.tight_layout()
    plt.savefig(
        FIGURES / "14_PWS0219_case_vs_baseline.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    # --------------------------------------------------
    # EVIDENCE CLASSIFICATION
    # --------------------------------------------------
    print("[5] BUILDING EVIDENCE CORRELATION TABLE")

    evidence = pd.DataFrame([
        {
            "evidence_id": "E01",
            "observation": "Five device connection events",
            "source": "device.csv",
            "finding": "Device connection activity observed",
            "interpretation": "Requires contextual review",
            "limitation": "Does not prove data transfer",
        },
        {
            "evidence_id": "E02",
            "observation": "Five device disconnection events",
            "source": "device.csv",
            "finding": "Device disconnection activity observed",
            "interpretation": "Can be correlated with file events",
            "limitation": "Device identity/content not established",
        },
        {
            "evidence_id": "E03",
            "observation": "Twenty-three file-access events",
            "source": "file.csv",
            "finding": "File activity recorded",
            "interpretation": "Review timing and file extensions",
            "limitation": "Access does not prove copying",
        },
        {
            "evidence_id": "E04",
            "observation": "One EXE file event",
            "source": "file.csv",
            "finding": "EXE activity observed",
            "interpretation": "At historical maximum",
            "limitation": "File execution is not established",
        },
        {
            "evidence_id": "E05",
            "observation": "Twenty-three after-hours file accesses",
            "source": "Processed user-day features",
            "finding": "Above historical 95th percentile",
            "interpretation": "Unusual relative to prior behaviour",
            "limitation": "Not above historical maximum",
        },
        {
            "evidence_id": "E06",
            "observation": "Both anomaly models flagged the case",
            "source": "Model predictions",
            "finding": "Consensus anomaly candidate",
            "interpretation": "High investigation priority",
            "limitation": "Unsupervised detection is not ground truth",
        },
        {
            "evidence_id": "E07",
            "observation": "Ten email events",
            "source": "email.csv",
            "finding": "Email activity recorded",
            "interpretation": "Volume below historical median",
            "limitation": "Metadata does not establish exfiltration",
        },
        {
            "evidence_id": "E08",
            "observation": "One hundred fourteen HTTP events",
            "source": "http.csv",
            "finding": "Web activity recorded",
            "interpretation": "At historical maximum",
            "limitation": "Activity alone does not prove malicious browsing",
        },
    ])

    evidence.to_csv(
        TABLES / "PWS0219_evidence_correlation_matrix.csv",
        index=False
    )

    # --------------------------------------------------
    # FINAL REPORT ADDENDUM
    # --------------------------------------------------
    print("[6] WRITING DFIR ANALYSIS ADDENDUM")

    report_path = (
        REPORTS / "PWS0219_DFIR_visual_analysis.txt"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PWS0219 DFIR VISUAL ANALYSIS\n")
        f.write("=" * 75 + "\n\n")

        f.write("CASE DETAILS\n")
        f.write(f"User: {USER}\n")
        f.write(f"Date: {CASE_DATE}\n")
        f.write(f"Extracted raw events: {len(events)}\n\n")

        f.write("EVENT COUNTS\n")
        f.write(events["source"].value_counts().to_string())
        f.write("\n\n")

        f.write("HISTORICAL BASELINE INTERPRETATION\n")
        f.write(
            "No measured case feature exceeds its historical maximum.\n"
        )
        f.write(
            "After-hours file access and total file access exceed "
            "the historical 95th percentile.\n"
        )
        f.write(
            "Several features equal the historical maximum.\n\n"
        )

        f.write("EVIDENCE CORRELATION\n")
        f.write(evidence.to_string(index=False))
        f.write("\n\n")

        f.write("CONCLUSION\n")
        f.write(
            "The combined telemetry and model results support "
            "prioritizing this user-day for investigation. "
            "They do not establish unauthorized copying, "
            "exfiltration, or malicious intent.\n"
        )

    print("\n[7] OUTPUT FILES")

    for name in [
        "11_PWS0219_event_timeline.png",
        "12_PWS0219_hourly_activity.png",
        "13_PWS0219_historical_percentiles.png",
        "14_PWS0219_case_vs_baseline.png",
    ]:
        print(FIGURES / name)

    print(TABLES / "PWS0219_evidence_correlation_matrix.csv")
    print(TABLES / "PWS0219_baseline_deviation.csv")
    print(report_path)

    print("\nSTEP 10 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
