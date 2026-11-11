"""Generate editable DOCX and PDF dissertation reports from this project.
Run from project root: python src/11_generate_final_report.py
"""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
R, T, F = ROOT/"reports", ROOT/"results"/"tables", ROOT/"figures"
R.mkdir(exist_ok=True)
DOCX, PDF = R/"Insider_Threat_Detection_MTech_Dissertation.docx", R/"Insider_Threat_Detection_MTech_Dissertation.pdf"
TITLE = "Insider-Threat Detection Using Unsupervised Machine Learning and Behavioural Anomaly Analysis"
STUDENT, ROLL, INSTITUTE, SUPERVISOR = "[Student Name]", "[Roll Number]", "[Institute Name]", "[Supervisor Name]"
PROGRAMME, YEAR = "M.Tech. Cyber Security", "2026"

def js(name):
    p=T/name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
def csv(name):
    p=T/name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()
def val(d,k,default):
    return d.get(k,default) if isinstance(d,dict) else default
def add_table_doc(doc, df, limit=22):
    if df.empty:
        doc.add_paragraph("[Table not available in generated project outputs.]"); return
    df=df.head(limit)
    if len(df.columns)>8: df=df.iloc[:,:8]
    tb=doc.add_table(rows=1, cols=len(df.columns)); tb.style="Light Shading Accent 1"
    for i,c in enumerate(df.columns):
        tb.rows[0].cells[i].text=str(c).replace("_"," ").title()
        shd=OxmlElement("w:shd"); shd.set(qn("w:fill"),"D9EAF7")
        tb.rows[0].cells[i]._tc.get_or_add_tcPr().append(shd)
    for _,row in df.iterrows():
        cells=tb.add_row().cells
        for i,x in enumerate(row):
            cells[i].text="" if pd.isna(x) else str(x)[:90]
    doc.add_paragraph()
def add_fig_doc(doc,name,caption):
    p=F/name
    if p.exists():
        para=doc.add_paragraph(); para.alignment=WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(str(p),width=Inches(6.0))
        cap=doc.add_paragraph(caption); cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for r in cap.runs: r.italic=True; r.font.size=Pt(9)
    else: doc.add_paragraph(f"[Missing figure: {name}]")

