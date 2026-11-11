import json
import warnings
import pandas as pd
import numpy as np

from pathlib import Path
from urllib.parse import urlparse

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PREDICTIONS = ROOT / "results" / "predictions"
TABLES = ROOT / "results" / "tables"
REPORTS = ROOT / "reports"
FIGURES = ROOT / "figures"

USER = "PWS0219"
CASE_DATE = pd.Timestamp("2011-02-15")

DATE_FORMAT = "%m/%d/%Y %H:%M:%S"

# Raw files are read using only the columns required for
# forensic metadata analysis. Content fields are excluded.
RAW_CONFIG = {
    "logon.csv": {
        "source": "LOGON",
        "columns": ["id", "date", "user", "pc", "activity"],
    },
    "device.csv": {
        "source": "DEVICE",
        "columns": ["id", "date", "user", "pc", "activity"],
    },
    "file.csv": {
        "source": "FILE",
        "columns": ["id", "date", "user", "pc", "filename"],
    },
    "email.csv": {
        "source": "EMAIL",
        "columns": [
            "id", "date", "user", "pc",
            "to", "size", "attachments"
        ],
    },
    "http.csv": {
        "source": "HTTP",
        "columns": ["id", "date", "user", "pc", "url"],
    },
}


def parse_dates(series):
    return pd.to_datetime(
        series,
        format=DATE_FORMAT,
        errors="coerce"
    )


def extract_small_file(filename, config):
    """Extract target user/date from smaller raw CSV files."""
    path = RAW / filename

    print(f"Reading {filename}...")

    df = pd.read_csv(
        path,
        usecols=config["columns"],
        low_memory=False
    )

    df = df[df["user"] == USER].copy()

    df["timestamp"] = parse_dates(df["date"])

    df = df[df["timestamp"].dt.normalize() == CASE_DATE].copy()

    return normalize_events(df, config["source"])


def extract_large_file(filename, config, chunksize=250000):
    """Extract target user/date without loading a large log entirely."""
    path = RAW / filename

    print(f"Scanning {filename} in chunks...")

    results = []
    total_rows = 0
    matched_rows = 0

    for chunk in pd.read_csv(
        path,
        usecols=config["columns"],
        chunksize=chunksize,
        low_memory=False
    ):
        total_rows += len(chunk)

        chunk = chunk[chunk["user"] == USER].copy()

        if chunk.empty:
            continue

        chunk["timestamp"] = parse_dates(chunk["date"])

        chunk = chunk[
            chunk["timestamp"].dt.normalize() == CASE_DATE
        ].copy()

        if not chunk.empty:
            matched_rows += len(chunk)
            results.append(
                normalize_events(chunk, config["source"])
            )

    print(
        f"  Scanned {total_rows:,} rows; "
        f"matched {matched_rows:,} target events."
    )

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame()


def normalize_events(df, source):
    """Create a common event structure without raw content."""
    rows = []

    for _, row in df.iterrows():
        timestamp = row["timestamp"]
        pc = row.get("pc", "")
        details = ""

        if source in ["LOGON", "DEVICE"]:
            event_type = str(row.get("activity", "Unknown"))
            details = f"Activity: {event_type}"

        elif source == "FILE":
            filename = str(row.get("filename", ""))
            extension = Path(filename).suffix.lower()

            event_type = "File Access"
            details = (
                f"Filename: {filename}; "
                f"Extension: {extension or 'unknown'}"
            )

        elif source == "EMAIL":
            event_type = "Email"

            size = pd.to_numeric(
                row.get("size", 0),
                errors="coerce"
            )

            attachments = pd.to_numeric(
                row.get("attachments", 0),
                errors="coerce"
            )

            details = (
                f"Message size: {size}; "
                f"Attachment count: {attachments}"
            )

        elif source == "HTTP":
            event_type = "Web Activity"

            url = str(row.get("url", ""))
            domain = urlparse(url).hostname or "unknown"

            details = f"Domain: {domain}"

        else:
            event_type = "Unknown"

        rows.append({
            "event_id": row.get("id", ""),
            "timestamp": timestamp,
            "date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "user": USER,
            "pc": pc,
            "source": source,
            "event_type": event_type,
            "details": details,
        })

    return pd.DataFrame(rows)


