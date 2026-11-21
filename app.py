
import html
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from pypdf import PdfReader

from classifier import classify_result, get_explanation
from gemini_helper import simplify_medical_report
from medical_extractor import extract_medical_tests


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Careplain - Medical Report Simplifier",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# CUSTOM CSS
# ==========================================

st.markdown(
    """
<style>
#MainMenu, footer {
    visibility: hidden;
}

.block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

.hero {
    background: linear-gradient(135deg, #0f766e 0%, #0e7490 100%);
    padding: 2rem 2.2rem;
    border-radius: 16px;
    color: #ffffff;
    margin-bottom: 1.5rem;
}

.hero h1 {
    color: #ffffff;
    margin: 0 0 .3rem 0;
    font-size: 2.1rem;
}

.hero p {
    margin: 0;
    font-size: 1.05rem;
    opacity: .95;
}

.hero .tag {
    display: inline-block;
    background: rgba(255,255,255,.18);
    padding: .2rem .8rem;
    border-radius: 999px;
    font-size: .8rem;
    margin-bottom: .8rem;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
}

.metric-card .num {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.1;
}

.metric-card .lab {
    font-size: .85rem;
    color: #475569;
}

.test-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin-bottom: .9rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
}

.test-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: .6rem;
}

.test-name {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
}

.badge {
    padding: .2rem .8rem;
    border-radius: 999px;
    font-size: .8rem;
    font-weight: 600;
}

.test-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: .6rem;
}

.lbl {
    font-size: .75rem;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: #64748b;
}

.val {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
}

.test-note {
    font-size: .9rem;
    color: #334155;
    border-top: 1px dashed #e2e8f0;
    padding-top: .5rem;
}

.disclaimer {
    background: #fffbeb;
    border: 1px solid #fde68a;
    color: #78350f;
    border-radius: 10px;
    padding: .8rem 1rem;
    font-size: .88rem;
    margin-top: 1rem;
}

.app-footer {
    text-align: center;
    color: #64748b;
    font-size: .8rem;
    margin-top: 2rem;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# CLASSIFICATION STYLES
# ==========================================

CATEGORY_STYLE = {
    "Within Range": ("#15803d", "#dcfce7", "Within Range"),
    "Attention": ("#b45309", "#fef3c7", "Needs Attention"),
    "Critical": ("#b91c1c", "#fee2e2", "Critical"),
    "Unknown": ("#475569", "#e2e8f0", "Not Classified"),
}


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def convert_number(value):
    if value is None:
        return None

    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def format_range(lower, upper, unit):

    if lower is not None and upper is not None:
        text = f"{lower:g} - {upper:g}"

    elif upper is not None:
        text = f"up to {upper:g}"

    elif lower is not None:
        text = f"at least {lower:g}"

    else:
        return "Not provided"

    return f"{text} {unit}".strip()


def flag_label(flag):

    flag = str(flag or "").lower()

    if "critical" in flag:
        return "Critical"

    if "high" in flag:
        return "High"

    if "low" in flag:
        return "Low"

    return "None reported"


def build_rows(tests):

    """Convert extracted medical tests into display-ready rows."""

    rows = []

    for test in tests:

        unit = str(test.get("unit") or "").strip()

        lower = convert_number(test.get("lower_range"))
        upper = convert_number(test.get("upper_range"))

        flag = str(test.get("flag") or "")

        raw_value = test.get("value")

        category = classify_result(
            convert_number(raw_value),
            lower,
            upper,
            flag
        )

        rows.append(
            {
                "name": str(
                    test.get("test_name") or "Unknown Test"
                ),

                "value": (
                    "Not provided"
                    if raw_value is None
                    else f"{raw_value} {unit}".strip()
                ),

                "range": format_range(
                    lower,
                    upper,
                    unit
                ),

                "flag": flag_label(flag),

                "category": category,

                "explanation": get_explanation(category),
            }
        )

    return rows


# ==========================================
# DISPLAY MEDICAL TEST CARDS
# ==========================================

def render_test_card(row):

    color, bg, label = CATEGORY_STYLE[row["category"]]

    e = html.escape

    card = "".join(
        [
            f'<div class="test-card" style="border-left:6px solid {color};">',

            '<div class="test-head">',

            f'<span class="test-name">{e(row["name"])}</span>',

            f'<span class="badge" style="background:{bg};color:{color};">'
            f'{label}</span>',

            "</div>",

            '<div class="test-grid">',

            f'<div><div class="lbl">Your result</div>'
            f'<div class="val">{e(row["value"])}</div></div>',

            f'<div><div class="lbl">Lab reference range</div>'
            f'<div class="val">{e(row["range"])}</div></div>',

            f'<div><div class="lbl">Lab flag</div>'
            f'<div class="val">{e(row["flag"])}</div></div>',

            "</div>",

            f'<div class="test-note">{e(row["explanation"])}</div>',

            "</div>",
        ]
    )

    st.markdown(card, unsafe_allow_html=True)


# ==========================================
# DISPLAY METRICS
# ==========================================

def render_metric(col, number, label, color):

    col.markdown(
        f'<div class="metric-card">'
        f'<div class="num" style="color:{color};">{number}</div>'
        f'<div class="lab">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ==========================================
# CREATE DOWNLOADABLE REPORT
# ==========================================

def create_download_report(
    rows,
    summary,
    filename,
    prompt_version,
    report_type,
    reading_level
):

    lines = [
        "CAREPLAIN - MEDICAL REPORT SIMPLIFIED",
        "=" * 45,

        f"Original File: {filename}",
        f"Report Type: {report_type}",
        f"Prompt Version: {prompt_version}",
        f"Target Reading Level: {reading_level}",

        "",
        "SMART ATTENTION CLASSIFICATION",
        "=" * 45,
    ]

    for row in rows:

        lines += [
            f"\nTest Name: {row['name']}",
            f"Result: {row['value']}",
            f"Reference Range: {row['range']}",
            f"Lab Flag: {row['flag']}",

            f"Classification: "
            f"{CATEGORY_STYLE[row['category']][2]}",

            row["explanation"],

            "-" * 35,
        ]

    lines += [
        "\nPATIENT-FRIENDLY EXPLANATION",
        "=" * 45,

        summary,

        "\nMEDICAL DISCLAIMER",

        "This application provides educational information only. "
        "It does not diagnose diseases or prescribe treatments. "
        "Always consult a qualified healthcare professional.",
    ]

    return "\n".join(lines)


# ==========================================
# SIDEBAR SETTINGS
# ==========================================

with st.sidebar:

    st.markdown("## ⚙️ Settings")

    report_type = st.selectbox(
        "Medical report type",
        ["Lab Report", "Discharge Summary"]
    )

    prompt_version = st.selectbox(
        "Prompt Engineering Version",
        [f"V{i}" for i in range(11)],
        index=5,
        help=(
            "Choose a prompt strategy from V0 to V10. V0–V6 and V9 use "
            "one explanation call; V7/V8 use two; V10 uses three. "
            "V5 is a fast, plain-language option."
        )
    )

    reading_level = st.selectbox(
        "Target reading grade",
        ["Grade 6", "Grade 7", "Grade 8", "Grade 10"],
        index=1,
        help="This is the target reading grade, not a guaranteed score."
    )

    language = st.selectbox(
        "Explanation language",
        ["English"]
    )

    st.markdown("---")

    st.markdown("### How it works")

    st.markdown(
        "1. Upload a medical report\n"
        "2. AI extracts medical test results\n"
        "3. Rules classify each result\n"
        "4. Selected prompt explains the report\n"
        "5. Download your simplified report"
    )

    st.markdown("---")

    st.markdown("### 🔒 Privacy")

    st.caption(
        "The text of your report is sent to Google's Gemini API "
        "for processing. Do not upload reports you are not "
        "comfortable sharing."
    )


# ==========================================
# APPLICATION HEADER
# ==========================================

st.markdown(
    '<div class="hero">'
    '<span class="tag">CAREPLAIN • AI-POWERED</span>'
    '<h1>🏥 Careplain</h1>'
    '<p>Understand complex medical reports in simple language '
    'with Smart Attention Classification.</p>'
    '</div>',
    unsafe_allow_html=True,
)


# ==========================================
# PDF UPLOAD
# ==========================================

with st.container(border=True):

    st.markdown("#### 📄 Upload your medical report")

    uploaded_file = st.file_uploader(
        "Choose a text-based PDF report",
        type=["pdf"],
        label_visibility="collapsed",
    )


# ==========================================
# PROCESS UPLOADED PDF
# ==========================================

if uploaded_file is not None:

    # Reset old results when a different file is uploaded.
    current_file_id = (
        uploaded_file.name,
        uploaded_file.size
    )

    if st.session_state.get("last_upload") != current_file_id:

        for key in (
            "rows",
            "extracted_tests",
            "ai_summary",
            "filename",
            "report_text",
            "level_used",
            "prompt_version",
            "report_type",
            "language_used",
        ):
            st.session_state.pop(key, None)

        st.session_state["last_upload"] = current_file_id

    # Read PDF.
    try:

        reader = PdfReader(
            BytesIO(uploaded_file.getvalue())
        )

        extracted_text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    except Exception:

        extracted_text = None

        st.error(
            "Unable to read this PDF. "
            "It may be corrupted or password-protected."
        )

    # Check whether the PDF contains readable text.
    if extracted_text is not None and not extracted_text.strip():

        st.error(
            "No readable text was found. "
            "Please upload a text-based PDF instead of a scanned image."
        )

    elif extracted_text:

        st.success(
            f"✅ {uploaded_file.name} uploaded "
            f"({len(reader.pages)} page(s))"
        )

        # Analyse button.
        if st.button(
            "🔍 Analyse My Medical Report",
            use_container_width=True,
            type="primary"
        ):

            # Read API key from Streamlit secrets.
            try:

                api_key = st.secrets["GEMINI_API_KEY"]

            except Exception:

                st.error(
                    "Gemini API key not found. "
                    "Add GEMINI_API_KEY to "
                    ".streamlit/secrets.toml"
                )

                st.stop()

            try:

                # Test extraction is shared by every prompt version. Keep it
                # for this upload so comparing prompts only calls the explainer.
                with st.spinner(
                    f"Generating your report with {prompt_version}... "
                    "The selected prompt strategy may use multiple AI steps."
                ):
                    if "extracted_tests" in st.session_state:
                        tests = st.session_state["extracted_tests"]
                        summary = simplify_medical_report(
                            extracted_text,
                            reading_level,
                            api_key,
                            prompt_version=prompt_version,
                            report_type=report_type,
                            language=language,
                        )
                    else:
                        # On the first run, extraction and explanation are
                        # independent, so run them concurrently.
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            tests_future = executor.submit(
                                extract_medical_tests,
                                extracted_text,
                                api_key,
                            )
                            summary_future = executor.submit(
                                simplify_medical_report,
                                extracted_text,
                                reading_level,
                                api_key,
                                prompt_version=prompt_version,
                                report_type=report_type,
                                language=language,
                            )

                            tests = tests_future.result()
                            summary = summary_future.result()

                    st.session_state["extracted_tests"] = tests

                # Save results.
                st.session_state["rows"] = build_rows(tests)

                st.session_state["ai_summary"] = summary

                st.session_state["filename"] = uploaded_file.name

                st.session_state["report_text"] = extracted_text

                st.session_state["level_used"] = reading_level

                st.session_state["prompt_version"] = prompt_version

                st.session_state["report_type"] = report_type

                st.session_state["language_used"] = language

                st.success("Medical report analysis completed!")

            except Exception as error:

                error_text = str(error)
                if "daily request quota is exhausted" in error_text.lower():
                    st.error(
                        "Gemini's daily API request quota is exhausted for "
                        "the available models. Wait for the reset time shown "
                        "in the details below, or enable billing/increase "
                        "your Gemini API quota."
                    )
                else:
                    st.error(
                        "Unable to analyse the report. Please try again."
                    )

                st.caption(f"Details: {error_text}")


# ==========================================
# DISPLAY RESULTS
# ==========================================

if "rows" in st.session_state:

    rows = st.session_state["rows"]

    summary = st.session_state["ai_summary"]

    st.markdown("---")

    st.markdown("### 📈 Analysis Overview")

    # Show the settings used for this analysis.
    st.caption(
        f"Prompt Version: {st.session_state['prompt_version']} | "
        f"Report Type: {st.session_state['report_type']} | "
        f"Target Reading Level: {st.session_state['level_used']} | "
        f"Language: {st.session_state['language_used']}"
    )

    # Count classifications.
    counts = {
        key: 0
        for key in CATEGORY_STYLE
    }

    for row in rows:
        counts[row["category"]] += 1

    # Display classification metrics.
    c1, c2, c3, c4 = st.columns(4)

    render_metric(
        c1,
        counts["Within Range"],
        "Within Range",
        "#15803d"
    )

    render_metric(
        c2,
        counts["Attention"],
        "Needs Attention",
        "#b45309"
    )

    render_metric(
        c3,
        counts["Critical"],
        "Critical",
        "#b91c1c"
    )

    render_metric(
        c4,
        counts["Unknown"],
        "Not Classified",
        "#475569"
    )

    # Results tabs.
    tab_results, tab_explain, tab_original = st.tabs(
        [
            "📊 Test Results",
            "💬 Explained Simply",
            "📄 Original Text"
        ]
    )

    # --------------------------------------
    # TAB 1: MEDICAL TEST RESULTS
    # --------------------------------------

    with tab_results:

        view = st.radio(
            "Show",
            [
                "All results",
                "Needs attention only"
            ],
            horizontal=True,
            label_visibility="collapsed",
        )

        shown = [
            row
            for row in rows
            if (
                view == "All results"
                or row["category"] in ("Attention", "Critical")
            )
        ]

        if not rows:

            st.warning(
                "No test results could be extracted from this report."
            )

        elif not shown:

            st.success(
                "No results need attention based on the "
                "available report information."
            )

        for row in shown:
            render_test_card(row)

    # --------------------------------------
    # TAB 2: PATIENT-FRIENDLY EXPLANATION
    # --------------------------------------

    with tab_explain:

        st.markdown(summary)

    # --------------------------------------
    # TAB 3: ORIGINAL REPORT TEXT
    # --------------------------------------

    with tab_original:

        st.text_area(
            "Extracted report text",
            st.session_state["report_text"],
            height=350,
            label_visibility="collapsed",
        )

    # --------------------------------------
    # DOWNLOAD REPORT
    # --------------------------------------

    download_data = create_download_report(
        rows,
        summary,
        st.session_state["filename"],
        st.session_state["prompt_version"],
        st.session_state["report_type"],
        st.session_state["level_used"]
    )

    st.download_button(
        label="📥 Download Simplified Report (.txt)",

        data=download_data,

        file_name="Careplain_Simplified_Report.txt",

        mime="text/plain",

        use_container_width=True,
    )

    # --------------------------------------
    # MEDICAL DISCLAIMER
    # --------------------------------------

    st.markdown(
        '<div class="disclaimer">'
        '⚕️ <b>Medical Disclaimer:</b> This application provides '
        'educational information only. It does not diagnose diseases '
        'or prescribe treatments. Test results must be interpreted '
        'by a qualified healthcare professional.'
        '</div>',
        unsafe_allow_html=True,
    )


# ==========================================
# FOOTER
# ==========================================

st.markdown(
    '<div class="app-footer">'
    'Careplain • Prompt Engineering Research Project • '
    'Smart Attention Classification'
    '</div>',
    unsafe_allow_html=True,
)
