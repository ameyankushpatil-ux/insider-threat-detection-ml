"""
12_Final_project_Report.py
==========================
Generate the final M.Tech project report (DOCX + PDF), project presentation (PPTX),
and a separate study guide (DOCX + Markdown) from the completed project outputs.

RUN FROM ANY WORKING DIRECTORY:
    python src/12_Final_project_Report.py

EXPECTED PROJECT STRUCTURE:
    project-root/
      src/12_Final_project_Report.py
      assets/iiit_sricity_logo.png       <-- place the ORIGINAL institute logo here
      figures/                           <-- figures 01 to 14 from project pipeline
      results/tables/                    <-- CSV and JSON results
      reports/                           <-- existing phase reports
      data/processed/                    <-- optional supporting CSVs

The script never fabricates an official institute logo. If the original logo is not
present, it uses a clearly-labelled text-only institute heading and reports a warning.

The report is an academic project-report draft. Add institute-mandated certificate,
declaration, plagiarism statement, supervisor signature and formatting before submission.
"""

from __future__ import annotations

import json
import math
import re
import sys
import textwrap
from pathlib import Path
from datetime import datetime

# ----------------------------- Dependency checks -----------------------------

REQUIRED = {
    "pandas": "pandas",
    "docx": "python-docx",
    "reportlab": "reportlab",
    "pptx": "python-pptx",
    "PIL": "Pillow",
}

missing = []
for module, package in REQUIRED.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(package)

if missing:
    print("\n[ERROR] Missing Python packages:", ", ".join(missing))
    print("Install them inside your project virtual environment:")
    print("    python -m pip install pandas python-docx reportlab python-pptx Pillow")
    raise SystemExit(1)

import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage,
    Table as RLTable, TableStyle, KeepTogether
)

from pptx import Presentation
from pptx.util import Inches as PInches, Pt as PPt
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from PIL import Image as PILImage

# ----------------------------- Project configuration -------------------------

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ASSETS = ROOT / "assets"
FIGURES = ROOT / "figures"
TABLES = ROOT / "results" / "tables"
PREDICTIONS = ROOT / "results" / "predictions"
REPORTS = ROOT / "reports"
PROCESSED = ROOT / "data" / "processed"

for folder in (ASSETS, REPORTS):
    folder.mkdir(parents=True, exist_ok=True)

TITLE = (
    "Insider-Threat Detection Using Unsupervised Machine Learning "
    "and Behavioural Anomaly Analysis"
)
INSTITUTE = "Indian Institute of Information Technology, Sri City"
PROGRAMME = "M.Tech. Cyber Security"
COURSE_INSTRUCTOR = "Dr. Amilpur Santhosh"
ACADEMIC_YEAR = "2026–2027"

STUDENTS = [
    ("Amey Patil", "OMCS25S00059"),
    ("Omkar Patil", "OMCS25S00055"),
    ("Chaitanya Sukasi", "OMCS25S00086"),
]

# Put the original institute logo at this path. PNG with transparent background is ideal.
LOGO = ASSETS / "iiit_sricity_logo.png"

OUT_DOCX = REPORTS / "12_Insider_Threat_MTech_Final_Report.docx"
OUT_PDF = REPORTS / "12_Insider_Threat_MTech_Final_Report.pdf"
OUT_PPTX = REPORTS / "12_Insider_Threat_Project_Presentation.pptx"
OUT_STUDY_DOCX = REPORTS / "12_Insider_Threat_Project_Study_Guide.docx"
OUT_STUDY_MD = REPORTS / "12_Insider_Threat_Project_Study_Guide.md"

# ----------------------------- Helpers ---------------------------------------

def log(message: str) -> None:
    print(f"[12-FINAL] {message}")

def read_json(filename: str) -> dict:
    path = TABLES / filename
    if not path.exists():
        log(f"Optional JSON not found: {path.relative_to(ROOT)}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"Could not parse {filename}: {exc}")
        return {}

def read_csv(filename: str) -> pd.DataFrame:
    path = TABLES / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        log(f"Could not read {filename}: {exc}")
        return pd.DataFrame()

def safe_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)

def add_page_number(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)

def set_cell_shading(cell, fill="DCE6F1"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)

