#!/usr/bin/env python3
"""
Generate synthetic engineering documents for the Offline Engineering-Docs
Assistant assignment (Task: "Data you need" -> synthetic documents).

Produces, under data/synthetic/:
  1. EQSPEC-RADAR-100_RevA.pdf   - equipment specification (Rev A)
  2. EQSPEC-RADAR-100_RevB.pdf   - same spec, Rev B, with 4 changed values
  3. TESTREPORT-TR-2231.pdf      - test report referencing the spec
  4. TESTREPORT-TR-2240.pdf      - second test report (a FAIL case)
  5. ECN-0458.pdf                - engineering change notice
  6. ECN-0461.pdf                - second ECN
  7. MAINT-MANUAL-PWR-SUPPLY.docx- maintenance manual extract
  8. EQSPEC-POWERSUPPLY-200.pdf  - second equipment spec (for cross-doc Qs)
  9. CONFIDENTIAL-SUPPLIER-ASSESSMENT.pdf - marked/restricted document
  10. SYN-MILSTD-810-SUMMARY.pdf  - synthetic stand-in for a MIL-STD-810H-style
                                    environmental test summary (NOT the real
                                    standard - see README; a placeholder with
                                    invented numbers so the tool has an
                                    "environmental test" style doc to search)
  11. SYN-NASA-SEHB-EXCERPT.pdf   - synthetic stand-in excerpt in the style of
                                    the NASA Systems Engineering Handbook
                                    (definitions of requirement/verification
                                    terms), invented wording, not copied text.
  12. SYN-FAA-AC-EXCERPT.pdf      - synthetic stand-in FAA-Advisory-Circular-
                                    style short circular.

All "SYN-*" documents are clearly synthetic placeholders created because this
sandboxed build environment has no network access to the real public sources.
See scripts/fetch_real_docs.py and README.md "Documents" section for how to
replace them with the real public documents on a machine with internet
access.
"""
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document as DocxDocument

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=8)
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
MARK = ParagraphStyle("Mark", parent=styles["Normal"], fontSize=9,
                       textColor=colors.red, spaceAfter=10)


def build_pdf(filename, flow):
    path = os.path.join(OUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=LETTER,
                             topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                             leftMargin=0.8 * inch, rightMargin=0.8 * inch)
    doc.build(flow)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# 1 & 2. Equipment specification, Rev A and Rev B (with changed values)