def make_docx():
    ev=js("model_evaluation_summary.json"); case=js("PWS0219_DFIR_summary.json")
    d=Document(); sec=d.sections[0]
    sec.top_margin=Inches(.7); sec.bottom_margin=Inches(.7)
    d.styles["Normal"].font.name="Calibri"; d.styles["Normal"].font.size=Pt(10.5)
    for s in ["Heading 1","Heading 2"]:
        d.styles[s].font.color.rgb=RGBColor(31,78,121)
    p=d.add_paragraph(); p.alignment=1; p.paragraph_format.space_before=Pt(70)
    r=p.add_run(INSTITUTE.upper()); r.bold=True; r.font.size=Pt(16)
    p=d.add_paragraph(); p.alignment=1; p.paragraph_format.space_before=Pt(45)
    r=p.add_run(TITLE); r.bold=True; r.font.size=Pt(21); r.font.color.rgb=RGBColor(31,78,121)
    for line in ["\nA Dissertation Submitted in Partial Fulfilment of the Requirements",
                 f"for the Award of {PROGRAMME}",f"\nSubmitted by: {STUDENT}",f"Roll Number: {ROLL}",
                 f"\nSupervisor: {SUPERVISOR}",f"\nAcademic Year: {YEAR}"]:
        p=d.add_paragraph(line); p.alignment=1
    d.add_page_break()
    d.add_heading("Declaration and Institutional Details",1)
    d.add_paragraph("Replace the editable placeholders and insert the institute-prescribed declaration, certificate, plagiarism statement, and formatting.")
    d.add_heading("Abstract",1)
    d.add_paragraph("This project develops an unsupervised behavioural anomaly-detection workflow using the CERT Insider Threat Test Dataset r4.2. User-day features are engineered from endpoint, logon, file, email, and web activity. A chronological train-test split is used, with StandardScaler fitted only on training data. Isolation Forest and One-Class SVM are evaluated on a held-out period. Their outputs are compared and combined into a consensus investigation-priority score. A DFIR investigation of PWS0219 on 15 February 2011 reconstructs 169 source events and compares the case day with 282 historical user-day observations. Verified ground-truth labels were unavailable; therefore, outputs are investigation leads rather than confirmed insider-threat classifications.")
    d.add_paragraph("Keywords: insider threat; behavioural analytics; anomaly detection; Isolation Forest; One-Class SVM; CERT dataset; digital forensics.")
    d.add_heading("Chapter 1 — Introduction",1)
    d.add_heading("1.1 Background and Problem Statement",2)
    d.add_paragraph("Insider-threat detection is challenging because potentially harmful actions may be performed using valid accounts and authorised access. Behavioural anomaly detection can identify activity that differs from learned patterns, but unusual behaviour is not necessarily malicious. This project investigates unsupervised methods to prioritise user-day observations when verified labels are unavailable.")
    d.add_heading("1.2 Objectives",2)
    for x in ["Inspect and validate CERT r4.2 telemetry and processed features.","Engineer behavioural user-day features from endpoint and communication activity.","Train Isolation Forest and One-Class SVM models.","Evaluate chronologically and compare anomaly outputs.","Prioritise consensus candidates and reconstruct a selected case at event level."]:
        d.add_paragraph(x,style="List Bullet")
    d.add_heading("Chapter 2 — Dataset and Data Validation",1)
    d.add_paragraph("The available CERT r4.2 telemetry includes logon, device, file, email, HTTP, and LDAP data. The processed dataset contains 342,706 user-day records across 1,000 users, spanning 2010-01-02 to 2011-05-17. A verified insiders.csv ground-truth file was not available. Therefore, supervised metrics such as precision, recall, F1-score, ROC-AUC, and false-positive rate cannot be reported.")
    d.add_paragraph("Validation reported zero invalid dates, missing user IDs, duplicate user-days, missing behavioural values, negative values, or infinite values in the selected behavioural features. DBSCAN fields covered only a 30,000-row sample.")
    d.add_heading("Chapter 3 — Feature Engineering and Exploratory Analysis",1)
    d.add_paragraph("Twenty behavioural features were selected to represent logon/logoff activity, computer diversity, after-hours activity, device events, file access and selected extensions, email volume and size, recipient diversity, and web activity/domain diversity. A log1p transformation was applied to selected non-negative features. Redundant variables were excluded based on exploratory correlation analysis; correlation is not causation.")
    for n,c in [("01_zero_activity_analysis.png","Figure 1. Zero-activity analysis."),("02_feature_distributions.png","Figure 2. Behavioural feature distributions."),("03_spearman_correlation.png","Figure 3. Spearman correlation matrix."),("04_monthly_activity_trends.png","Figure 4. Monthly activity trends.")]: add_fig_doc(d,n,c)
    d.add_heading("Chapter 4 — Experimental Design and Models",1)
    d.add_heading("4.1 Chronological Split",2)
    d.add_paragraph("Training contained 275,893 records from 2010-01-02 to 2011-02-05. Testing contained 66,813 records from 2011-02-06 to 2011-05-17. StandardScaler was fitted only on training data and applied to the test partition.")
    d.add_heading("4.2 Isolation Forest",2)
    d.add_paragraph("Isolation Forest identifies observations that are isolated with shorter average path lengths in random isolation trees. The model was trained on the training partition and scored on the chronological test partition.")
    
    d.add_heading("4.3 One-Class SVM", 2)
    d.add_paragraph(
        "One-Class SVM estimates a boundary around the training distribution. "
        "Observations outside the learned support are treated as outliers. "
        "Fitting used a 10,000-record training sample for computational "
        "practicality, with test scoring performed in batches."
    )

    d.add_heading("4.4 Consensus Ranking", 2)
    d.add_paragraph(
        "Consensus candidates are records flagged by both models. Candidate "
        "ranking uses the mean of the two test-set anomaly-score percentile "
        "ranks. This is a relative ranking measure, not a probability of "
        "malicious activity."
    )

    d.add_heading("Chapter 5 — Results and Model Comparison", 1)
    d.add_paragraph(
        f"Test records: {ev.get('test_records', 66813):,}. "
        f"Isolation Forest: {ev.get('isolation_forest_anomalies', 621):,} "
        f"({ev.get('isolation_forest_rate_percent', 0.9295):.2f}%). "
        f"One-Class SVM: {ev.get('ocsvm_anomalies', 1702):,} "
        f"({ev.get('ocsvm_rate_percent', 2.5474):.2f}%). "
        f"Consensus: {ev.get('both_models_flagged', 487):,} "
        f"({ev.get('consensus_rate_percent', 0.7289):.2f}%). "
        f"Jaccard similarity: {ev.get('jaccard_similarity', 0.265251):.4f}. "
        "Jaccard measures overlap, not accuracy."
    )
    add_table_doc(d, csv("model_comparison.csv"))

    for n, c in [
        ("05_model_anomaly_rates.png", "Figure 5. Model anomaly rates."),
        ("06_model_agreement.png", "Figure 6. Model agreement."),
        ("07_daily_anomaly_trends.png", "Figure 7. Daily anomaly trends."),
        ("08_anomaly_score_distributions.png", "Figure 8. Anomaly-score distributions."),
        ("09_top_anomalous_users.png", "Figure 9. Top consensus-anomalous users."),
        ("10_daily_anomaly_rates.png", "Figure 10. Daily anomaly rates.")
    ]:
        add_fig_doc(d, n, c)

    d.add_heading("Chapter 6 — DFIR Case Study: PWS0219", 1)
    d.add_paragraph(
        f"The selected case was ranked {case.get('consensus_rank', 7)} "
        f"and flagged by both models. Its consensus score was "
        f"{case.get('consensus_score', 0.999573):.6f}, a relative ranking "
        "score rather than a calibrated threat probability. The reconstruction "
        "contained 169 events: 114 HTTP, 23 FILE, 12 LOGON, 10 DEVICE, "
        "and 10 EMAIL. All 169 original event IDs were preserved uniquely."
    )

    add_table_doc(d, csv("PWS0219_event_source_counts.csv"))

    for n, c in [
        ("11_PWS0219_event_timeline.png", "Figure 11. PWS0219 source-event timeline."),
        ("12_PWS0219_hourly_activity.png", "Figure 12. Hourly event activity."),
        ("13_PWS0219_historical_percentiles.png", "Figure 13. Tie-aware historical percentiles."),
        ("14_PWS0219_case_vs_baseline.png", "Figure 14. Case day versus historical baseline.")
    ]:
        add_fig_doc(d, n, c)

    d.add_heading("6.1 Historical Behavioural Baseline", 2)
    d.add_paragraph(
        "The case day was compared with 282 historical user-day observations. "
        "A tie-aware midrank percentile was used. None of the 20 case features "
        "exceeded the historical maximum. After-hours file access was 23, "
        "above the historical 95th percentile of 17 but below the maximum "
        "of 25. Total file access was 23, slightly above its 95th percentile "
        "of 22.95 but below the maximum of 35. EXE count was 1, equal to "
        "the historical maximum of 1."
    )
    add_table_doc(d, csv("PWS0219_historical_baseline.csv"), 25)

    d.add_heading("6.2 Event Interpretation", 2)
    d.add_paragraph(
        "A logon and device connection on PC-8955 were followed by file-access "
        "events, including ZIP and EXE events, then device disconnection and "
        "logoff. This temporal sequence is an investigative lead only; it does "
        "not prove copying, removable-media transfer, or exfiltration. Email "
        "volume and total email size were below historical medians, and no "
        "after-hours email activity was observed."
    )

    d.add_heading("Chapter 7 — Discussion", 1)
    d.add_paragraph(
        "The workflow integrates feature engineering, chronological evaluation, "
        "model agreement, and traceable event-level investigation. The selected "
        "case ranked highly in the ensemble while none of its 20 compared "
        "features exceeded the user's historical maximum. This demonstrates "
        "why model scores require contextual analyst review."
    )

    d.add_heading("Chapter 8 — Limitations and Threats to Validity", 1)
    for x in [
        "Verified ground-truth labels were unavailable; supervised metrics cannot be calculated.",
        "CERT data is synthetic and may not represent every operational enterprise environment.",
        "One-Class SVM fitting used a 10,000-record sample.",
        "DBSCAN outputs covered only a 30,000-record sample.",
        "Consensus scores are relative rankings, not calibrated probabilities.",
        "Legitimate role or workload variation may create anomalies.",
        "Temporal association does not establish intent or exfiltration."
    ]:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Chapter 9 — Conclusion and Future Work", 1)
    d.add_paragraph(
        "The project implemented an unsupervised behavioural anomaly-prioritisation "
        "workflow using CERT r4.2. Isolation Forest and One-Class SVM generated "
        "complementary anomaly outputs, and consensus reduced the candidate set "
        "for investigation. The PWS0219 case study demonstrated traceable "
        "source-event reconstruction and historical comparison. The evidence "
        "supports prioritising unusual observations for analyst review, not "
        "concluding that the selected user committed malicious activity. "
        "Future work includes verified labels, analyst feedback, role-aware "
        "peer groups, sequence-based features, explainability, calibrated "
        "thresholds, and evaluation on additional datasets."
    )

    d.add_heading("References", 1)
    references = [
        "Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. "
        "IEEE International Conference on Data Mining, 413–422. "
        "https://doi.org/10.1109/ICDM.2008.17",
        "Schölkopf, B., et al. (2001). Estimating the support of a "
        "high-dimensional distribution. Neural Computation, 13(7), "
        "1443–1471. https://doi.org/10.1162/089976601750264965",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. "
        "Journal of Machine Learning Research, 12, 2825–2830.",
        "Carnegie Mellon University Software Engineering Institute. "
        "Insider Threat Test Dataset, Release 4.2. "
        "https://doi.org/10.1184/R1/12841247.v1",
        "NIST. (2012). Computer Security Incident Handling Guide, "
        "SP 800-61 Revision 2. https://doi.org/10.6028/NIST.SP.800-61r2"
    ]
    for ref in references:
        d.add_paragraph(ref, style="List Number")

    d.add_heading("Appendix — Reproducibility", 1)
    d.add_paragraph(
        "Run the project scripts from the project root with the virtual "
        "environment activated. Preserve the raw dataset locally. Record "
        "Python and package versions, random seeds, configuration parameters, "
        "and the exact dataset release. Update institutional placeholders "
        "and apply the institute's prescribed dissertation formatting."
    )

    d.save(DOCX)
    print("Created DOCX:", DOCX)


