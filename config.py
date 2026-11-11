from pathlib import Path

# Project root: directory containing this file
PROJECT_ROOT = Path(__file__).resolve().parent

# Main directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

SRC_DIR = PROJECT_ROOT / "src"
MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = PROJECT_ROOT / "figures"

# Existing processed dataset
FINAL_DATASET = PROCESSED_DATA_DIR / "user_day_review2_final.csv"

# Existing DFIR timeline
DFIR_TIMELINE = PROCESSED_DATA_DIR / (
    "PWS0219_2011-02-15_DFIR_investigation_timeline.csv"
)

# Output directories
METRICS_DIR = RESULTS_DIR / "metrics"
PREDICTIONS_DIR = RESULTS_DIR / "predictions"
TABLES_DIR = RESULTS_DIR / "tables"

# Reproducibility
RANDOM_STATE = 42

# Project metadata
PROJECT_TITLE = (
    "Insider-Threat Detection Using Unsupervised "
    "Machine Learning and Behavioural Anomaly Analysis"
)

PROJECT_DATASET = "CERT Insider Threat Dataset r4.2"

# Create output directories if they do not exist
for directory in [
    SRC_DIR,
    MODELS_DIR,
    RESULTS_DIR,
    REPORTS_DIR,
    FIGURES_DIR,
    METRICS_DIR,
    PREDICTIONS_DIR,
    TABLES_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