def build_historical_baseline():
    """Compare case features with prior user-day observations."""
    path = PROCESSED / "user_day_review2_final.csv"

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path, low_memory=False)

    df["date_only"] = pd.to_datetime(
        df["date_only"],
        errors="coerce"
    )

    historical = df[
        (df["user"] == USER)
        & (df["date_only"] < CASE_DATE)
    ].copy()

    case = df[
        (df["user"] == USER)
        & (df["date_only"] == CASE_DATE)
    ].copy()

    if case.empty:
        raise ValueError(
            "Target user/date not found in processed dataset."
        )

    if historical.empty:
        raise ValueError(
            "No historical observations available for this user."
        )

    features = [
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

    rows = []

    for feature in features:
        if feature not in historical.columns:
            continue

        values = pd.to_numeric(
            historical[feature],
            errors="coerce"
        ).dropna()

        case_value = float(case.iloc[0][feature])

        if values.empty:
            continue

        rows.append({
            "feature": feature,
            "case_value": case_value,
            "historical_observations": len(values),
            "historical_mean": values.mean(),
            "historical_median": values.median(),
            "historical_std": values.std(),
            "historical_min": values.min(),
            "historical_max": values.max(),
            "historical_95th_percentile": values.quantile(0.95),
            "historical_99th_percentile": values.quantile(0.99),

            # Tie-aware empirical percentile (midrank method)
            "empirical_percentile": (
                (
                    (values < case_value).sum()
                    + 0.5 * (values == case_value).sum()
                ) / len(values) * 100
            ),

            # Explicit historical maximum comparison
            "equal_to_historical_max": bool(
                case_value == values.max()
            ),
            "above_historical_max": bool(
                case_value > values.max()
            ),
        })

    result = pd.DataFrame(rows)

    result.to_csv(
        TABLES / "PWS0219_historical_baseline.csv",
        index=False
    )

    return historical, case, result


def main():
    print("=" * 75)
    print("STEP 09: RAW-EVENT DFIR INVESTIGATION")
    print("=" * 75)

    all_events = []

    # Smaller raw files.
    for filename in [
        "logon.csv",
        "device.csv",
        "file.csv",
    ]:
        events = extract_small_file(
            filename,
            RAW_CONFIG[filename]
        )
        all_events.append(events)

    # Large files: streaming/chunk extraction.
    for filename in [
        "email.csv",
        "http.csv",
    ]:
        events = extract_large_file(
            filename,
            RAW_CONFIG[filename]
        )
        all_events.append(events)

    events = pd.concat(
        [x for x in all_events if not x.empty],
        ignore_index=True
    )

    events = events.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # --------------------------------------------------
    # 1. SAVE RAW-EVENT METADATA TIMELINE
    # --------------------------------------------------
    timeline_path = (
        PROCESSED /
        "PWS0219_2011-02-15_DFIR_full_timeline.csv"
    )

    events.to_csv(timeline_path, index=False)

    print("\n[1] RAW-EVENT TIMELINE")
    print(f"Total events: {len(events):,}")
    print(events["source"].value_counts().to_string())

    # --------------------------------------------------
    # 2. EVENT COUNTS
    # --------------------------------------------------
    source_counts = (
        events.groupby("source")
        .size()
        .rename("event_count")
        .reset_index()
        .sort_values("event_count", ascending=False)
    )

    source_counts.to_csv(
        TABLES / "PWS0219_event_source_counts.csv",
        index=False
    )

    event_type_counts = (
        events.groupby(["source", "event_type"])
        .size()
        .rename("event_count")
        .reset_index()
    )

    event_type_counts.to_csv(
        TABLES / "PWS0219_event_type_counts.csv",
        index=False
    )

    # --------------------------------------------------
    # 3. EVENT TIMELINE SUMMARY
    # --------------------------------------------------
    print("\n[2] TIMELINE SUMMARY")

    print("First event:", events["timestamp"].min())
    print("Last event:", events["timestamp"].max())

    print("\nEvent source counts:")
    print(source_counts.to_string(index=False))

    print("\nEvent type counts:")
    print(event_type_counts.to_string(index=False))

    # --------------------------------------------------
    # 4. DEVICE / FILE TEMPORAL SEQUENCE
    # --------------------------------------------------
    device_file = events[
        events["source"].isin(["DEVICE", "FILE", "LOGON"])
    ].copy()

    device_file.to_csv(
        PROCESSED /
        "PWS0219_device_file_sequence.csv",
        index=False
    )

    # --------------------------------------------------
    # 5. HISTORICAL BASELINE
    # --------------------------------------------------
    print("\n[3] HISTORICAL BASELINE")

    historical, case, baseline = build_historical_baseline()

    print(
        f"Historical user-day observations: {len(historical):,}"
    )

    print("\nCase-versus-history comparison:")
    print(
        baseline[
            [
                "feature",
                "case_value",
                "historical_median",
                "historical_95th_percentile",
                "empirical_percentile",
            ]
        ].round(2).to_string(index=False)
    )

    # --------------------------------------------------
    # 6. MODEL EVIDENCE
    # --------------------------------------------------
    prediction_path = (
        PREDICTIONS /
        "test_evaluation_with_consensus.csv"
    )

    predictions = pd.read_csv(prediction_path)

    model_case = predictions[
        (predictions["user"] == USER)
        & (predictions["date_only"] == "2011-02-15")
    ]

    if model_case.empty:
        raise ValueError("Model case record not found.")

    model_record = model_case.iloc[0].to_dict()

    # --------------------------------------------------
    # 7. INVESTIGATION REPORT
    # --------------------------------------------------
    report_path = (
        REPORTS /
        "PWS0219_2011-02-15_DFIR_report.txt"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("DIGITAL FORENSICS AND INCIDENT RESPONSE REPORT\n")
        f.write("=" * 75 + "\n\n")

        f.write(f"Subject user: {USER}\n")
        f.write(f"Investigation date: {CASE_DATE.date()}\n")
        f.write("Dataset: CERT Insider Threat Dataset r4.2\n\n")

        f.write("1. MODEL DETECTION\n")
        f.write("-" * 50 + "\n")
        f.write(
            f"Isolation Forest anomaly: "
            f"{model_record['isolation_forest_anomaly']}\n"
        )
        f.write(
            f"One-Class SVM anomaly: "
            f"{model_record['ocsvm_anomaly']}\n"
        )
        f.write(
            f"Consensus score: "
            f"{model_record['consensus_score']:.6f}\n"
        )
        f.write(
            f"Consensus rank: "
            f"{model_record['consensus_rank']}\n\n"
        )

        f.write("2. RAW EVENT SUMMARY\n")
        f.write("-" * 50 + "\n")
        f.write(f"Total extracted events: {len(events)}\n")
        f.write(source_counts.to_string(index=False))
        f.write("\n\n")

        f.write("3. HISTORICAL BASELINE\n")
        f.write("-" * 50 + "\n")
        f.write(
            f"Historical observations: {len(historical)}\n"
        )
        f.write(baseline.to_string(index=False))
        f.write("\n\n")

        f.write("4. INVESTIGATION LIMITATIONS\n")
        f.write("-" * 50 + "\n")
        f.write(
            "The available telemetry records observable events "
            "but does not independently establish malicious intent.\n"
        )
        f.write(
            "Device connection followed by file activity does not "
            "prove that files were copied to removable media.\n"
        )
        f.write(
            "Email and HTTP metadata are analysed without treating "
            "synthetic dataset content or URLs as real-world threats.\n"
        )
        f.write(
            "The anomaly score is a relative model score, not a "
            "probability of insider-threat activity.\n"
        )

    # --------------------------------------------------
    # 8. JSON SUMMARY
    # --------------------------------------------------
    summary = {
        "user": USER,
        "case_date": str(CASE_DATE.date()),
        "raw_event_count": int(len(events)),
        "event_counts_by_source": {
            row["source"]: int(row["event_count"])
            for _, row in source_counts.iterrows()
        },
        "historical_user_day_observations": int(len(historical)),
        "isolation_forest_flag": int(
            model_record["isolation_forest_anomaly"]
        ),
        "ocsvm_flag": int(model_record["ocsvm_anomaly"]),
        "consensus_rank": int(model_record["consensus_rank"]),
        "consensus_score": float(model_record["consensus_score"]),
        "conclusion": (
            "High-priority investigation candidate; "
            "malicious intent is not established."
        ),
    }

    with open(
        TABLES / "PWS0219_DFIR_summary.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=4)

    print("\n[4] OUTPUTS")
    print(timeline_path)
    print(PROCESSED / "PWS0219_device_file_sequence.csv")
    print(TABLES / "PWS0219_event_source_counts.csv")
    print(TABLES / "PWS0219_event_type_counts.csv")
    print(TABLES / "PWS0219_historical_baseline.csv")
    print(TABLES / "PWS0219_DFIR_summary.json")
    print(report_path)

    print("\nSTEP 09 COMPLETED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
