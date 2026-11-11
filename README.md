# Insider-Threat Detection Using Unsupervised Machine Learning and Behavioural Anomaly Analysis

An academic cybersecurity project that analyses daily user-behaviour telemetry and ranks unusual user-days for further investigation using unsupervised machine-learning techniques.

> **Important:** This project produces anomaly indicators and investigation candidates. It does not establish that a user is malicious or confirm an insider-threat incident.

## Project overview

- **Domain:** Cybersecurity — Insider-Threat Detection
- **Approach:** Unsupervised machine learning and behavioural anomaly analysis
- **Dataset:** CERT Insider Threat Test Dataset r4.2
- **Implementation:** Python
- **Models:** Isolation Forest and One-Class SVM

## Overview

Insider-threat detection is challenging because legitimate users can perform activities that are unusual without necessarily being malicious. This project explores an unsupervised behavioural-anomaly detection workflow using user-day activity features derived from the CERT dataset.

The workflow inventories and validates the available data, explores behavioural patterns, engineers features, creates a chronological train/test split, trains two anomaly-detection models, compares their outputs, ranks consensus investigation candidates, and performs a deeper event-level investigation of a selected user-day.

## Objectives

1. Prepare and validate user-day behavioural telemetry.
2. Engineer numerical features representing login, device, file, email and web activity.
3. Train unsupervised anomaly-detection models.
4. Compare model outputs and rank candidate user-days.
5. Investigate a selected candidate using underlying event records.
6. Document methodology, limitations and reproducibility considerations.

## Dataset and privacy

The project uses the **CERT Insider Threat Test Dataset r4.2**. The integrated user-day dataset used in the analysis contains:

- 342,706 user-day records
- 1,000 users
- 55 columns in the integrated dataset
- Date range: 2010-01-02 to 2011-05-17

The raw CERT dataset is not included in this repository. Obtain it from its authorized source and follow the dataset's terms and conditions. Do not commit raw data, processed user-level records, event timelines, credentials or other sensitive material.

The repository's `.gitignore` excludes `data/`, `results/` and `models/` by default. Review every file before publishing this repository publicly.

## Methodology

### 1. Data inventory and validation

The pipeline inventories raw and processed files, classifies behavioural and metadata fields, and checks dates, user identifiers, duplicate user-days, missing values, negative values and infinite values.

### 2. Exploratory data analysis

Exploratory analysis examines zero-activity patterns, feature distributions, correlations and monthly activity trends. Highly correlated or redundant fields are considered during feature selection.

### 3. Feature engineering

Twenty behavioural features are retained for modelling. A `log1p` transformation is applied to reduce skew in activity-count and size features. User and date metadata are retained separately and are not used as model inputs.

### 4. Chronological split and scaling

The data is split chronologically to reduce temporal leakage:

| Partition | Records | Date range |
|---|---:|---|
| Training | 275,893 | 2010-01-02 to 2011-02-05 |
| Testing | 66,813 | 2011-02-06 to 2011-05-17 |

The `StandardScaler` is fitted on the training partition only and then applied to the test partition.

### 5. Unsupervised anomaly detection

Two models are used:

- **Isolation Forest:** identifies observations that are relatively easy to isolate in randomly partitioned feature space.
- **One-Class SVM:** learns a boundary around the training observations and identifies observations outside that learned region.

Isolation Forest is trained on the training data. One-Class SVM is trained on a 10,000-row training sample, and test observations are scored in batches.

### 6. Consensus ranking

Model outputs are compared and a consensus ranking is produced using percentile-normalised anomaly scores. The consensus score is a ranking signal, **not a probability of malicious activity**.

### 7. Event-level investigation

A selected candidate, **PWS0219 on 2011-02-15**, is examined using available raw event sources. The investigation correlates logon, device, file, email and HTTP event metadata into a timeline and compares the case's daily features with that user's historical behaviour.

## Selected experimental results

Results below refer to the chronological test partition.

| Measure | Result |
|---|---:|
| Test records | 66,813 |
| Isolation Forest flagged | 621 (0.93%) |
| One-Class SVM flagged | 1,702 (2.55%) |
| Both models flagged | 487 (0.73%) |
| Jaccard overlap | 0.2653 |