def make_pdf():
    ev = js("model_evaluation_summary.json")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"], fontSize=18,
        leading=23, alignment=TA_CENTER,
        textColor=colors.HexColor("#1F4E79")
    )
    heading_style = ParagraphStyle(
        "ChapterHeading", parent=styles["Heading1"],
        fontSize=13, leading=16,
        textColor=colors.HexColor("#1F4E79"),
        spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"],
        fontSize=8.5, leading=12,
        alignment=TA_JUSTIFY, spaceAfter=6
    )
    caption_style = ParagraphStyle(
        "FigureCaption", parent=styles["BodyText"],
        fontSize=8, leading=10, alignment=TA_CENTER,
        spaceAfter=8
    )

    story = [
        Spacer(1, 35 * mm),
        Paragraph(INSTITUTE, heading_style),
        Spacer(1, 15 * mm),
        Paragraph(TITLE, title_style),
        Spacer(1, 12 * mm),
        Paragraph(
            f"A dissertation submitted for {PROGRAMME}<br/><br/>"
            f"Submitted by: {STUDENT}<br/>Roll Number: {ROLL}<br/><br/>"
            f"Supervisor: {SUPERVISOR}<br/><br/>Academic Year: {YEAR}",
            body_style
        ),
        PageBreak()
    ]

    def heading(text):
        story.append(Paragraph(text, heading_style))

    def paragraph(text):
        story.append(Paragraph(text, body_style))

    def figure(name, caption):
        path = F / name
        if path.exists():
            img = Image(str(path))
            scale = min(
                (165 * mm) / img.imageWidth,
                (190 * mm) / img.imageHeight,
                1.0
            )
            img.drawWidth = img.imageWidth * scale
            img.drawHeight = img.imageHeight * scale
            story.extend([img, Paragraph(caption, caption_style)])

    def table_from_csv(df):
        if df.empty:
            return
        df = df.head(20)
        if len(df.columns) > 7:
            df = df.iloc[:, :7]
        data = [[str(c).replace("_", " ").title() for c in df.columns]]
        for _, row in df.iterrows():
            data.append([
                str("" if pd.isna(v) else v)[:45]
                for v in row.tolist()
            ])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.extend([table, Spacer(1, 4 * mm)])

    heading("Abstract")
    paragraph(
        "This project develops an unsupervised behavioural anomaly-detection "
        "workflow using CERT r4.2 user-day telemetry. Isolation Forest and "
        "One-Class SVM are evaluated using a chronological holdout. A DFIR "
        "investigation of PWS0219 on 15 February 2011 reconstructs 169 source "
        "events and compares the case with 282 historical user-day observations. "
        "Verified labels were unavailable; outputs are investigation leads, "
        "not confirmed insider-threat classifications."
    )

    heading("Chapter 1 — Introduction")
    paragraph(
        "Potentially harmful insider actions may use valid accounts and "
        "authorised access. Behavioural anomaly detection can prioritise "
        "deviations from learned patterns, but unusual behaviour is not "
        "necessarily malicious."
    )

    heading("Chapter 2 — Dataset and Validation")
    paragraph(
        "Available CERT r4.2 telemetry includes logon, device, file, email, "
        "HTTP, and LDAP sources. The processed dataset contains 342,706 "
        "user-day records across 1,000 users from 2010-01-02 to 2011-05-17. "
        "A verified insiders.csv label file was unavailable, so supervised "
        "metrics are not reported."
    )

    heading("Chapter 3 — Feature Engineering and EDA")
    paragraph(
        "Twenty behavioural features were selected and transformed using "
        "log1p. Redundant variables were excluded based on exploratory "
        "correlation analysis. Correlation is not causation."
    )
    for n, c in [
        ("01_zero_activity_analysis.png", "Figure 1. Zero-activity analysis."),
        ("02_feature_distributions.png", "Figure 2. Feature distributions."),
        ("03_spearman_correlation.png", "Figure 3. Spearman correlation."),
        ("04_monthly_activity_trends.png", "Figure 4. Monthly activity.")
    ]:
        figure(n, c)

    heading("Chapter 4 — Experimental Design")
    paragraph(
        "Training contained 275,893 records from 2010-01-02 to 2011-02-05; "
        "testing contained 66,813 records from 2011-02-06 to 2011-05-17. "
        "Scaling was fitted only on training data. One-Class SVM used a "
        "10,000-record fitting sample. Consensus ranking averages the two "
        "test-set anomaly-score percentile ranks and is not a probability."
    )

    heading("Chapter 5 — Results")
    paragraph(
        f"On {ev.get('test_records', 66813):,} test records, Isolation Forest "
        f"flagged {ev.get('isolation_forest_anomalies', 621):,} "
        f"({ev.get('isolation_forest_rate_percent', 0.9295):.2f}%), "
        f"One-Class SVM flagged {ev.get('ocsvm_anomalies', 1702):,} "
        f"({ev.get('ocsvm_rate_percent', 2.5474):.2f}%), and consensus "
        f"flagged {ev.get('both_models_flagged', 487):,} "
        f"({ev.get('consensus_rate_percent', 0.7289):.2f}%). "
        f"Jaccard similarity was {ev.get('jaccard_similarity', 0.265251):.4f}; "
        "it measures overlap, not accuracy."
    )
    table_from_csv(csv("model_comparison.csv"))

    for n, c in [
        ("05_model_anomaly_rates.png", "Figure 5. Model anomaly rates."),
        ("06_model_agreement.png", "Figure 6. Model agreement."),
        ("07_daily_anomaly_trends.png", "Figure 7. Daily anomaly trends."),
        ("08_anomaly_score_distributions.png", "Figure 8. Score distributions."),
        ("09_top_anomalous_users.png", "Figure 9. Top consensus users."),
        ("10_daily_anomaly_rates.png", "Figure 10. Daily anomaly rates.")
    ]:
        figure(n, c)

    heading("Chapter 6 — DFIR Case Study: PWS0219")
    paragraph(
        "PWS0219 was ranked seventh and flagged by both models, with "
        "consensus score approximately 0.999573. The reconstruction contained "
        "169 events: 114 HTTP, 23 FILE, 12 LOGON, 10 DEVICE, and 10 EMAIL. "
        "All 169 event IDs were unique."
    )
    for n, c in [
        ("11_PWS0219_event_timeline.png", "Figure 11. Event timeline."),
        ("12_PWS0219_hourly_activity.png", "Figure 12. Hourly activity."),
        ("13_PWS0219_historical_percentiles.png", "Figure 13. Tie-aware historical percentiles."),
        ("14_PWS0219_case_vs_baseline.png", "Figure 14. Case versus baseline.")
    ]:
        figure(n, c)

    heading("Historical Baseline")
    paragraph(
        "The case day was compared with 282 historical user-day observations. "
        "None of the 20 features exceeded the historical maximum. After-hours "
        "file access was 23, above the 95th percentile of 17 but below maximum "
        "25. Total file access was 23, slightly above the 95th percentile of "
        "22.95 but below maximum 35. EXE count was 1, equal to historical "
        "maximum 1."
    )
    table_from_csv(csv("PWS0219_historical_baseline.csv"))
    paragraph(
        "A logon/device/file/disconnect sequence is an investigative lead, "
        "not proof of copying or exfiltration. Email volume and size were "
        "below historical medians, and no after-hours email activity was observed."
    )

    heading("Chapter 7 — Discussion")
    paragraph(
        "The selected case ranked highly while none of its 20 compared features "
        "exceeded the user's historical maximum, demonstrating why model scores "
        "require contextual analyst review."
    )

    heading("Chapter 8 — Limitations")
    paragraph(
        "No verified ground-truth labels were available; CERT is synthetic; "
        "One-Class SVM used a 10,000-record sample; DBSCAN covered only a "
        "30,000-row sample; consensus scores are not probabilities; legitimate "
        "variation may cause anomalies; and temporal association does not "
        "establish intent."
    )

    heading("Chapter 9 — Conclusion and Future Work")
    paragraph(
        "The workflow prioritises unusual observations for analyst review; "
        "it does not establish that PWS0219 committed malicious activity. "
        "Future work includes verified labels, analyst feedback, role-aware "
        "peer groups, sequence features, explainability, calibrated thresholds, "
        "and evaluation on additional datasets."
    )

    heading("References")
    for ref in [
        "Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. IEEE ICDM. https://doi.org/10.1109/ICDM.2008.17",
        "Schölkopf, B., et al. (2001). Estimating the support of a high-dimensional distribution. Neural Computation. https://doi.org/10.1162/089976601750264965",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. JMLR, 12, 2825–2830.",
        "CMU Software Engineering Institute. CERT Insider Threat Test Dataset r4.2. https://doi.org/10.1184/R1/12841247.v1",
        "NIST (2012). Computer Security Incident Handling Guide, SP 800-61 Rev. 2. https://doi.org/10.6028/NIST.SP.800-61r2"
    ]:
        paragraph(ref)

    SimpleDocTemplate(
        str(PDF), pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=17 * mm, bottomMargin=18 * mm,
        title=TITLE
    ).build(story)

    print("Created PDF:", PDF)


if __name__ == "__main__":
    print("Generating dissertation reports...")
    make_docx()
    make_pdf()
    print("REPORT GENERATION COMPLETED.")