# ---------------------------------------------------------------------------
def spec_flow(revision, op_temp_low, op_temp_high, max_altitude, voltage_limit,
              weight_kg, vib_duration_hours):
    f = []
    f.append(Paragraph(f"EQUIPMENT SPECIFICATION — RADAR-100 ({revision})", H1))
    f.append(Paragraph("Document No: EQSPEC-RADAR-100 &nbsp;&nbsp; Classification: UNCLASSIFIED", BODY))
    f.append(Spacer(1, 12))

    f.append(Paragraph("1. Scope", H2))
    f.append(Paragraph(
        "This specification defines the performance, environmental, safety and "
        "interface requirements for the RADAR-100 surveillance radar unit, "
        "for use by the engineering and test teams.", BODY))

    f.append(Paragraph("2. Applicable Documents", H2))
    f.append(Paragraph(
        "2.1 This specification references MIL-STD-810H for environmental "
        "test methods and MIL-STD-461G for electromagnetic interference "
        "limits.", BODY))

    f.append(Paragraph("3. Requirements", H2))
    f.append(Paragraph("3.1 Performance Requirements", H2))
    f.append(Paragraph(
        "3.1.1 The unit shall detect a 1 square meter radar cross-section "
        "target at a minimum range of 45 kilometers under clear-weather "
        "conditions.", BODY))
    f.append(Paragraph(
        "3.1.2 The unit shall complete a full 360-degree azimuth scan in "
        "no more than 4 seconds.", BODY))
    f.append(Paragraph(
        "3.1.3 The unit shall achieve a range resolution of 15 meters or "
        "better.", BODY))
    f.append(Paragraph(
        f"3.1.4 The unit shall operate continuously for 500 hours between "
        f"scheduled maintenance actions.", BODY))

    f.append(Paragraph("3.2 Environmental Requirements", H2))
    f.append(Paragraph(
        f"3.2.1 The unit shall operate within an ambient temperature range "
        f"of {op_temp_low}°C to {op_temp_high}°C without degradation in "
        f"performance (reference: MIL-STD-810H, Method 501.7 and 502.7).", BODY))
    f.append(Paragraph(
        f"3.2.2 The unit shall withstand random vibration testing for a "
        f"minimum duration of {vib_duration_hours} hours per axis, per "
        f"MIL-STD-810H Method 514.8, Category 4 (equipment category: "
        f"ground, mobile).", BODY))
    f.append(Paragraph(
        f"3.2.3 The unit shall function at altitudes up to {max_altitude} "
        f"meters above mean sea level per MIL-STD-810H Method 500.6.", BODY))
    f.append(Paragraph(
        "3.2.4 The unit shall meet IP65 ingress protection rating for dust "
        "and water resistance.", BODY))

    f.append(Paragraph("3.3 Electrical Requirements", H2))
    f.append(Paragraph(
        f"3.3.1 The unit shall operate from a nominal 28 VDC supply and "
        f"shall tolerate transients up to {voltage_limit} V without damage, "
        f"per MIL-STD-461G, CS116.", BODY))
    f.append(Paragraph(
        "3.3.2 The unit shall not exceed 850 W average power consumption "
        "in Mode 1 (search) and 1200 W in Mode 2 (track).", BODY))
    f.append(Paragraph(
        "3.3.3 The unit shall limit conducted emissions per MIL-STD-461G, "
        "CE102, across the 10 kHz to 10 MHz band.", BODY))

    f.append(Paragraph("3.4 Safety Requirements", H2))
    f.append(Paragraph(
        "3.4.1 The unit shall provide an emergency stop control that removes "
        "all RF transmission within 200 milliseconds of activation, per "
        "MIL-STD-882E hazard mitigation guidance.", BODY))
    f.append(Paragraph(
        "3.4.2 The unit shall not present an electric shock hazard exceeding "
        "the limits of MIL-STD-882E, Table III, Severity Category II.", BODY))
    f.append(Paragraph(
        "3.4.3 The unit shall include interlocks that prevent high-voltage "
        "access panels from being opened while the transmitter is energized.", BODY))

    f.append(Paragraph("3.5 Interface Requirements", H2))
    f.append(Paragraph(
        "3.5.1 The unit shall provide a MIL-STD-1553B data bus interface for "
        "command and telemetry.", BODY))
    f.append(Paragraph(
        "3.5.2 The unit shall provide a 10/100BASE-T Ethernet maintenance "
        "port, connector type P/N 7741-0032.", BODY))
    f.append(Paragraph(
        f"3.5.3 The unit shall not exceed a total mass of {weight_kg} kg "
        f"including mounting hardware.", BODY))
    f.append(Paragraph(
        "3.5.4 The unit shall provide a visual BITE (built-in test "
        "equipment) status indicator visible from 3 meters.", BODY))

    f.append(Paragraph("3.6 Reliability Requirements", H2))
    f.append(Paragraph(
        "3.6.1 The unit shall achieve a Mean Time Between Failures (MTBF) of "
        "no less than 2,000 hours.", BODY))
    f.append(Paragraph(
        "3.6.2 The unit shall achieve a Mean Time To Repair (MTTR) of no "
        "more than 30 minutes for line-replaceable unit swaps.", BODY))

    f.append(Paragraph("4. Verification", H2))
    f.append(Paragraph(
        "4.1 All requirements in Section 3 shall be verified by test, "
        "analysis, inspection, or demonstration as recorded in the "
        "associated test report.", BODY))

    f.append(Paragraph("5. Operating Limits Table", H2))
    table_data = [
        ["Parameter", "Mode 1 (Search)", "Mode 2 (Track)", "Unit"],
        ["Operating temperature", f"{op_temp_low} to {op_temp_high}", f"{op_temp_low} to {op_temp_high}", "°C"],
        ["Supply voltage limit", str(voltage_limit), str(voltage_limit), "V"],
        ["Average power", "850", "1200", "W"],
        ["Mass (max)", str(weight_kg), str(weight_kg), "kg"],
        ["Max altitude", str(max_altitude), str(max_altitude), "m MSL"],
    ]
    t = Table(table_data, colWidths=[1.8 * inch, 1.4 * inch, 1.4 * inch, 0.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    f.append(t)
    f.append(Spacer(1, 10))
    f.append(Paragraph(
        f"Document Revision: {revision} &nbsp;&nbsp; Date: "
        f"{'2025-03-10' if revision == 'Rev A' else '2025-09-22'}", BODY))
    return f


build_pdf("EQSPEC-RADAR-100_RevA.pdf", spec_flow(
    "Rev A", op_temp_low=-40, op_temp_high=71, max_altitude=4500,
    voltage_limit=50, weight_kg=38, vib_duration_hours=1))

build_pdf("EQSPEC-RADAR-100_RevB.pdf", spec_flow(
    "Rev B", op_temp_low=-45, op_temp_high=71, max_altitude=6000,
    voltage_limit=60, weight_kg=35.5, vib_duration_hours=2))


# ---------------------------------------------------------------------------
# 3 & 4. Test reports
# ---------------------------------------------------------------------------
def test_report_flow(test_id, date, result_summary, rows, ref_spec="EQSPEC-RADAR-100 Rev B"):
    f = []
    f.append(Paragraph(f"TEST REPORT — {test_id}", H1))
    f.append(Paragraph(f"Test ID: {test_id} &nbsp;&nbsp; Date: {date}", BODY))
    f.append(Paragraph(f"Reference Specification: {ref_spec}", BODY))
    f.append(Spacer(1, 10))
    f.append(Paragraph("1. Test Conditions", H2))
    f.append(Paragraph(
        "1.1 Ambient temperature 23°C, relative humidity 45%, test chamber "
        "calibrated per internal procedure QA-04. Vibration tests performed "
        "on a tri-axial electrodynamic shaker per MIL-STD-810H Method 514.8.", BODY))
    f.append(Paragraph("2. Results", H2))
    table_data = [["Req. No.", "Requirement", "Measured", "Limit", "Result"]] + rows
    t = Table(table_data, colWidths=[0.7 * inch, 2.0 * inch, 1.1 * inch, 1.1 * inch, 0.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    f.append(t)
    f.append(Spacer(1, 10))
    f.append(Paragraph(f"3. Summary: {result_summary}", H2))
    return f


build_pdf("TESTREPORT-TR-2231.pdf", test_report_flow(
    "TR-2231", "2025-10-02",
    "Overall PASS. All measured values within Rev B limits.",
    [
        ["3.2.1", "Operating temperature range", "-45 to 71 °C", "-45 to 71 °C", "PASS"],
        ["3.2.2", "Vibration duration per axis", "2.0 hours", ">= 2.0 hours", "PASS"],
        ["3.2.3", "Max operating altitude", "6000 m", "6000 m", "PASS"],
        ["3.3.1", "Voltage transient tolerance", "58 V", "<= 60 V", "PASS"],
        ["3.5.3", "Mass", "35.1 kg", "<= 35.5 kg", "PASS"],
    ]))

build_pdf("TESTREPORT-TR-2240.pdf", test_report_flow(
    "TR-2240", "2025-10-20",
    "FAIL on requirement 3.3.2 (power consumption in Mode 2 exceeded limit); "
    "a corrective action is tracked under ECN-0461.",
    [
        ["3.1.1", "Detection range (1 sqm target)", "46.2 km", ">= 45 km", "PASS"],
        ["3.1.2", "Azimuth scan time", "3.8 s", "<= 4 s", "PASS"],
        ["3.3.2", "Average power, Mode 2 (track)", "1265 W", "<= 1200 W", "FAIL"],
        ["3.6.1", "MTBF (demonstrated, partial)", "1850 h", ">= 2000 h", "FAIL"],
    ]))


# ---------------------------------------------------------------------------
# 5 & 6. Engineering Change Notices
# ---------------------------------------------------------------------------
def ecn_flow(ecn_no, date, change_text, affected_docs):
    f = []
    f.append(Paragraph(f"ENGINEERING CHANGE NOTICE — {ecn_no}", H1))
    f.append(Paragraph(f"ECN Number: {ecn_no} &nbsp;&nbsp; Date: {date}", BODY))
    f.append(Paragraph("1. Description of Change", H2))
    f.append(Paragraph(change_text, BODY))
    f.append(Paragraph("2. Reason for Change", H2))
    f.append(Paragraph(
        "Field data and qualification testing indicated the previous limit "
        "was insufficient for the extended operating envelope required by "
        "the customer.", BODY))
    f.append(Paragraph("3. Affected Documents", H2))
    for d in affected_docs:
        f.append(Paragraph(f"- {d}", BODY))
    f.append(Paragraph("4. Disposition", H2))
    f.append(Paragraph(
        "Approved by Change Control Board. Effective on next production "
        "build.", BODY))
    return f


build_pdf("ECN-0458.pdf", ecn_flow(
    "ECN-0458", "2025-09-15",
    "The RADAR-100 operating temperature requirement (section 3.2.1) changed "
    "from -40°C to -45°C to meet a new cold-climate deployment requirement. "
    "The maximum operating altitude (section 3.2.3) changed from 4500 m to "
    "6000 m. The supply voltage transient limit (section 3.3.1) changed from "
    "50 V to 60 V. The maximum mass limit (section 3.5.3) changed from 38 kg "
    "to 35.5 kg.",
    ["EQSPEC-RADAR-100 (Rev A -> Rev B)", "TESTREPORT-TR-2231"]))

build_pdf("ECN-0461.pdf", ecn_flow(
    "ECN-0461", "2025-10-25",
    "Corrective action for the Mode 2 (track) power overshoot found in "
    "TR-2240: a revised power-supply firmware limits peak track-mode draw "
    "to 1190 W. No specification values change; this ECN documents the "
    "firmware fix (v2.3.1) and schedules re-test.",
    ["TESTREPORT-TR-2240", "EQSPEC-POWERSUPPLY-200"]))


# ---------------------------------------------------------------------------
# 7. Second equipment spec (power supply) - for cross references
# ---------------------------------------------------------------------------
def power_spec_flow():
    f = []
    f.append(Paragraph("EQUIPMENT SPECIFICATION — POWER SUPPLY UNIT PSU-200", H1))
    f.append(Paragraph("Document No: EQSPEC-POWERSUPPLY-200 &nbsp;&nbsp; Rev A", BODY))
    f.append(Paragraph("1. Scope", H2))
    f.append(Paragraph(
        "This specification covers the PSU-200 power supply unit providing "
        "28 VDC regulated output to the RADAR-100 system.", BODY))
    f.append(Paragraph("2. Requirements", H2))
    f.append(Paragraph("2.1 The PSU-200 shall output 28 VDC +/- 2% under all specified load conditions.", BODY))
    f.append(Paragraph("2.2 The PSU-200 shall limit Mode 2 (track) output current such that downstream power draw does not exceed 1200 W, per ECN-0461 firmware v2.3.1.", BODY))
    f.append(Paragraph("2.3 The PSU-200 shall shall provide over-voltage protection that trips within 5 ms above 32 VDC.", BODY))
    f.append(Paragraph("2.4 The PSU-200 shall weigh no more than 4.2 kg.", BODY))
    f.append(Paragraph("2.5 The PSU-200 shall operate from -45°C to 71°C ambient, consistent with EQSPEC-RADAR-100 Rev B.", BODY))
    f.append(Paragraph("3. Part Numbers", H2))
    f.append(Paragraph("Main assembly P/N 7741-0032. Replacement fan module P/N 7741-0045.", BODY))
    return f


build_pdf("EQSPEC-POWERSUPPLY-200.pdf", power_spec_flow())


# ---------------------------------------------------------------------------
# 8. Marked / restricted document
# ---------------------------------------------------------------------------
def marked_doc_flow():
    f = []
    f.append(Paragraph("CONFIDENTIAL", MARK))
    f.append(Paragraph("SUPPLIER QUALITY ASSESSMENT — RADAR-100 PROGRAM", H1))
    f.append(Paragraph("Document marking: CONFIDENTIAL — Distribution limited to program staff.", MARK))
    f.append(Paragraph("1. Purpose", H2))
    f.append(Paragraph(
        "This assessment reviews the qualification status of the PSU-200 "
        "supplier (Vendor Code 4471) ahead of production release.", BODY))
    f.append(Paragraph("2. Findings", H2))
    f.append(Paragraph(
        "2.1 The supplier's incoming inspection process meets AS9100 "
        "clause 8.4.2 requirements.", BODY))
    f.append(Paragraph(
        "2.2 Two non-conformances were raised against lot QC-889 (connector "
        "pin plating thickness below spec); corrective action closed "
        "2025-10-30.", BODY))
    f.append(Paragraph("3. Recommendation", H2))
    f.append(Paragraph(
        "Approve for production release contingent on first-article "
        "inspection of the next three lots.", BODY))
    f.append(Spacer(1, 20))
    f.append(Paragraph("CONFIDENTIAL — End of Document", MARK))
    return f


build_pdf("CONFIDENTIAL-SUPPLIER-ASSESSMENT.pdf", marked_doc_flow())


# ---------------------------------------------------------------------------
# 9. Synthetic stand-ins for the real public documents (network-restricted
#    build environment; see scripts/fetch_real_docs.py for the real ones).
# ---------------------------------------------------------------------------
def synthetic_milstd_summary_flow():
    f = []
    f.append(Paragraph("[SYNTHETIC PLACEHOLDER — NOT THE REAL MIL-STD-810H]", MARK))
    f.append(Paragraph("ENVIRONMENTAL TEST METHODS — SUMMARY REFERENCE (SYN-MILSTD-810-SUMMARY)", H1))
    f.append(Paragraph(
        "This is an invented, internally-written summary of environmental "
        "test method categories, created only because this build "
        "environment cannot download the real MIL-STD-810H document. It "
        "uses plausible but non-authoritative numbers. Replace with the "
        "real public MIL-STD-810H PDF (Distribution A) before using this "
        "tool for anything real. See scripts/fetch_real_docs.py.", BODY))
    f.append(Paragraph("Method 500.6 — Low Pressure (Altitude)", H2))
    f.append(Paragraph(
        "Equipment Category 2 (ground, fixed) is tested to a simulated "
        "altitude of 4,500 meters for 2 hours of exposure.", BODY))
    f.append(Paragraph("Method 501.7 / 502.7 — High / Low Temperature", H2))
    f.append(Paragraph(
        "Equipment Category 4 (ground, mobile) storage temperature range is "
        "-51°C to +71°C; operating temperature range is -46°C to +71°C.", BODY))
    f.append(Paragraph("Method 514.8 — Vibration", H2))
    f.append(Paragraph(
        "Category 4 (ground mobile) random vibration tests run a minimum "
        "of 1 hour per axis for functional check and up to 2 hours per axis "
        "for endurance qualification.", BODY))
    f.append(Paragraph("Method 507.6 — Humidity", H2))
    f.append(Paragraph(
        "Standard humidity cycling is 10 days (240 hours) at up to 95% "
        "relative humidity.", BODY))
    return f


def synthetic_nasa_sehb_flow():
    f = []
    f.append(Paragraph("[SYNTHETIC PLACEHOLDER — NOT THE REAL NASA SE HANDBOOK]", MARK))
    f.append(Paragraph("REQUIREMENTS & VERIFICATION TERMINOLOGY — EXCERPT (SYN-NASA-SEHB-EXCERPT)", H1))
    f.append(Paragraph(
        "Invented excerpt, written to mimic the structure of a systems-"
        "engineering handbook's terminology section, created because this "
        "build environment cannot reach ntrs.nasa.gov / nasa.gov to "
        "download the real NASA SP-2016-6105 Rev 2 handbook. Replace with "
        "the real public PDF before real use.", BODY))
    f.append(Paragraph("Definition: Requirement", H2))
    f.append(Paragraph(
        "A requirement is a statement that identifies a product or process "
        "operational, functional, or design characteristic or constraint, "
        "which is unambiguous, testable or measurable, and necessary for "
        "product or process acceptability.", BODY))
    f.append(Paragraph("Definition: Verification", H2))
    f.append(Paragraph(
        "Verification is proof of compliance with a requirement, typically "
        "shown by one of four methods: Test, Analysis, Inspection, or "
        "Demonstration (often abbreviated TAID).", BODY))
    f.append(Paragraph("Definition: Validation", H2))
    f.append(Paragraph(
        "Validation confirms that a product, when used, fulfills its "
        "intended purpose in the intended operational environment, as "
        "distinct from verification against a written requirement.", BODY))
    return f


def synthetic_faa_ac_flow():
    f = []
    f.append(Paragraph("[SYNTHETIC PLACEHOLDER — NOT A REAL FAA ADVISORY CIRCULAR]", MARK))
    f.append(Paragraph("ADVISORY CIRCULAR (SAMPLE STRUCTURE) — SYN-FAA-AC-EXCERPT", H1))
    f.append(Paragraph(
        "Invented short circular written in the typical structure of an FAA "
        "Advisory Circular (purpose, background, guidance), created because "
        "this build environment cannot reach faa.gov to download a real AC. "
        "Replace with a real public Advisory Circular before real use.", BODY))
    f.append(Paragraph("1. Purpose", H2))
    f.append(Paragraph(
        "This circular provides guidance on documenting environmental "
        "qualification test evidence for line-replaceable avionics units.", BODY))
    f.append(Paragraph("2. Background", H2))
    f.append(Paragraph(
        "Applicants have asked for clarification on how much test evidence "
        "is needed to support an equipment qualification form.", BODY))
    f.append(Paragraph("3. Guidance", H2))
    f.append(Paragraph(
        "Qualification test reports should reference the specific "
        "requirement numbers they verify, the test method used, and the "
        "pass/fail result for each measured parameter.", BODY))
    return f


build_pdf("SYN-MILSTD-810-SUMMARY.pdf", synthetic_milstd_summary_flow())
build_pdf("SYN-NASA-SEHB-EXCERPT.pdf", synthetic_nasa_sehb_flow())
build_pdf("SYN-FAA-AC-EXCERPT.pdf", synthetic_faa_ac_flow())


# ---------------------------------------------------------------------------
# 10. Maintenance manual extract (DOCX)
# ---------------------------------------------------------------------------
def build_maintenance_docx():
    doc = DocxDocument()
    doc.add_heading("MAINTENANCE MANUAL EXTRACT — RADAR-100 POWER SUPPLY MODULE", level=1)
    doc.add_paragraph("Document No: MAINT-MANUAL-PWR-SUPPLY   Section 7: Fan Module Replacement")

    doc.add_heading("7.1 Warnings", level=2)
    p = doc.add_paragraph()
    p.add_run("WARNING: ").bold = True
    p.add_run(
        "Disconnect primary power and wait 5 minutes for capacitor "
        "discharge before opening the power supply enclosure. Residual "
        "voltage above 50 V may be present on the bus bar."
    )
    p2 = doc.add_paragraph()
    p2.add_run("CAUTION: ").bold = True
    p2.add_run(
        "Use only the specified replacement fan module P/N 7741-0045. "
        "Using an unapproved fan voids the thermal qualification."
    )

    doc.add_heading("7.2 Required Parts and Tools", level=2)
    doc.add_paragraph("- Replacement fan module, P/N 7741-0045", style=None)
    doc.add_paragraph("- Torx T10 driver")
    doc.add_paragraph("- Anti-static wrist strap")

    doc.add_heading("7.3 Procedure", level=2)
    steps = [
        "Power down the system and disconnect the main 28 VDC input connector.",
        "Wait 5 minutes, then verify zero volts across the bus bar with a multimeter.",
        "Remove the four T10 fasteners securing the rear access panel.",
        "Disconnect the fan's 2-pin connector from header J4 on the power board.",
        "Remove the failed fan module (P/N 7741-0045) and install the replacement, "
        "orienting the airflow arrow toward the heat sink.",
        "Reconnect the fan connector to header J4.",
        "Reinstall the rear access panel and torque fasteners to 0.5 N·m.",
        "Reconnect main power and confirm BITE status indicator shows GREEN "
        "within 30 seconds of power-up.",
    ]
    for i, s in enumerate(steps, 1):
        doc.add_paragraph(f"{i}. {s}")

    doc.add_heading("7.4 Verification", level=2)
    doc.add_paragraph(
        "After replacement, run self-test routine SELFTEST-04 and confirm "
        "fan speed reads between 4,500 and 5,200 RPM on the maintenance "
        "port (Ethernet, 10/100BASE-T)."
    )

    path = os.path.join(OUT_DIR, "MAINT-MANUAL-PWR-SUPPLY.docx")
    doc.save(path)
    print(f"wrote {path}")


build_maintenance_docx()

print(f"\nDone. {len(os.listdir(OUT_DIR))} files in {OUT_DIR}")