The Jaccard value describes the overlap between the two models' flagged sets; it is not a measure of detection accuracy or model effectiveness.

### Investigation example

For PWS0219 on 2011-02-15, the event-level investigation assembled 169 events:

| Event source | Events |
|---|---:|
| HTTP | 114 |
| FILE | 23 |
| LOGON | 12 |
| DEVICE | 10 |
| EMAIL | 10 |
| **Total** | **169** |

The analysis identified activity sequences and some features above the user's historical 95th percentile. However, no measured feature exceeded that user's historical maximum in the comparison performed. The observed sequence is an investigation lead, not proof of file copying, data exfiltration or malicious intent.

## Repository structure

```text
insider-threat-detection-ml/
├── assets/                 # Approved project assets
├── figures/                # Generated analysis figures
├── notebooks/              # Exploratory notebooks (not included in initial public release)
├── reports/                # Project reports (not included in initial public release)
├── src/                    # Python pipeline scripts
├── config.py
├── requirements.txt
├── .gitignore
└── README.md
```

The exact local data and output folders are created by the project scripts/configuration as needed and are intentionally not tracked in this repository.

## Figures

The `figures/` directory contains generated visualizations, including:

- Zero-activity analysis and feature distributions
- Spearman correlation heatmap
- Monthly activity trends
- Model anomaly rates and agreement
- Daily anomaly trends and score distributions

## Setup

### Requirements

- Windows, Linux or macOS
- Python 3.12 (the project was run in Python 3.12.10)
- CERT Insider Threat Test Dataset r4.2, obtained separately from its authorized source

### Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Place the authorized dataset files in the directory structure expected by the scripts. Check `config.py` and each script's input-path configuration before running the pipeline. Dataset files are not supplied in this repository.

## Running the pipeline

Run the scripts from the repository root, in numerical order, after placing the required dataset files in the expected locations:

```bash
python src/01_dataset_inventory.py
python src/02_data_validation.py
python src/03_exploratory_analysis.py
python src/04_feature_engineering.py
python src/05_temporal_split.py
python src/06_model_training.py
python src/07_model_evaluation.py
python src/08_user_behavior_analysis.py
python src/09_dfir_investigation.py
python src/10_dfir_visualization.py
```

The report-generation scripts are:

```bash
python src/11_generate_final_report.py
python src/12_Final_project_Report.py
```

Check each script's configuration and prerequisites before execution. The report generators expect the outputs produced by earlier pipeline stages.

## Evaluation and limitations

- The analysed project inputs do not include a verified ground-truth labels file (`insiders.csv`). Therefore, supervised metrics such as accuracy, precision, recall, F1-score, ROC-AUC and false-positive rate are not reported as validated results.
- The One-Class SVM was trained on a 10,000-row sample due to computational considerations.
- DBSCAN results in the exploratory source material cover a 30,000-row sample only and must not be generalized to the full dataset.
- Agreement between two unsupervised models does not establish correctness.
- Synthetic dataset activity and event metadata require cautious interpretation.
- Anomaly scores are not probabilities and should be interpreted with contextual investigation.
- The selected DFIR sequence does not prove data exfiltration or malicious intent.

## Responsible use

This is an academic research prototype, not a production security control. Do not use anomaly rankings alone to accuse, discipline or make employment decisions about individuals. Any operational use would require validated labels, privacy and legal review, human investigation, documented procedures and careful false-positive evaluation.

## Reproducibility

The scripts use a fixed random state where configured. The chronological split and training-only scaler fitting are intended to reduce temporal leakage. Reproducing results requires the same authorized dataset version, compatible dependencies, expected directory structure and configuration.

## References

- CERT Insider Threat Center, **Insider Threat Test Dataset**. Obtain dataset access and usage terms from the official CERT/SEI distribution source.
- Liu, F. T., Ting, K. M., and Zhou, Z.-H. (2008). *Isolation Forest*. IEEE International Conference on Data Mining.
- Schölkopf, B., Platt, J. C., Shawe-Taylor, J., Smola, A. J., and Williamson, R. C. (2001). *Estimating the Support of a High-Dimensional Distribution*. Neural Computation.

---

**Cybersecurity research project — Insider-Threat Detection using Unsupervised Machine Learning.**