def add_docx_table(doc, df: pd.DataFrame, max_rows=25, max_cols=8):
    if df.empty:
        doc.add_paragraph("[No corresponding table was found in results/tables.]")
        return
    view = df.head(max_rows).copy()
    view = view.iloc[:, :max_cols]
    table = doc.add_table(rows=1, cols=len(view.columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, column in enumerate(view.columns):
        cell = table.rows[0].cells[i]
        cell.text = str(column).replace("_", " ").title()
        set_cell_shading(cell)
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(8)
    for _, row in view.iterrows():
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = safe_text(value)[:100]
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(7.5)
    doc.add_paragraph()

def add_docx_figure(doc, filename, caption, width=6.0):
    path = FIGURES / filename
    if not path.exists():
        doc.add_paragraph(f"[Figure not found: {filename}]")
        return
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.add_run().add_picture(str(path), width=Inches(width))
    cap = doc.add_paragraph(caption)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap.runs:
        run.italic = True
        run.font.size = Pt(8)

def add_pdf_table(story, df, max_rows=20, max_cols=7):
    if df.empty:
        return
    view = df.head(max_rows).iloc[:, :max_cols]
    data = [[str(c).replace("_", " ").title() for c in view.columns]]
    data.extend([[safe_text(v)[:55] for v in row] for row in view.itertuples(index=False, name=None)])
    table = RLTable(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("LEADING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([table, Spacer(1, 4 * mm)])

def add_pdf_figure(story, filename, caption, max_width=170*mm, max_height=220*mm):
    path = FIGURES / filename
    if not path.exists():
        return
    img = RLImage(str(path))
    scale = min(max_width / img.imageWidth, max_height / img.imageHeight, 1.0)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    story.extend([img, Spacer(1, 2*mm), Paragraph(caption, PDF_STYLES["caption"]), Spacer(1, 3*mm)])

def add_docx_bullets(doc, items):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")

def logo_available() -> bool:
    if not LOGO.exists():
        return False
    try:
        with PILImage.open(LOGO) as img:
            img.verify()
        return True
    except Exception:
        log("Logo file exists but is not a readable image. It will be omitted.")
        return False

def add_cover_logo_docx(doc):
    if logo_available():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(LOGO), width=Inches(1.2))
    else:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("IIIT SRI CITY")
        r.bold = True
        r.font.size = Pt(20)
        r.font.color.rgb = RGBColor(31, 78, 121)
        p = doc.add_paragraph(
            "[Insert the official IIIT Sri City logo: assets/iiit_sricity_logo.png]"
        )
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.italic = True
            run.font.size = Pt(8)

def add_cover_logo_pdf(story):
    if logo_available():
        story.append(RLImage(str(LOGO), width=28*mm, height=28*mm))
    else:
        story.append(Paragraph("IIIT SRI CITY", PDF_STYLES["cover_inst"]))
        story.append(Paragraph(
            "[Official logo will be inserted when assets/iiit_sricity_logo.png is supplied.]",
            PDF_STYLES["small_center"]
        ))

def add_cover_logo_ppt(slide):
    if logo_available():
        slide.shapes.add_picture(str(LOGO), PInches(5.95), PInches(0.35), height=PInches(1.35))
    else:
        box = slide.shapes.add_textbox(PInches(4.5), PInches(0.45), PInches(4.3), PInches(0.55))
        para = box.text_frame.paragraphs[0]
        para.text = "IIIT SRI CITY"
        para.alignment = PP_ALIGN.CENTER
        para.font.size = PPt(24)
        para.font.bold = True
        para.font.color.rgb = PRGB(31, 78, 121)

# ----------------------------- Project evidence ------------------------------

FEATURES = [
    "login_count", "logoff_count", "unique_pc_count",
    "after_hours_login_count", "after_hours_logoff_count",
    "device_activity_count", "after_hours_device_activity",
    "file_access_count", "after_hours_file_access",
    "zip_file_count", "exe_file_count", "pdf_file_count",
    "email_count", "attachment_count", "total_email_size",
    "after_hours_email_count", "unique_recipients",
    "web_activity_count", "unique_domains", "after_hours_web_activity",
]

MODEL_COMPARISON = [
    ("Isolation Forest", 621, 0.93),
    ("One-Class SVM", 1702, 2.55),
    ("Two-model consensus", 487, 0.73),
]

CHAPTERS = [
("Abstract", [
"This project implements an unsupervised behavioural anomaly-detection workflow using the CERT Insider Threat Test Dataset r4.2. User-day activity is represented using 20 behavioural features derived from logon, device, file, email and HTTP activity. The integrated dataset contains 342,706 user-day records for 1,000 users, spanning 2 January 2010 to 17 May 2011.",
"A chronological split separates 275,893 training records (2 January 2010–5 February 2011) from 66,813 test records (6 February–17 May 2011). Selected non-negative features are log1p-transformed. StandardScaler is fitted on training data only. Isolation Forest and One-Class SVM are trained and evaluated on the later period; One-Class SVM fitting uses a 10,000-record sample for computational practicality.",
"Isolation Forest flags 621 test records (0.93%), One-Class SVM flags 1,702 (2.55%), and both flag 487 (0.73%). Jaccard overlap is 0.2653. A detailed case study reconstructs 169 source events for PWS0219 on 15 February 2011 and compares the day with 282 historical user-day observations. Verified ground-truth labels were unavailable, so outputs are investigation candidates rather than confirmed insider threats."
]),
("1. Introduction and Background", [
"An insider threat involves harmful, risky or policy-violating activity performed by a person or account that already has some level of legitimate access. The source of risk may be a malicious insider, a compromised account, negligence or an accidental action. Insider-threat detection is difficult because the activity may use approved identities, endpoints and applications.",
"Security teams collect high volumes of endpoint, identity, file, email and web telemetry. Rule-based detections remain useful for known patterns, but may not identify subtle deviations or may create excessive alerts. Behavioural analytics provides a complementary approach by learning patterns from historical activity and prioritising observations that differ from those patterns."
]),
("2. Problem Statement", [
"Given multi-source enterprise activity logs and no verified label for every user-day, how can a reproducible analytical pipeline identify and prioritise unusual user behaviour, compare complementary unsupervised detectors, and preserve traceability to source events for analyst review—without treating statistical deviation as proof of malicious intent?",
"The system must validate and integrate heterogeneous telemetry, build user-day features, prevent temporal data leakage, learn from an earlier period, score a later period, combine model outputs transparently and reconstruct selected observations at event level."
]),
("3. Why the Problem Is Difficult", [
"Legitimate and malicious actions can look similar in logs. High file activity may reflect a genuine deadline; unusual device activity may be normal for an administrator; and a compromised account may deliberately remain within ordinary activity ranges.",
"User behaviour differs by job role, seniority, department, work schedule, location and workload. A single global threshold may therefore flag legitimate work while missing a subtle deviation. Logs are distributed across systems with different schemas, timestamps and levels of detail. Raw event volumes can also create memory and runtime constraints.",
"Ground-truth labels are often incomplete or unavailable. Without verified labels, supervised metrics such as precision, recall, F1-score, ROC-AUC and false-positive rate cannot be reported honestly. An anomaly score measures deviation under a model; it does not reveal intent or prove data theft."
]),
("4. Motivation and Need", [
"This project is designed as a security-operations triage aid. It narrows a large dataset to a ranked set of unusual user-day records and retains an auditable path from model output to source events. This can help analysts decide where contextual investigation may be useful.",
"Unsupervised learning is appropriate for this experimental setting because the available processed dataset did not contain a verified ground-truth insiders.csv label file. The system therefore does not pretend that all unusual activity is malicious and does not train on invented labels."
]),
("5. Objectives and Scope", [
"1. Inventory and validate CERT r4.2 user-day data and source telemetry.",
"2. Engineer behavioural features from logon/logoff, devices, files, email and web activity.",
"3. Explore distributions and correlations and remove selected redundant features.",
"4. Use a chronological train-test split and fit preprocessing on training data only.",
"5. Train Isolation Forest and One-Class SVM and compare anomaly outputs.",
"6. Create a transparent consensus ranking and investigate a selected candidate using raw events and a user-specific historical baseline.",
"7. Document limitations, privacy controls and future research.",
"Scope is offline analysis of the CERT synthetic dataset. This is not a live enterprise monitoring product, an attribution tool or a proof-of-maliciousness engine."
]),
("6. Dataset and Data Requirements", [
"The available CERT r4.2 source categories include logon, device, file, email, HTTP and LDAP. The integrated processed dataset used in the final pipeline contains 342,706 user-day records, 55 original columns and 1,000 users, with dates from 2010-01-02 to 2011-05-17.",
"Required data elements include a stable user identifier, parseable timestamp, event identifier, host or device context, activity type and selected event metadata. A consistent user-day key is required for aggregation. The project uses metadata and counts rather than retaining raw email or file contents in the case timeline.",
"Validation found zero invalid dates, missing user IDs, duplicate user-day keys, missing selected behavioural values, negative values or infinite values. The available DBSCAN columns covered only a 30,000-row sample and are not treated as full-dataset ground truth."
]),
("7. Feature Engineering and Preprocessing", [
"Twenty numerical features are selected: login_count, logoff_count, unique_pc_count, after_hours_login_count, after_hours_logoff_count, device_activity_count, after_hours_device_activity, file_access_count, after_hours_file_access, zip_file_count, exe_file_count, pdf_file_count, email_count, attachment_count, total_email_size, after_hours_email_count, unique_recipients, web_activity_count, unique_domains and after_hours_web_activity.",
"Selected non-negative skewed features are transformed using log1p, which applies log(1+x) and reduces the influence of very large counts while preserving zero values. User and date metadata are retained outside the model feature matrix.",
"Exploratory correlation analysis identified highly redundant pairs. Examples include device activity and device connect counts, after-hours email count and ratio, and file access count and unique file extensions. Redundancy reduction can improve interpretability and avoid giving nearly duplicated measurements excessive influence; correlation does not establish causation.",
"The chronological split avoids training on future observations and testing on earlier observations. StandardScaler is fitted on the training partition only and applied unchanged to test data. This reduces preprocessing leakage."
]),
("8. Why Isolation Forest?", [
"Isolation Forest is an unsupervised anomaly-detection algorithm based on random isolation trees. It recursively selects a feature and a split value. Observations that are unusual relative to the majority tend to be isolated using fewer splits, producing shorter average path lengths.",
"It was selected because it does not require labelled anomalies, handles multivariate numeric features, can be efficient on large tabular datasets and is suited to identifying sparse unusual combinations of activity. It provides a tree-based isolation perspective that differs from boundary-based methods.",
"Limitations include sensitivity to settings such as number of trees, sample size and contamination; limited understanding of event sequence and business context; potential confusion between legitimate role variation and anomalies; and scores that are not threat probabilities. Correlated or poorly scaled representations can also influence behaviour."
]),
("9. Why One-Class SVM?", [
"One-Class Support Vector Machine learns a boundary around the training data in feature space. With an appropriate kernel, it estimates a region that contains most of the normal training observations; points outside the learned support are marked as outliers.",
"It was selected as a complementary detector because it uses a different modelling assumption from Isolation Forest. Comparing both methods helps reveal which candidate observations are stable across different anomaly-detection approaches. In this implementation it was fitted using a 10,000-record sample of training data to manage computation.",
"Limitations include sensitivity to kernel and hyperparameter choices, the need for feature scaling, potentially high computational cost at scale, sensitivity to contamination in training data and dependence on the sample used to fit the boundary. A single global boundary may not represent users with very different roles."
]),
("10. Consensus Method and Its Limitations", [
"The project intersects the binary anomaly flags from the two models to define a consensus candidate set. It then averages their percentile-normalised anomaly-score ranks to order candidates. This is a transparent ranking heuristic.",
"The consensus score is not a calibrated probability and should not be described as a probability of maliciousness. Requiring agreement can reduce the number of candidates but may miss anomalies identified by only one model. Percentile ranks depend on the evaluated score distribution and do not establish detection accuracy."
]),
("11. Experimental Design and Results", [
"The chronological training partition contains 275,893 records from 2010-01-02 to 2011-02-05. The test partition contains 66,813 records from 2011-02-06 to 2011-05-17. StandardScaler was fitted on training data only. The One-Class SVM used a 10,000-record fitting sample.",
"On the test period, Isolation Forest flagged 621 records (0.93%), One-Class SVM flagged 1,702 records (2.55%), and the two-model intersection contained 487 records (0.73%). Jaccard similarity was 0.2653. Jaccard measures overlap between sets; it is not a measure of accuracy or effectiveness.",
"Since verified ground-truth labels were not available, the project does not report precision, recall, F1-score, ROC-AUC or false-positive rate. The anomaly rates are descriptive outputs of the models and should not be interpreted as true incident rates."
]),
("12. DFIR Case Study: PWS0219, 15 February 2011", [
"The selected user-day was flagged by both models and ranked seventh in the consensus candidate list, with score 0.999573. The reconstruction contains 169 unique source event IDs: 114 HTTP, 23 FILE, 12 LOGON, 10 DEVICE and 10 EMAIL events. The observed event window is 01:18:47 to 22:14:04. The case was compared with 282 historical user-day observations for the same user.",
"After-hours logins and logoffs reached the user's historical maxima. After-hours device activity also reached the historical maximum. File access count was 23, slightly above the historical 95th percentile of 22.95 but below the historical maximum of 35. After-hours file access was 23, above the 95th percentile of 17 but below the maximum of 25. EXE count was 1, equal to the historical maximum of 1. No measured feature exceeded the user's historical maximum.",
"On PC-8955, a logon at 02:15:39 was followed by a device connection at 02:18:24, multiple file events around 02:19–02:23, including ZIP and EXE events, then device disconnection at 02:25:36 and logoff at 02:27:20. This sequence is a lead for investigation; it does not prove file copying or exfiltration.",
"Email count and total email size were below the user's historical medians, and no after-hours email activity was observed. Synthetic HTTP URLs or domains should not be declared malicious based on strings alone. The defensible conclusion is that the day merits contextual review, not that the user committed an insider attack."
]),
("13. Requirements and Reproducibility", [
"Software used in the workflow includes Python, pandas, NumPy, scikit-learn, matplotlib, joblib, python-docx, ReportLab and python-pptx. Hardware must have sufficient RAM for tabular data processing; the project was run on a 16 GB system. The One-Class SVM training sample and batch processing reduce resource pressure.",
"Reproducibility requires preserving the dataset release, feature list, temporal split manifest, scaler and model artifacts, random seeds, model parameters, script versions and derived result tables. The exact algorithm parameters should be taken from the final training scripts and model artifacts; this report generator does not invent missing values.",
"Raw CERT data should not be published in a public Git repository. Share code, non-sensitive derived summaries and instructions for obtaining the dataset under the provider's terms."
]),
("14. Ethical, Privacy and Operational Considerations", [
"Behavioural scores can have serious consequences if misused. The system should support triage and investigation, not automated punishment, employee ranking or access revocation. Analysts should review job role, schedule, approved projects, travel, leave and business context before escalation.",
"Data minimisation is important. The DFIR timeline uses event metadata and excludes raw message and file contents. Access to raw telemetry should be restricted, logged and retained only as required. Reports should clearly communicate uncertainty and preserve human review."
]),
("15. Limitations and Threats to Validity", [
"Verified ground-truth labels were unavailable, so supervised performance metrics cannot be computed. CERT is synthetic and may not represent all production environments. One-Class SVM used a 10,000-record training sample. DBSCAN-related outputs covered only a 30,000-record sample and were not used as full-dataset labels.",
"Consensus scores are relative ranking values, not probabilities. Legitimate role or workload variation can create anomalies. The global user-day representation loses some event sequence detail. Temporal association between device connection and file events does not prove transfer or exfiltration. The selected case has not been verified as a malicious incident."
]),
("16. Future Scope", [
"1. Add verified incident labels and analyst adjudication so precision, recall, F1, ROC-AUC and false-positive rates can be evaluated.",
"2. Develop role-, department- and peer-group-aware baselines to reduce false positives caused by heterogeneous user populations.",
"3. Add sequence-aware features and temporal models to capture order, duration and event transitions rather than daily counts alone.",
"4. Compare scalable alternatives such as Local Outlier Factor, robust covariance methods and autoencoders under controlled evaluation.",
"5. Add explainability using feature contribution summaries, nearest historical days, peer comparisons and evidence timelines.",
"6. Calibrate thresholds using validation data, incorporate analyst feedback and monitor concept drift.",
"7. Evaluate additional datasets and, after privacy and security review, a controlled enterprise pilot with role-based access, audit trails and human approval."
]),
("17. Conclusion", [
"The project implemented an end-to-end unsupervised behavioural anomaly-prioritisation workflow using CERT r4.2. It validated the integrated data, engineered 20 user-day features, used a chronological holdout, trained Isolation Forest and One-Class SVM, compared their outputs and generated a consensus investigation ranking. The PWS0219 case study linked model output to 169 source events and a same-user historical baseline.",
"The work demonstrates a reproducible way to narrow analyst attention when labels are unavailable. It does not establish real-world detection accuracy and does not prove malicious intent in the selected case. The main contribution is the integration of unsupervised scoring with cautious, traceable DFIR investigation."
]),
("References and Study Resources", [
"[1] F. T. Liu, K. M. Ting and Z.-H. Zhou, “Isolation Forest,” Proceedings of the 8th IEEE International Conference on Data Mining, 2008. DOI: 10.1109/ICDM.2008.17.",
"[2] B. Schölkopf et al., “Estimating the Support of a High-Dimensional Distribution,” Neural Computation, vol. 13, no. 7, pp. 1443–1471, 2001. DOI: 10.1162/089976601750264965.",
"[3] F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.",
"[4] CERT Insider Threat Center, Software Engineering Institute, Carnegie Mellon University, Insider Threat Test Dataset r4.2. Follow the provider's terms and citation instructions.",
"[5] NIST SP 800-61 Revision 2, Computer Security Incident Handling Guide, 2012.",
"[6] Scikit-learn User Guide: IsolationForest and OneClassSVM documentation. Use the documentation version matching the environment used for experiments."
]),
]

STUDY_TERMS = [
("Insider threat", "A risk arising from a person or account with legitimate access that is misused, compromised or used negligently. An unusual event alone does not prove insider threat."),
("Behavioural baseline", "A statistical description of observed activity for a user or peer group over a reference period."),
("Anomaly detection", "The task of identifying observations that differ substantially from the patterns learned from data."),
("Unsupervised learning", "Learning structure from data without relying on supplied class labels for each record."),
("User-day record", "An aggregate record representing one user's activity over one calendar day."),
("Feature engineering", "Converting raw events into numerical or categorical variables suitable for analysis or machine learning."),
("log1p transformation", "The transformation log(1+x), often used for non-negative skewed counts; it preserves zero and compresses large values."),
("StandardScaler", "A preprocessing method that centres features using the training mean and scales them using the training standard deviation."),
("Data leakage", "The unintended use of information from the test/future period during training or preprocessing, leading to overly optimistic evaluation."),
("Isolation Forest", "An anomaly detector that isolates observations with random trees; unusual points often have shorter average path lengths."),
("One-Class SVM", "A boundary-based detector that estimates the support of the training distribution and identifies points outside that support."),
("Contamination", "A model setting or assumption related to the expected proportion of anomalies; it is not a verified incident rate."),
("Kernel", "A function used by an SVM to represent similarity and implicitly map observations into a feature space."),
("Anomaly score", "A model-derived measure of how unusual an observation is under the fitted model; not automatically a probability."),
("Consensus detection", "Combining outputs from multiple detectors, here by requiring both models to flag a record."),
("Percentile rank", "A relative position in a score distribution; it indicates ranking, not probability of harm."),
("Jaccard similarity", "Intersection size divided by union size for two sets; here it measures overlap between detector anomaly sets."),
("DFIR", "Digital Forensics and Incident Response: evidence preservation, event reconstruction, analysis and response."),
("Historical percentile", "A comparison of a case value with the distribution of that user's historical observations."),
("False positive", "An alert that is treated as positive by a detector but is not a true incident; without labels, the project's false-positive rate is unknown."),
("Concept drift", "A change over time in the data-generating behaviour that can make a previously learned model less representative."),
("Human-in-the-loop", "A workflow where an analyst reviews model outputs and context before a consequential decision."),
]

Q_AND_A = [
("Why did you choose unsupervised learning?",
 "The available processed dataset did not include verified ground-truth labels for the user-day records. Unsupervised learning allows us to model deviations without inventing labels. The outputs are leads for analyst review, not confirmed incidents."),
("Why did you choose Isolation Forest?",
 "It is designed for anomaly detection, works without labels, handles multivariate tabular data and is generally practical for larger datasets. Unusual observations can be isolated in fewer random tree splits."),
("Why did you also use One-Class SVM?",
 "It provides a different, boundary-based view of normality. Comparing it with Isolation Forest helps assess overlap and model sensitivity. In this project it was trained on a 10,000-row sample for computational practicality."),
("Why use a chronological split?",
 "It reflects the operational direction of time: learn from earlier activity and evaluate on later activity. It also reduces the risk of random splitting mixing future observations into training."),
("Why fit the scaler only on training data?",
 "The test period must not influence preprocessing. Fitting on training only prevents information from the held-out future period leaking into the training pipeline."),
("What does 0.2653 Jaccard similarity mean?",
 "It means the two model anomaly sets overlap by 0.2653 under the intersection-over-union definition. It is an agreement measure, not accuracy."),
("Does a consensus score of 0.999573 mean 99.9573% probability of an insider threat?",
 "No. It is a percentile-normalised ranking score used to prioritise candidates. It is not calibrated as a probability."),
("Can you report precision, recall or F1?",
 "Not responsibly with the available materials because verified ground-truth labels were not available. Those metrics require known true labels."),
("What is the main limitation of Isolation Forest?",
 "Its output depends on parameters and representation, and a global model may confuse legitimate role differences with anomalies. It does not infer intent or understand all event sequences."),
("What is the main limitation of One-Class SVM?",
 "It can be computationally expensive and sensitive to kernel, hyperparameter, scaling and training-sample choices."),
("Why investigate PWS0219?",
 "It was flagged by both detectors and ranked seventh in the consensus list. The project then reconstructed its raw events and compared it with the user's historical activity."),
("Did PWS0219 exfiltrate data?",
 "The evidence does not establish that. A device connection followed by file events is a temporal association and an investigation lead, not proof of copying or exfiltration."),
("What is the project's contribution?",
 "A reproducible pipeline joining validated user-day features, temporal evaluation, two complementary unsupervised detectors, transparent consensus ranking and traceable DFIR review."),
("How would you improve it?",
 "Add verified labels and analyst adjudication, peer-group baselines, sequence-aware features, explainability, calibrated thresholds, drift monitoring and evaluation on additional datasets."),
]

FIGURE_LIST = [
("01_zero_activity_analysis.png", "Zero-activity analysis across selected behavioural features."),
("02_feature_distributions.png", "Distributions of selected behavioural features."),
("03_spearman_correlation.png", "Spearman correlation matrix used to inspect redundancy."),
("04_monthly_activity_trends.png", "Monthly behavioural activity trends."),
("05_model_anomaly_rates.png", "Anomaly rates produced by the two detectors and consensus."),
("06_model_agreement.png", "Agreement and disagreement between model outputs."),
("07_daily_anomaly_trends.png", "Daily anomaly trends in the chronological test period."),
("08_anomaly_score_distributions.png", "Anomaly score distributions."),
("09_top_anomalous_users.png", "Users with the highest number of consensus anomaly days."),
("10_daily_anomaly_rates.png", "Daily consensus anomaly rates."),
("11_PWS0219_event_timeline.png", "PWS0219 raw-event timeline."),
("12_PWS0219_hourly_activity.png", "PWS0219 hourly event activity."),
("13_PWS0219_historical_percentiles.png", "PWS0219 feature values compared with historical percentiles."),
("14_PWS0219_case_vs_baseline.png", "PWS0219 case-day activity compared with its historical baseline."),
]

# ----------------------------- DOCX generation -------------------------------

def make_docx():
    log("Generating Word report...")
    ev = read_json("model_evaluation_summary.json")
    case = read_json("PWS0219_DFIR_summary.json")

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(6)
    for name in ("Heading 1", "Heading 2", "Heading 3"):
        doc.styles[name].font.name = "Calibri"
        doc.styles[name].font.color.rgb = RGBColor(31, 78, 121)
        doc.styles[name].font.bold = True
    doc.styles["Heading 1"].font.size = Pt(16)
    doc.styles["Heading 2"].font.size = Pt(12)

    add_cover_logo_docx(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(INSTITUTE.upper())
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor(31, 78, 121)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(PROGRAMME).bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(25)
    r = p.add_run(TITLE)
    r.bold = True
    r.font.size = Pt(21)
    r.font.color.rgb = RGBColor(31, 78, 121)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("\nProject Report submitted in partial fulfilment of the requirements\n")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Submitted by\n").bold = True
    for name, roll in STUDENTS:
        p = doc.add_paragraph(f"{name}  |  {roll}")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("\nCourse Instructor\n").bold = True
    p.add_run(COURSE_INSTRUCTOR)
    p = doc.add_paragraph(f"\n{INSTITUTE}\n{ACADEMIC_YEAR}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()
    doc.add_heading("Important Submission Checklist", 0)
    add_docx_bullets(doc, [
        "Replace or verify the logo using the official institute file at assets/iiit_sricity_logo.png.",
        "Insert institute-prescribed certificate, declaration, plagiarism statement and signature pages if required.",
        "Verify course code, semester, project type, supervisor/instructor designation and academic year with the department.",
        "Verify exact model parameters and random seeds against src/06_model_training.py before final submission.",
        "Check page breaks, figure readability, table widths and reference style in Word and exported PDF.",
        "Do not upload CERT raw data to public repositories; follow dataset terms.",
    ])
    doc.add_heading("Contents", 0)
    for title, _ in CHAPTERS:
        doc.add_paragraph(title, style="List Number")

    doc.add_page_break()
    for title, paragraphs in CHAPTERS:
        doc.add_heading(title, level=1)
        for text in paragraphs:
            if re.match(r"^\d+\.", text):
                doc.add_paragraph(text, style="List Number")
            else:
                p = doc.add_paragraph(text)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if title.startswith("11. Experimental"):
            doc.add_heading("Model comparison summary", level=2)
            add_docx_table(doc, read_csv("model_comparison.csv"))
            add_docx_table(doc, read_csv("model_agreement_summary.csv"))
        if title.startswith("12. DFIR"):
            doc.add_heading("Source-event counts", level=2)
            add_docx_table(doc, read_csv("PWS0219_event_source_counts.csv"))
            doc.add_heading("Historical baseline comparison", level=2)
            add_docx_table(doc, read_csv("PWS0219_historical_baseline.csv"), max_rows=25)

    doc.add_heading("Project Figures", level=1)
    for filename, caption in FIGURE_LIST:
        if (FIGURES / filename).exists():
            doc.add_heading(caption, level=2)
            add_docx_figure(doc, filename, filename, width=6.0)

    for sec in doc.sections:
        header = sec.header.paragraphs[0]
        header.text = "IIIT SRI CITY  |  M.TECH CYBER SECURITY PROJECT"
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in header.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(110, 110, 110)
        footer = sec.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("Insider-Threat Detection Project  |  ")
        add_page_number(footer)

    doc.save(OUT_DOCX)
    log(f"Word report saved: {OUT_DOCX}")

# ----------------------------- PDF generation --------------------------------

PDF_STYLES = getSampleStyleSheet()
PDF_STYLES.add(ParagraphStyle(
    name="cover_title_custom", parent=PDF_STYLES["Title"], fontName="Helvetica-Bold",
    fontSize=18, leading=23, textColor=colors.HexColor("#1F4E79"),
    alignment=TA_CENTER, spaceAfter=12
))
PDF_STYLES.add(ParagraphStyle(
    name="cover_inst", parent=PDF_STYLES["Normal"], fontName="Helvetica-Bold",
    fontSize=13, leading=17, textColor=colors.HexColor("#1F4E79"),
    alignment=TA_CENTER, spaceAfter=8
))
PDF_STYLES.add(ParagraphStyle(
    name="small_center", parent=PDF_STYLES["Normal"], fontSize=8,
    alignment=TA_CENTER, textColor=colors.grey
))
PDF_STYLES.add(ParagraphStyle(
    name="chapter_custom", parent=PDF_STYLES["Heading1"], fontName="Helvetica-Bold",
    fontSize=13, leading=16, textColor=colors.HexColor("#1F4E79"),
    spaceBefore=9, spaceAfter=6
))
PDF_STYLES.add(ParagraphStyle(
    name="body_custom", parent=PDF_STYLES["BodyText"], fontName="Helvetica",
    fontSize=8.7, leading=12, alignment=TA_JUSTIFY, spaceAfter=6
))
PDF_STYLES.add(ParagraphStyle(
    name="caption_custom", parent=PDF_STYLES["BodyText"], fontSize=8,
    leading=10, alignment=TA_CENTER, italic=True, spaceAfter=6
))

def pdf_escape(text):
    return (safe_text(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\n", "<br/>"))

def pdf_footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(
        A4[0] / 2, 10 * mm,
        f"IIIT Sri City | M.Tech Cyber Security | Page {document.page}"
    )
    canvas.restoreState()

def make_pdf():
    log("Generating PDF report...")
    story = [Spacer(1, 10*mm)]
    add_cover_logo_pdf(story)
    story.extend([
        Paragraph(INSTITUTE.upper(), PDF_STYLES["cover_inst"]),
        Paragraph(PROGRAMME, PDF_STYLES["small_center"]),
        Spacer(1, 12*mm),
        Paragraph(TITLE, PDF_STYLES["cover_title_custom"]),
        Paragraph("Project Report", PDF_STYLES["small_center"]),
        Spacer(1, 8*mm),
        Paragraph("<b>Submitted by</b>", PDF_STYLES["small_center"]),
    ])
    for name, roll in STUDENTS:
        story.append(Paragraph(pdf_escape(f"{name} — {roll}"), PDF_STYLES["small_center"]))
    story.extend([
        Spacer(1, 5*mm),
        Paragraph(pdf_escape(f"Course Instructor: {COURSE_INSTRUCTOR}"), PDF_STYLES["small_center"]),
        Paragraph(pdf_escape(INSTITUTE), PDF_STYLES["small_center"]),
        Paragraph(pdf_escape(ACADEMIC_YEAR), PDF_STYLES["small_center"]),
        PageBreak(),
        Paragraph("Submission checklist", PDF_STYLES["chapter_custom"]),
    ])
    for item in [
        "Insert the original institute logo if it has not been supplied.",
        "Add institute-required certificate, declaration and signature pages.",
        "Verify course, semester, instructor designation and academic year.",
        "Check model parameters against the final training source code.",
        "Inspect figures, tables, page breaks and references before submission.",
    ]:
        story.append(Paragraph("• " + pdf_escape(item), PDF_STYLES["body_custom"]))

    for title, paragraphs in CHAPTERS:
        story.append(Paragraph(pdf_escape(title), PDF_STYLES["chapter_custom"]))
        for paragraph in paragraphs:
            story.append(Paragraph(pdf_escape(paragraph), PDF_STYLES["body_custom"]))
        if title.startswith("11. Experimental"):
            story.append(Paragraph("Model comparison table", PDF_STYLES["body_custom"]))
            add_pdf_table(story, read_csv("model_comparison.csv"))
        if title.startswith("12. DFIR"):
            story.append(Paragraph("Historical baseline table", PDF_STYLES["body_custom"]))
            add_pdf_table(story, read_csv("PWS0219_historical_baseline.csv"), max_rows=22)

    story.append(Paragraph("Project Figures", PDF_STYLES["chapter_custom"]))
    for filename, caption in FIGURE_LIST:
        if (FIGURES / filename).exists():
            story.append(Paragraph(pdf_escape(caption), PDF_STYLES["body_custom"]))
            add_pdf_figure(story, filename, filename)

    pdf = SimpleDocTemplate(
        str(OUT_PDF), pagesize=A4,
        rightMargin=17*mm, leftMargin=17*mm,
        topMargin=17*mm, bottomMargin=18*mm
    )
    pdf.build(story, onFirstPage=pdf_footer, onLaterPages=pdf_footer)
    log(f"PDF report saved: {OUT_PDF}")

# ----------------------------- Study guide -----------------------------------

def make_study_guide():
    log("Generating separate project study guide...")
    md = [
        f"# Project Study Guide: {TITLE}",
        "",
        f"**Institute:** {INSTITUTE}  ",
        f"**Course:** {PROGRAMME}  ",
        f"**Course Instructor:** {COURSE_INSTRUCTOR}",
        "",
        "## How to use this guide",
        "Use this as a viva and presentation preparation companion. It explains the terms used in the project, the design choices, the actual results and the limits of the evidence. Where the project outputs do not provide verified labels, do not claim supervised accuracy.",
        "",
        "## Key project facts",
        "- Dataset: CERT Insider Threat Test Dataset r4.2.",
        "- Integrated data: 342,706 user-day records, 1,000 users.",
        "- Date range: 2010-01-02 to 2011-05-17.",
        "- Training: 275,893 records, ending 2011-02-05.",
        "- Testing: 66,813 records, starting 2011-02-06.",
        "- Features: 20 behavioural features; log1p transformation.",
        "- Scaler: StandardScaler fitted on training data only.",
        "- Models: Isolation Forest and One-Class SVM; OCSVM fit on 10,000 training samples.",
        "- Results: IF 621 (0.93%); OCSVM 1,702 (2.55%); consensus 487 (0.73%).",
        "- Jaccard overlap: 0.2653; this is overlap, not accuracy.",
        "- Ground truth: verified labels were unavailable.",
        "- DFIR case: PWS0219, 2011-02-15; 169 source events; 282 historical user-day observations.",
        "",
        "## Concepts and terminology",
    ]
    for term, definition in STUDY_TERMS:
        md.extend([f"### {term}", definition, ""])
    md.append("## Viva questions and suggested answers")
    for q, a in Q_AND_A:
        md.extend([f"### {q}", a, ""])
    md.extend([
        "## Recommended study order",
        "1. Understand the insider-threat problem and why labels are missing.",
        "2. Learn the user-day dataset structure and the 20 features.",
        "3. Understand log1p, StandardScaler and temporal leakage.",
        "4. Learn the intuition, assumptions and limitations of Isolation Forest.",
        "5. Learn the intuition, assumptions and limitations of One-Class SVM.",
        "6. Explain the chronological split, model outputs and Jaccard overlap.",
        "7. Walk through the PWS0219 case without overstating the evidence.",
        "8. Prepare to discuss limitations, ethics and future work.",
        "",
        "## References to study",
        "- Liu, Ting & Zhou (2008), Isolation Forest, IEEE ICDM.",
        "- Schölkopf et al. (2001), Estimating the Support of a High-Dimensional Distribution.",
        "- Pedregosa et al. (2011), Scikit-learn: Machine Learning in Python.",
        "- CERT Insider Threat Center, Insider Threat Test Dataset r4.2 documentation.",
        "- NIST SP 800-61 Rev. 2, Computer Security Incident Handling Guide.",
        "- Scikit-learn official documentation for IsolationForest, OneClassSVM and StandardScaler.",
        "",
        "## Important statements to use during viva",
        "- “The model identifies statistical deviations, not malicious intent.”",
        "- “The consensus score is a relative ranking score, not a probability.”",
        "- “We did not report precision, recall or F1 because verified ground-truth labels were unavailable.”",
        "- “The PC/device/file sequence is an investigation lead, not proof of exfiltration.”",
        "- “Our contribution is a reproducible prioritisation and DFIR workflow.”",
    ])
    OUT_STUDY_MD.write_text("\n".join(md), encoding="utf-8")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading("Project Study Guide and Viva Preparation", 0)
    doc.add_paragraph(TITLE)
    doc.add_paragraph(f"{INSTITUTE} | {PROGRAMME} | Course Instructor: {COURSE_INSTRUCTOR}")
    doc.add_heading("Key project facts", 1)
    add_docx_bullets(doc, [
        "CERT r4.2; 342,706 user-day records; 1,000 users.",
        "Train 275,893; test 66,813; chronological split.",
        "20 selected features; log1p transform; training-only StandardScaler.",
        "Isolation Forest: 621 anomalies (0.93%).",
        "One-Class SVM: 1,702 anomalies (2.55%); trained on 10,000-row sample.",
        "Consensus: 487 (0.73%); Jaccard overlap 0.2653, not accuracy.",
        "No verified ground-truth labels were available.",
        "PWS0219 case: 169 events and 282 historical user-day observations.",
    ])
    doc.add_heading("Concepts and terminology", 1)
    for term, definition in STUDY_TERMS:
        doc.add_heading(term, 2)
        doc.add_paragraph(definition)
    doc.add_heading("Viva questions and suggested answers", 1)
    for question, answer in Q_AND_A:
        doc.add_heading(question, 2)
        doc.add_paragraph(answer)
    doc.add_heading("Recommended study order", 1)
    add_docx_bullets(doc, [
        "Problem and motivation; why unsupervised learning is appropriate.",
        "Dataset structure, source logs and 20 behavioural features.",
        "Feature engineering, log1p, scaling and temporal leakage.",
        "Isolation Forest and One-Class SVM intuition and limitations.",
        "Experimental split, anomaly rates, consensus and Jaccard overlap.",
        "PWS0219 case interpretation and evidence limitations.",
        "Ethics, future scope and research contribution.",
    ])
    doc.add_heading("References to study", 1)
    add_docx_bullets(doc, [
        "Liu, Ting & Zhou (2008), Isolation Forest, IEEE ICDM.",
        "Schölkopf et al. (2001), Estimating the Support of a High-Dimensional Distribution.",
        "Pedregosa et al. (2011), Scikit-learn: Machine Learning in Python.",
        "CERT Insider Threat Center, Insider Threat Test Dataset r4.2 documentation.",
        "NIST SP 800-61 Rev. 2, Computer Security Incident Handling Guide.",
        "Scikit-learn documentation for IsolationForest, OneClassSVM and StandardScaler.",
    ])
    doc.save(OUT_STUDY_DOCX)
    log(f"Study guide saved: {OUT_STUDY_DOCX}")
    log(f"Study guide Markdown saved: {OUT_STUDY_MD}")

# ----------------------------- PowerPoint ------------------------------------

def ppt_background(slide, prs):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = PRGB(255, 255, 255)
    shape.line.fill.background()
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, PInches(0.12)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRGB(0, 130, 145)
    bar.line.fill.background()

def ppt_title(slide, title, subtitle=None):
    box = slide.shapes.add_textbox(PInches(0.65), PInches(0.32), PInches(12), PInches(0.62))
    p = box.text_frame.paragraphs[0]
    p.text = title
    p.font.size = PPt(25)
    p.font.bold = True
    p.font.color.rgb = PRGB(31, 78, 121)
    if subtitle:
        sub = slide.shapes.add_textbox(PInches(0.68), PInches(0.98), PInches(11.8), PInches(0.35))
        sp = sub.text_frame.paragraphs[0]
        sp.text = subtitle
        sp.font.size = PPt(10)
        sp.font.color.rgb = PRGB(0, 130, 145)

def ppt_bullets(slide, items, font_size=19, x=0.85, y=1.5, w=11.7, h=5.5):
    box = slide.shapes.add_textbox(PInches(x), PInches(y), PInches(w), PInches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = PInches(0.12)
    for index, item in enumerate(items):
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.text = item
        para.level = 0
        para.font.size = PPt(font_size)
        para.font.color.rgb = PRGB(45, 52, 60)
        para.space_after = PPt(12)

def make_ppt():
    log("Generating PowerPoint presentation...")
    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    blank = prs.slide_layouts[6]

    slide = prs.slides.add_slide(blank)
    ppt_background(slide, prs)
    add_cover_logo_ppt(slide)
    title_box = slide.shapes.add_textbox(PInches(0.8), PInches(1.95), PInches(11.8), PInches(1.35))
    p = title_box.text_frame.paragraphs[0]
    p.text = TITLE
    p.alignment = PP_ALIGN.CENTER
    p.font.size = PPt(26)
    p.font.bold = True
    p.font.color.rgb = PRGB(31, 78, 121)
    detail = slide.shapes.add_textbox(PInches(1), PInches(3.55), PInches(11.3), PInches(3.1))
    tf = detail.text_frame
    tf.clear()
    for idx, (name, roll) in enumerate(STUDENTS):
        para = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        para.text = f"{name} — {roll}"
        para.alignment = PP_ALIGN.CENTER
        para.font.size = PPt(17)
    para = tf.add_paragraph()
    para.text = f"Course Instructor: {COURSE_INSTRUCTOR}"
    para.alignment = PP_ALIGN.CENTER
    para.font.size = PPt(16)
    para.font.bold = True
    para = tf.add_paragraph()
    para.text = f"{INSTITUTE} | {PROGRAMME}"
    para.alignment = PP_ALIGN.CENTER
    para.font.size = PPt(14)

    slides = [
        ("Research Context", [
            "Insider activity can occur through valid accounts and authorised systems.",
            "Atypical activity may be malicious, accidental, compromised-account activity or legitimate work.",
            "The system prioritises records for human investigation; it does not automatically declare guilt."
        ]),
        ("Problem Statement", [
            "How can multi-source user activity be converted into a reproducible anomaly-prioritisation workflow when verified labels are unavailable?",
            "The workflow must avoid temporal leakage, compare detectors and preserve traceability to source events."
        ]),
        ("Why Is It Difficult?", [
            "Legitimate and harmful actions can look similar in telemetry.",
            "Behaviour differs by role, schedule, workload and business context.",
            "Logs are high-volume, heterogeneous and distributed across systems.",
            "Ground-truth labels are incomplete or absent; anomaly is not synonymous with maliciousness."
        ]),
        ("Why This Project Is Needed", [
            "Static rules detect known patterns but may miss subtle deviations.",
            "Unsupervised learning can learn a baseline without requiring every record to be labelled.",
            "A ranked shortlist helps analysts focus effort while retaining human judgement."
        ]),
        ("Dataset and Requirements", [
            "CERT Insider Threat Test Dataset r4.2; 342,706 user-day records; 1,000 users.",
            "Date range: 02 Jan 2010–17 May 2011; sources include logon, device, file, email and HTTP.",
            "Requirements: user IDs, timestamps, event IDs, activity metadata, Python and sufficient memory.",
            "No verified insiders.csv ground-truth labels were available."
        ]),
        ("Feature Engineering", [
            "20 user-day features across identity/session, endpoint/file, email and web activity.",
            "log1p reduces skew in non-negative count features while preserving zero.",
            "Redundant variables were removed after correlation analysis.",
            "User and date are metadata, not model inputs."
        ]),
        ("Why Isolation Forest?", [
            "Random isolation trees separate observations; rare patterns tend to be isolated in fewer splits.",
            "Works without labels and is practical for multivariate tabular data.",
            "Useful for detecting sparse combinations of behavioural counts.",
            "Limitations: parameter sensitivity, limited context/sequence understanding and role-blind global baselines."
        ]),
        ("Why One-Class SVM?", [
            "Learns a boundary around the training distribution in feature space.",
            "Provides a different modelling assumption from tree-based isolation.",
            "Complementary outputs allow comparison of model sensitivity and agreement.",
            "Limitations: scaling/kernel sensitivity, computational cost and dependence on the 10,000-row training sample."
        ]),
        ("Pipeline and Evaluation", [
            "Raw telemetry → validation → user-day aggregation → feature selection → log1p.",
            "Chronological split; StandardScaler fitted on training only.",
            "Isolation Forest and One-Class SVM score the later test period.",
            "Model flags and percentile ranks are combined into a consensus investigation ranking."
        ]),
        ("Chronological Split", [
            "Train: 275,893 records (02 Jan 2010–05 Feb 2011).",
            "Test: 66,813 records (06 Feb 2011–17 May 2011).",
            "Training-only scaling reduces future-data leakage.",
            "One-Class SVM was fitted on a 10,000-record training sample."
        ]),
        ("Results", [
            "Isolation Forest: 621 test anomalies (0.93%).",
            "One-Class SVM: 1,702 test anomalies (2.55%).",
            "Both models: 487 records (0.73%).",
            "Jaccard overlap: 0.2653 — overlap only, not accuracy."
        ]),
        ("Consensus Ranking", [
            "The intersection of the two model flags forms the consensus candidate set.",
            "Anomaly scores are converted to percentile ranks and averaged.",
            "The resulting value orders investigation priority; it is not a threat probability.",
            "Consensus can miss anomalies detected by only one model."
        ]),
        ("DFIR Case: PWS0219", [
            "Date: 15 February 2011; consensus rank 7; score 0.999573.",
            "169 unique source events: 114 HTTP, 23 FILE, 12 LOGON, 10 DEVICE and 10 EMAIL.",
            "Compared with 282 historical user-day observations for the same user.",
            "No measured feature exceeded the user's historical maximum."
        ]),
        ("Evidence Interpretation", [
            "After-hours login/logoff and device activity reached historical maxima.",
            "File access 23 exceeded p95 22.95 but remained below max 35.",
            "After-hours file access 23 exceeded p95 17 but remained below max 25.",
            "Device connection followed by file events is a lead, not proof of copying or exfiltration.",
            "Email count and size were below historical medians; no after-hours email activity was observed."
        ]),
        ("Limitations and Validity", [
            "No verified labels: precision, recall, F1, ROC-AUC and false-positive rate cannot be calculated.",
            "CERT is synthetic; findings may not generalise directly to production enterprises.",
            "One-Class SVM used a 10,000-record sample; DBSCAN fields covered only a 30,000-row sample.",
            "Consensus scores are rankings, not probabilities; context and human review remain essential."
        ]),
        ("Ethics and Privacy", [
            "Use outputs for triage, not automated punishment or access revocation.",
            "Minimise content collection; preserve event metadata and audit access.",
            "Review role, schedule, approved work and business context before escalation.",
            "Communicate uncertainty and preserve human review."
        ]),
        ("Future Scope", [
            "Add verified labels and analyst adjudication for valid performance metrics.",
            "Build role-aware and peer-group baselines; add sequence-aware modelling.",
            "Add explainability, calibrated thresholds, drift monitoring and feedback loops.",
            "Evaluate additional datasets and controlled enterprise pilots."
        ]),
        ("Conclusion", [
            "A reproducible unsupervised pipeline was implemented using two complementary detectors.",
            "Consensus narrowed the test-period candidate set and supported a traceable DFIR case study.",
            "The contribution is investigation prioritisation—not proof of malicious insider activity."
        ]),
        ("Selected References", [
            "Liu, Ting & Zhou (2008), Isolation Forest, IEEE ICDM.",
            "Schölkopf et al. (2001), Estimating the Support of a High-Dimensional Distribution.",
            "Pedregosa et al. (2011), Scikit-learn: Machine Learning in Python.",
            "CERT Insider Threat Center, Insider Threat Test Dataset r4.2.",
            "NIST SP 800-61 Rev. 2, Computer Security Incident Handling Guide."
        ]),
        ("Questions", ["Thank you", "Questions and discussion"])
    ]

    for title, bullets in slides:
        slide = prs.slides.add_slide(blank)
        ppt_background(slide, prs)
        ppt_title(slide, title)
        ppt_bullets(slide, bullets, font_size=17 if len(bullets) >= 4 else 19)
        # Insert selected figures on dedicated result/evidence slides when available.
        if title == "Results" and (FIGURES / "05_model_anomaly_rates.png").exists():
            slide.shapes.add_picture(
                str(FIGURES / "05_model_anomaly_rates.png"),
                PInches(7.45), PInches(2.0), width=PInches(4.9)
            )
        if title == "DFIR Case: PWS0219" and (FIGURES / "11_PWS0219_event_timeline.png").exists():
            slide.shapes.add_picture(
                str(FIGURES / "11_PWS0219_event_timeline.png"),
                PInches(7.2), PInches(2.1), width=PInches(5.1)
            )

    prs.save(OUT_PPTX)
    log(f"PowerPoint saved: {OUT_PPTX}")

# ----------------------------- Final validation ------------------------------

def validate_outputs():
    log("Validating generated files...")
    expected = [OUT_DOCX, OUT_PDF, OUT_PPTX, OUT_STUDY_DOCX, OUT_STUDY_MD]
    failures = []
    for path in expected:
        if not path.exists() or path.stat().st_size < 1000:
            failures.append(str(path))
        else:
            print(f"  OK  {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")
    if failures:
        raise RuntimeError("Output validation failed: " + ", ".join(failures))

    # Check figure coverage and remind if any expected figures are absent.
    missing_figures = [name for name, _ in FIGURE_LIST if not (FIGURES / name).exists()]
    if missing_figures:
        log("Some figures were not found; report will contain fewer figures:")
        for name in missing_figures:
            print("   -", name)

    if not logo_available():
        log("ORIGINAL LOGO NOT FOUND.")
        log("Place the official image at: assets/iiit_sricity_logo.png")
        log("Run this script again; the logo will then be inserted into DOCX, PDF and PPTX.")

def main():
    print("=" * 78)
    print("IIIT SRI CITY — FINAL M.TECH PROJECT DOCUMENT GENERATOR")
    print(TITLE)
    print("=" * 78)
    print("Project root:", ROOT)
    print("Students:")
    for name, roll in STUDENTS:
        print(f"  - {name} ({roll})")
    print("Course Instructor:", COURSE_INSTRUCTOR)
    print()

    make_docx()
    make_pdf()
    make_study_guide()
    make_ppt()
    validate_outputs()

    print("\n" + "=" * 78)
    print("ALL GENERATION STEPS COMPLETED")
    print("Open the output folder with:")
    print(f'    explorer "{REPORTS}"')
    print("=" * 78)

if __name__ == "__main__":
    main()
