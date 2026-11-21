import hashlib
import html
import json
import re
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from csv import DictWriter
from datetime import datetime
from io import BytesIO, StringIO
from queue import Empty, Queue
from threading import Event

import streamlit as st
from pypdf import PdfReader

from classifier import classify_result, get_explanation
from gemini_helper import simplify_medical_report
from medical_extractor import extract_medical_tests
from research_lab import (
    EXPECTED_CALLS,
    PROMPT_STRATEGIES,
    comparison_cache_key,
    count_words,
    detect_headings,
    report_identifier,
)
from speech_helper import DEFAULT_VOICE, TTS_MODEL, synthesize_narration
from api_optimization import (
    content_hash, explanation_cache_key, get_or_create, is_quota_exhaustion,
)
try:
    from api_optimization import is_usable_explanation
except ImportError:
    # Streamlit can rerun app.py while retaining an older imported helper
    # module in memory. Keep the result check compatible with that process.
    def is_usable_explanation(text):
        return isinstance(text, str) and sum(character.isalnum() for character in text) >= 40
from demo_data import SAMPLE_TESTS, prepared_explanation


st.set_page_config(
    page_title="Careplain | Medical Report Simplifier",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
:root {
    --navy: #10243a;
    --teal: #0f766e;
    --teal-dark: #115e59;
    --sky: #e8f3fb;
    --ink: #1e293b;
    --muted: #64748b;
    --line: #dbe5ee;
}
.stApp { background: #f4f8fb; color: var(--ink); }
.stApp p, .stApp label, .stApp li { font-size: 1rem; line-height: 1.5; }
[data-testid="stCaptionContainer"] p { font-size: .9rem; line-height: 1.45; }
.block-container { max-width: 1280px; padding-top: 1.4rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #edf4f8; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
.hero {
    position: relative; overflow: hidden; padding: 2rem 2.25rem;
    border-radius: 22px; color: white; margin-bottom: 1.25rem;
    background: radial-gradient(circle at 90% 5%, rgba(255,255,255,.2), transparent 28%),
      linear-gradient(120deg, #10243a 0%, #12415a 45%, #0f766e 100%);
    box-shadow: 0 16px 40px rgba(16,36,58,.14);
    animation: fade-up .45s ease-out both;
}
.hero h1 { color: white; letter-spacing: .04em; font-size: clamp(2rem, 4vw, 2.8rem); margin: .4rem 0 .2rem; }
.hero p { color: #e6f5f5; font-size: 1.06rem; margin: .35rem 0 0; max-width: 760px; }
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .73rem; font-weight: 700; color: #b9e6e2; }
.hero-mark { float: right; font-size: 3rem; opacity: .92; padding: .25rem .5rem; }
.section-kicker { color: var(--teal-dark); font-weight: 700; font-size: .76rem; text-transform: uppercase; letter-spacing: .1em; }
.welcome-card, .surface-card {
    background: white; border: 1px solid var(--line); border-radius: 18px;
    padding: 1.25rem 1.4rem; box-shadow: 0 5px 18px rgba(16,36,58,.045);
    animation: fade-up .4s ease-out both;
}
.metric-card {
    min-height: 118px; background: white; border: 1px solid var(--line);
    border-radius: 16px; padding: 1rem 1.1rem; box-shadow: 0 5px 18px rgba(16,36,58,.05);
    transition: transform .18s ease, box-shadow .18s ease;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 12px 26px rgba(16,36,58,.1); }
.metric-value { color: var(--navy); font-weight: 750; font-size: 1.65rem; line-height: 1.2; }
.metric-label { color: var(--muted); font-size: .83rem; margin-top: .38rem; }
.test-card {
    background: white; border: 1px solid var(--line); border-left: 5px solid #94a3b8;
    border-radius: 15px; padding: 1rem 1.2rem; margin: .75rem 0;
    box-shadow: 0 4px 14px rgba(16,36,58,.04); animation: fade-up .32s ease-out both;
}
.test-head { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:.8rem; }
.test-name { font-weight:700; color:var(--navy); font-size:1.07rem; }
.badge { padding:.3rem .7rem; border-radius:999px; font-size:.77rem; font-weight:700; white-space:nowrap; }
.test-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }
.lbl { color:var(--muted); text-transform:uppercase; letter-spacing:.07em; font-size:.68rem; }
.val { color:var(--ink); font-weight:650; margin-top:.22rem; overflow-wrap:anywhere; }
.test-note { border-top:1px solid #e8eef3; margin-top:.85rem; padding-top:.7rem; color:#475569; font-size:.9rem; }
.disclaimer { background:#fff8e7; color:#704b0c; border:1px solid #f2d791; border-radius:13px; padding:.9rem 1rem; margin-top:1rem; font-size:.88rem; }
.app-footer { color:var(--muted); text-align:center; font-size:.79rem; padding:2rem 0 .5rem; }
div.stButton > button[kind="primary"] { border:0; border-radius:12px; background:linear-gradient(110deg,#0f766e,#0e7490); transition:transform .18s ease, box-shadow .18s ease; }
div.stButton > button[kind="primary"]:hover { transform:translateY(-2px); box-shadow:0 8px 18px rgba(15,118,110,.22); }
div[data-testid="stFileUploader"] { background:#fff; border:1px dashed #9cb8ca; border-radius:15px; padding:.5rem; }
@keyframes fade-up { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:.01ms !important; }
}
@media (max-width: 720px) {
  .hero { padding:1.4rem; border-radius:16px; }
  .hero-mark { font-size:2rem; }
  .test-grid { grid-template-columns:1fr; gap:.6rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


CATEGORY_STYLE = {
    "Within Range": ("#15803d", "#dcfce7", "Within Range"),
    "Attention": ("#a16207", "#fef3c7", "Needs Attention"),
    "Critical": ("#b91c1c", "#fee2e2", "Critical"),
    "Unknown": ("#475569", "#e2e8f0", "Insufficient Information"),
}

SUPPORTED_LANGUAGES = (
    "English", "Kannada", "Hindi", "Tamil", "Telugu", "Malayalam",
    "Bengali", "Marathi",
)
PROMPT_VERSIONS = [f"V{i}" for i in range(11)]


def convert_number(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def format_range(lower, upper, unit):
    if lower is not None and upper is not None:
        value = f"{lower:g} – {upper:g}"
    elif upper is not None:
        value = f"Up to {upper:g}"
    elif lower is not None:
        value = f"At least {lower:g}"
    else:
        return "Not provided"
    return f"{value} {unit}".strip()


def flag_label(flag):
    normalized = str(flag or "").lower()
    if "critical" in normalized:
        return "Critical"
    if "high" in normalized:
        return "High"
    if "low" in normalized:
        return "Low"
    return "None reported"


def build_rows(tests):
    rows = []
    for test in tests:
        unit = str(test.get("unit") or "").strip()
        lower = convert_number(test.get("lower_range"))
        upper = convert_number(test.get("upper_range"))
        flag = str(test.get("flag") or "")
        raw_value = test.get("value")
        category = classify_result(convert_number(raw_value), lower, upper, flag)
        rows.append({
            "name": str(test.get("test_name") or "Unknown Test"),
            "value": "Not provided" if raw_value is None else f"{raw_value} {unit}".strip(),
            "range": format_range(lower, upper, unit),
            "flag": flag_label(flag),
            "category": category,
            "explanation": get_explanation(category),
        })
    return rows


def render_test_card(row):
    color, background, label = CATEGORY_STYLE[row["category"]]
    escape = html.escape
    st.markdown(
        f"""
<div class="test-card" style="border-left-color:{color}">
  <div class="test-head"><span class="test-name">{escape(row['name'])}</span>
    <span class="badge" style="background:{background};color:{color}">{label}</span></div>
  <div class="test-grid">
    <div><div class="lbl">Result</div><div class="val">{escape(row['value'])}</div></div>
    <div><div class="lbl">Reference range</div><div class="val">{escape(row['range'])}</div></div>
    <div><div class="lbl">Report flag</div><div class="val">{escape(row['flag'])}</div></div>
  </div>
  <div class="test-note">{escape(row['explanation'])}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_metric(col, value, label):
    col.markdown(
        f'<div class="metric-card"><div class="metric-value">{html.escape(str(value))}</div>'
        f'<div class="metric-label">{html.escape(label)}</div></div>',
        unsafe_allow_html=True,
    )


def create_download_report(rows, summary, filename, report_type, prompt_version,
                          reading_level, analyzed_at):
    lines = [
        "CAREPLAIN — AI-POWERED MEDICAL REPORT SIMPLIFIER",
        "=" * 54,
        f"Original file: {filename}",
        f"Report type: {report_type}",
        f"Prompt version: {prompt_version}",
        f"Target reading grade: {reading_level}",
        f"Analysis date and time: {analyzed_at}",
        "",
        "TEST RESULTS AND RULE-BASED CLASSIFICATION",
        "=" * 54,
    ]
    for row in rows:
        lines.extend([
            f"\nTest: {row['name']}", f"Result: {row['value']}",
            f"Reference range: {row['range']}", f"Report flag: {row['flag']}",
            f"Classification: {CATEGORY_STYLE[row['category']][2]}",
            row["explanation"], "-" * 40,
        ])
    lines.extend([
        "\nPATIENT-FRIENDLY EXPLANATION", "=" * 54, summary,
        "\nMEDICAL DISCLAIMER",
        "This application provides educational information only. It does not "
        "diagnose conditions or prescribe treatment. Consult a qualified "
        "healthcare professional about your results.",
    ])
    return "\n".join(lines)


def friendly_error(error, api_key):
    details = str(error)
    cause = getattr(error, "__cause__", None)
    if cause:
        details += f"\nProvider details: {cause}"
    if api_key:
        details = details.replace(api_key, "[redacted]")
    normalized = details.lower()

    if "quota" in normalized or "resource_exhausted" in normalized or "429" in normalized:
        message = (
            "Gemini API quota was reached. For a daily limit, try again after "
            "the reset time shown in the technical details. For a short-term "
            "rate limit, wait for its retry window; review Google AI Studio "
            "limits if the error continues."
        )
    elif "503" in normalized or "unavailable" in normalized or "connection" in normalized:
        message = "Gemini is temporarily unavailable. Please try again later."
    elif "timeout" in normalized or "timed out" in normalized or "deadline exceeded" in normalized or "504" in normalized:
        message = (
            "Gemini took too long to respond. Requests stop after 30 seconds per model, "
            "with one fallback model available. Please run this version again."
        )
    elif "404" in normalized or "model" in normalized and "not found" in normalized:
        message = "The configured Gemini model is unavailable for this API key or project."
    elif "jsondecodeerror" in normalized or "invalid medical test data" in normalized:
        message = "Gemini returned structured data that could not be read. Please retry the analysis."
    elif "empty response" in normalized:
        message = "Gemini returned an empty response. Please retry the analysis."
    elif "no readable text" in normalized:
        message = "No selectable text was found in this PDF. Please use a text-based PDF."
    elif "unable to read this pdf" in normalized or "pdfreaderror" in normalized:
        message = "This PDF could not be read. It may be damaged or password-protected."
    elif (
        "gemini_api_key" in normalized
        or "secret not found" in normalized
        or "secrets.toml" in normalized
        or "api key is required" in normalized
    ):
        message = "Gemini API key is missing. Add GEMINI_API_KEY to .streamlit/secrets.toml."
    elif "encrypted" in normalized or "not decrypted" in normalized or "password" in normalized and "pdf" in normalized:
        message = "This PDF could not be opened. Check that it is not password-protected."
    else:
        message = "Unable to analyse this report. Check the file and API settings, then try again."
    return message, details


def new_usage_metrics():
    return {
        "api_calls": 0,
        "models": [],
        "token_metadata_available": False,
        "input_tokens": 0,
        "output_tokens": 0,
    }


def combine_usage_metrics(*items):
    combined = new_usage_metrics()
    for item in items:
        combined["api_calls"] += item["api_calls"]
        for model in item["models"]:
            if model not in combined["models"]:
                combined["models"].append(model)
        combined["input_tokens"] += item["input_tokens"]
        combined["output_tokens"] += item["output_tokens"]
        combined["token_metadata_available"] |= item["token_metadata_available"]
    return combined


def comparison_signature(report_text, selected, report_type, reading_level, language):
    payload = {
        "report_identifier": report_identifier(report_text),
        "selected_versions": list(selected),
        "report_type": report_type,
        "reading_level": reading_level,
        "language": language,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def render_voice_narration(text, language, key_suffix):
    if demo_mode:
        locale = {
            "English": "en-US", "Kannada": "kn-IN", "Hindi": "hi-IN",
            "Tamil": "ta-IN", "Telugu": "te-IN", "Malayalam": "ml-IN",
            "Bengali": "bn-IN", "Marathi": "mr-IN",
        }.get(language, "en-US")
        safe_text = json.dumps(text).replace("<", "\\u003c")
        speak_id = "demo_speak_" + re.sub(r"[^a-zA-Z0-9_]", "_", key_suffix)
        stop_id = speak_id + "_stop"
        st.html(
            f"""<div style='font:14px sans-serif'>
            <button id='{speak_id}' style='padding:10px 14px;cursor:pointer'>▶ Play sample narration</button>
            <button id='{stop_id}' style='padding:10px 14px;cursor:pointer'>■ Stop</button>
            <span> Uses your browser's local speech voice; no Gemini request.</span>
            </div><script>
            const sampleText = {safe_text};
            document.getElementById({json.dumps(speak_id)}).onclick = () => {{
              window.speechSynthesis.cancel();
              const speech = new SpeechSynthesisUtterance(sampleText);
              speech.lang = {json.dumps(locale)};
              window.speechSynthesis.speak(speech);
            }};
            document.getElementById({json.dumps(stop_id)}).onclick = () => window.speechSynthesis.cancel();
            </script>""",
            unsafe_allow_javascript=True,
        )
        return

    st.caption(
        f"Narration uses the exact generated text in {language}. "
        "Generating audio makes one additional Gemini TTS request."
    )
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    audio_cache = st.session_state.setdefault("voice_audio_cache", {})
    cache_key = None
    if "GEMINI_API_KEY" in st.secrets:
        key_fingerprint = hashlib.sha256(
            st.secrets["GEMINI_API_KEY"].encode("utf-8")
        ).hexdigest()
        cache_key = hashlib.sha256(
            f"{text_hash}|{language}|{DEFAULT_VOICE}|{TTS_MODEL}|{key_fingerprint}".encode("utf-8")
        ).hexdigest()

    if st.button("🔊 Generate AI voice narration", key=f"narrate_{key_suffix}", use_container_width=True):
        if cache_key and cache_key in audio_cache:
            st.info("Using the narration already generated for this explanation.")
        else:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                with st.spinner("Generating the audio narration…"):
                    audio, mime_type = synthesize_narration(text, api_key, voice=DEFAULT_VOICE)
                if cache_key:
                    audio_cache[cache_key] = {"audio": audio, "mime_type": mime_type}
                    while len(audio_cache) > 3:
                        audio_cache.pop(next(iter(audio_cache)))
                    st.session_state["voice_audio_cache"] = audio_cache
            except Exception as error:
                api_key = locals().get("api_key")
                message, details = friendly_error(error, api_key)
                st.error(f"Unable to generate narration. {message}")
                with st.expander("Narration details"):
                    st.code(details)

    if cache_key and cache_key in audio_cache:
        st.audio(audio_cache[cache_key]["audio"], format="audio/wav")


def run_prompt_comparison_version(version, report_text, settings, api_key,
                                   stop_event, stage_events, pre_extracted_findings=None):
    metrics = new_usage_metrics()
    started = time.perf_counter()

    def queue_stage(label, state):
        stage_events.put((version, label, state))

    try:
        response = simplify_medical_report(
            report_text,
            settings["reading_level"],
            api_key,
            prompt_version=version,
            report_type=settings["report_type"],
            language=settings["language"],
            metrics=metrics,
            on_stage=queue_stage,
            stop_event=stop_event,
            pre_extracted_findings=pre_extracted_findings,
        )
        if not is_usable_explanation(response):
            raise ValueError("Gemini returned an incomplete explanation. Please run this version again.")
        return {
            "status": "success",
            "strategy": PROMPT_STRATEGIES[version],
            "response": response,
            "headings": detect_headings(response),
            "word_count": count_words(response),
            "processing_seconds": time.perf_counter() - started,
            "api_calls": metrics["api_calls"],
            "models": list(metrics["models"]),
            "from_cache": False,
        }
    except Exception as error:
        details = str(error)
        stopped_by_quota = "was stopped before sending another call" in details.lower()
        if stopped_by_quota:
            message = "Stopped because another prompt version exhausted the daily quota."
        else:
            message, details = friendly_error(error, api_key)
        return {
            "status": "stopped" if stopped_by_quota else "failed",
            "strategy": PROMPT_STRATEGIES[version],
            "error": message,
            "details": details,
            "processing_seconds": time.perf_counter() - started,
            "api_calls": metrics["api_calls"],
            "models": list(metrics["models"]),
            "headings": [],
            "word_count": 0,
            "from_cache": False,
        }


with st.sidebar:
    st.markdown("## 🏥 Careplain")
    st.caption("AI-powered medical report simplifier")

    with st.expander("Prompt configuration", expanded=True):
        report_type = st.selectbox("Medical report type", ["Lab Report", "Discharge Summary"])
        prompt_version = st.selectbox(
            "Prompt engineering version", [f"V{i}" for i in range(11)], index=5,
            help="Choose a research prompt version. V7, V8 and V10 use multi-stage workflows.",
        )
        reading_level = st.selectbox("Target reading grade", ["Grade 6", "Grade 7", "Grade 8", "Grade 10"], index=1)
        language = st.selectbox("Explanation language", SUPPORTED_LANGUAGES)

    demo_mode = st.toggle(
        "Demo Mode · synthetic sample · no Gemini calls",
        value=False,
        key="careplain_demo_mode",
        help="Shows prepared synthetic examples. Live report analysis and Gemini narration are disabled in this mode.",
    )

    with st.expander("Project objective"):
        st.write(
            "Careplain aims to simplify complex medical reports into patient-friendly "
            "explanations using progressive prompt engineering techniques. The system "
            "explores how different prompting strategies influence readability, "
            "completeness, medical information preservation and safety."
        )

    with st.expander("How it works"):
        st.markdown(
            "1. Upload a medical report.\n"
            "2. AI extracts medical test results and findings.\n"
            "3. Rule-based logic classifies available test results.\n"
            "4. The selected prompt generates a patient-friendly explanation.\n"
            "5. Download the simplified report."
        )

    with st.expander("Smart Attention Classification"):
        st.markdown(
            "- **Within Range:** the value falls within the supplied reference range.\n"
            "- **Attention:** the value falls outside that range or has an abnormal flag.\n"
            "- **Critical:** the report explicitly marks a critical result.\n"
            "- **Insufficient information:** available values are not enough to classify."
        )
        st.caption("This is a rule-based comparison, not a diagnosis or a measure of clinical risk. Reference ranges vary by laboratory and patient context.")

    with st.expander("Prompt engineering research"):
        st.write("Careplain explores progressive prompt versions V0–V10 across:")
        st.markdown("Readability · Clarity · Completeness · Information preservation · Hallucination reduction · Safety · Response time")

    with st.expander("Safety guidelines"):
        st.markdown(
            "- Preserve reported values and units.\n"
            "- Do not invent missing results or reference ranges.\n"
            "- Identify uncertainty clearly.\n"
            "- Do not diagnose or prescribe medicines.\n"
            "- Discuss results with a qualified healthcare professional."
        )

    with st.expander("Privacy"):
        st.write(
            "Medical report text is sent to Google's Gemini API for processing. "
            "Avoid uploading identifiable medical information unless you have "
            "the necessary permission and are comfortable with the data handling arrangements."
        )

    with st.expander("About Careplain"):
        st.write("**CAREPLAIN — AI-POWERED MEDICAL REPORT SIMPLIFIER USING PROMPT ENGINEERING**")
        st.caption("An academic research prototype exploring how prompt engineering can improve the accessibility and understanding of complex medical information.")


st.markdown(
    '<div class="hero"><span class="hero-mark">✚</span>'
    '<div class="eyebrow">AI-powered medical report simplifier</div>'
    '<h1>CAREPLAIN</h1>'
    '<p>Making complex medical information simple, clear and understandable.</p>'
    '<p>Welcome. Upload a report to see its key results and a patient-friendly explanation.</p></div>',
    unsafe_allow_html=True,
)


dashboard_tab, comparison_tab, research_tab, info_tab = st.tabs([
    "📋 Dashboard", "🧪 Prompt Comparison Lab", "🔬 Research", "ℹ️ About & safety",
])


with dashboard_tab:
    if demo_mode:
        st.success("DEMO MODE — synthetic sample data and prepared text only. No Gemini requests are made.")
        demo_version = st.selectbox(
            "Prepared demo prompt version", ["V0", "V1", "V2", "V10"],
            key="demo_prompt_version",
        )
        demo_summary = prepared_explanation(demo_version, language)
        demo_rows = build_rows(SAMPLE_TESTS)
        st.markdown("### Sample dashboard · fictional report")
        st.caption(f"Prepared {demo_version} example · {language} · synthetic values")
        demo_columns = st.columns(4)
        render_metric(demo_columns[0], len(demo_rows), "Sample tests identified")
        render_metric(demo_columns[1], sum(row["category"] == "Within Range" for row in demo_rows), "Within sample range")
        render_metric(demo_columns[2], sum(row["category"] in ("Attention", "Critical") for row in demo_rows), "Sample results to discuss")
        render_metric(demo_columns[3], "0", "Gemini requests in demo")
        st.markdown("#### Smart Attention Classification · local rules")
        for sample_row in demo_rows:
            render_test_card(sample_row)
        st.markdown("#### Prepared patient-friendly sample")
        st.markdown(demo_summary)
        st.caption("This is prepared demonstration text. It was not generated or verified by AI and is not based on a real patient.")
        render_voice_narration(demo_summary, language, "demo_dashboard")
        st.download_button(
            "Download synthetic demo report",
            create_download_report(
                demo_rows, demo_summary, "SYNTHETIC_SAMPLE.pdf", report_type,
                demo_version, reading_level, "DEMO SAMPLE — not generated live",
            ),
            file_name="Careplain_Synthetic_Demo.txt", mime="text/plain",
        )

    has_analysis = "rows" in st.session_state and "ai_summary" in st.session_state
    if not has_analysis:
        st.markdown(
            '<div class="welcome-card"><div class="section-kicker">Your report workspace</div>'
            '<h3>Start with a medical report</h3>'
            '<p>Careplain extracts available test results, compares them with the report’s own ranges, '
            'and explains the report using your selected prompt version.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Upload a report")
    st.caption("Text-based PDF · Maximum file size follows the app upload setting")
    uploaded_file = st.file_uploader("Choose a medical report (PDF)", type=["pdf"], label_visibility="collapsed")

    if uploaded_file is not None:
        pdf_bytes = uploaded_file.getvalue()
        current_file_id = (uploaded_file.name, len(pdf_bytes), hashlib.sha256(pdf_bytes).hexdigest())

        if st.session_state.get("last_upload") != current_file_id:
            for key in (
                "rows", "extracted_tests", "cached_tests_file_id", "ai_summary",
                "filename", "report_text", "level_used", "prompt_version",
                "report_type", "language_used", "analysis_metrics", "analyzed_at",
            ):
                st.session_state.pop(key, None)
            st.session_state["last_upload"] = current_file_id

        st.caption(f"Selected: **{uploaded_file.name}** · {len(pdf_bytes) / 1024:.1f} KB")
        analyze = st.button(
            "✨ Analyse my medical report", type="primary", use_container_width=True,
            disabled=demo_mode,
            help="Turn Demo Mode off before sending a real report to Gemini." if demo_mode else None,
        )

        if analyze:
            status = st.status("Preparing your analysis", expanded=True)
            progress = st.progress(0, text="Starting report analysis")
            extraction_metrics = new_usage_metrics()
            explanation_metrics = new_usage_metrics()
            stage_events = Queue()
            quota_stop = Event()
            analysis_started = time.perf_counter()
            api_key = None

            def report_stage(label, state):
                stage_events.put((label, state))

            def report_stage_inline(label, state):
                suffix = "…" if state == "running" else " complete"
                status.update(label=f"{label}{suffix}", state="running", expanded=True)

            def show_pending_stages():
                latest = None
                while True:
                    try:
                        latest = stage_events.get_nowait()
                    except Empty:
                        break
                    label, state = latest
                    suffix = "…" if state == "running" else " complete"
                    status.update(label=f"{label}{suffix}", state="running", expanded=True)

            try:
                status.update(label="Reading uploaded PDF", state="running", expanded=True)
                pdf_text_cache = st.session_state.setdefault("pdf_text_cache", {})
                pdf_hash = current_file_id[2]
                if pdf_hash in pdf_text_cache:
                    report_text = pdf_text_cache[pdf_hash]["text"]
                    page_count = pdf_text_cache[pdf_hash]["pages"]
                else:
                    reader = PdfReader(BytesIO(pdf_bytes))
                    report_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
                    page_count = len(reader.pages)
                    if not report_text:
                        raise ValueError("No readable text was found in this PDF.")
                    pdf_text_cache[pdf_hash] = {"text": report_text, "pages": page_count}
                    while len(pdf_text_cache) > 10:
                        pdf_text_cache.pop(next(iter(pdf_text_cache)))
                progress.progress(0.15, text="PDF text ready")
                status.update(label=f"PDF read · {page_count} page(s)", state="running", expanded=True)
                api_key = st.secrets["GEMINI_API_KEY"]
                report_hash = content_hash(report_text)
                extraction_cache = st.session_state.setdefault("extracted_report_cache", {})
                explanation_cache = st.session_state.setdefault("explanation_cache", {})
                explanation_key = explanation_cache_key(
                    report_text, prompt_version, report_type, reading_level, language
                )
                summary_cached = (
                    explanation_key in explanation_cache
                    and is_usable_explanation(explanation_cache[explanation_key])
                )
                if explanation_key in explanation_cache and not summary_cached:
                    explanation_cache.pop(explanation_key, None)
                tests_cached = report_hash in extraction_cache
                summary = explanation_cache.get(explanation_key)

                if tests_cached:
                    tests = extraction_cache[report_hash]
                    status.update(label="Reusing extracted medical information", state="running", expanded=True)
                    progress.progress(0.48, text="Using session-cached medical information")
                else:
                    status.update(label="Extracting medical information", state="running", expanded=True)
                    if summary_cached or prompt_version in ("V7", "V10"):
                        tests = extract_medical_tests(
                            report_text, api_key, metrics=extraction_metrics,
                            on_stage=report_stage_inline, stop_event=quota_stop,
                        )
                        extraction_cache[report_hash] = tests
                        while len(extraction_cache) > 10:
                            extraction_cache.pop(next(iter(extraction_cache)))
                    else:
                        # For single-stage prompts and V8, independent local
                        # extraction and generation run together for speed.
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            pending_tasks = {
                                executor.submit(
                                    extract_medical_tests, report_text, api_key,
                                    metrics=extraction_metrics, on_stage=report_stage,
                                    stop_event=quota_stop,
                                ): "extraction",
                                executor.submit(
                                    simplify_medical_report, report_text, reading_level,
                                    api_key, prompt_version=prompt_version,
                                    report_type=report_type, language=language,
                                    metrics=explanation_metrics, on_stage=report_stage,
                                    stop_event=quota_stop,
                                ): "explanation",
                            }
                            task_error = None
                            while pending_tasks:
                                show_pending_stages()
                                finished, _ = wait(
                                    pending_tasks, timeout=0.15,
                                    return_when=FIRST_COMPLETED,
                                )
                                for future in finished:
                                    task_name = pending_tasks.pop(future)
                                    try:
                                        result = future.result()
                                    except Exception as error:
                                        task_error = task_error or error
                                        continue
                                    if task_name == "extraction":
                                        tests = result
                                        extraction_cache[report_hash] = tests
                                    else:
                                        summary = result
                                        if not is_usable_explanation(summary):
                                            raise ValueError(
                                                "Gemini returned an incomplete explanation. Please run this version again."
                                            )
                                        explanation_cache[explanation_key] = summary
                                st.session_state["extracted_report_cache"] = extraction_cache
                                st.session_state["explanation_cache"] = explanation_cache
                            if task_error is not None:
                                raise task_error
                        while len(explanation_cache) > 30:
                            explanation_cache.pop(next(iter(explanation_cache)))
                        while len(extraction_cache) > 10:
                            extraction_cache.pop(next(iter(extraction_cache)))

                status.update(label="Classifying results with local Python rules", state="running", expanded=True)
                rows = build_rows(tests)
                progress.progress(0.62, text="Medical results classified locally")

                if not summary_cached and summary is None:
                    status.update(label="Generating patient-friendly explanation", state="running", expanded=True)
                    summary, summary_cached = get_or_create(
                        explanation_cache,
                        explanation_key,
                        lambda: simplify_medical_report(
                            report_text, reading_level, api_key,
                            prompt_version=prompt_version, report_type=report_type,
                            language=language, metrics=explanation_metrics,
                            on_stage=report_stage_inline, stop_event=quota_stop,
                            pre_extracted_findings={"tests": tests},
                        ),
                    )
                    if not is_usable_explanation(summary):
                        explanation_cache.pop(explanation_key, None)
                        raise ValueError(
                            "Gemini returned an incomplete explanation. Please run this version again."
                        )
                    while len(explanation_cache) > 30:
                        explanation_cache.pop(next(iter(explanation_cache)))
                if summary_cached:
                    explanation_metrics["cache_hit"] = True
                    status.update(label="Reusing cached explanation", state="running", expanded=True)

                show_pending_stages()
                st.session_state["pdf_text_cache"] = pdf_text_cache
                st.session_state["extracted_report_cache"] = extraction_cache
                st.session_state["explanation_cache"] = explanation_cache
                metrics = combine_usage_metrics(extraction_metrics, explanation_metrics)
                metrics.update({
                    "extraction_cache_hit": tests_cached,
                    "explanation_cache_hit": summary_cached,
                    "extraction_api_calls": extraction_metrics["api_calls"],
                    "explanation_api_calls": explanation_metrics["api_calls"],
                })

                status.update(label="Preparing final report", state="running", expanded=True)
                analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
                elapsed = time.perf_counter() - analysis_started
                st.session_state.update({
                    "rows": rows,
                    "ai_summary": summary,
                    "filename": uploaded_file.name,
                    "report_text": report_text,
                    "level_used": reading_level,
                    "prompt_version": prompt_version,
                    "report_type": report_type,
                    "language_used": language,
                    "analysis_metrics": {**metrics, "processing_seconds": elapsed},
                    "analyzed_at": analyzed_at,
                })
                progress.progress(1.0, text="Report ready")
                status.update(label="Analysis complete", state="complete", expanded=False)
                st.success("Your report is ready. Review the results and explanation below.")
            except Exception as error:
                status.update(label="Analysis could not be completed", state="error", expanded=True)
                progress.empty()
                message, details = friendly_error(error, api_key)
                st.error(message)
                with st.expander("Technical details"):
                    st.code(details)

    if "rows" in st.session_state and "ai_summary" in st.session_state and not demo_mode:
        rows = st.session_state["rows"]
        counts = {category: 0 for category in CATEGORY_STYLE}
        for row in rows:
            counts[row["category"]] += 1

        st.markdown("### Analysis overview")
        st.caption(
            f"{st.session_state['filename']} · {st.session_state['report_type']} · "
            f"{st.session_state['prompt_version']} · {st.session_state['level_used']} · "
            f"{st.session_state['language_used']}"
        )
        metric_cols = st.columns(4)
        render_metric(metric_cols[0], len(rows), "Tests identified")
        render_metric(metric_cols[1], counts["Within Range"], "Within supplied range")
        render_metric(metric_cols[2], counts["Attention"] + counts["Critical"], "Results needing discussion")
        render_metric(metric_cols[3], st.session_state["prompt_version"], "Prompt version used")

        result_tab, explanation_tab, original_tab = st.tabs(["Test results", "Patient-friendly explanation", "Original text"])
        with result_tab:
            view = st.radio("Results to show", ["Needs discussion", "All results"], horizontal=True, label_visibility="collapsed")
            visible_rows = [row for row in rows if view == "All results" or row["category"] in ("Attention", "Critical")]
            if not rows:
                st.info("No medical test results were identified in this report.")
            elif not visible_rows:
                st.success("No extracted results were flagged for discussion based on the available ranges and report flags.")
            for row in visible_rows:
                render_test_card(row)

        with explanation_tab:
            st.markdown(st.session_state["ai_summary"])
            st.markdown(
                '<div class="disclaimer"><strong>Medical information only.</strong> '
                'Careplain does not diagnose conditions or prescribe treatment. '
                'Please discuss your report with a qualified healthcare professional.</div>',
                unsafe_allow_html=True,
            )
            render_voice_narration(
                st.session_state["ai_summary"],
                st.session_state["language_used"],
                "dashboard",
            )

        with original_tab:
            st.text_area("Extracted PDF text", st.session_state["report_text"], height=350, label_visibility="collapsed")

        metrics = st.session_state.get("analysis_metrics", {})
        st.caption(
            f"This analysis: {metrics.get('api_calls', 0)} Gemini request attempts · "
            f"{metrics.get('extraction_api_calls', 0)} extraction + "
            f"{metrics.get('explanation_api_calls', 0)} explanation · "
            f"{metrics.get('processing_seconds', 0):.2f} seconds · "
            f"extraction cache {'hit' if metrics.get('extraction_cache_hit') else 'miss'} · "
            f"explanation cache {'hit' if metrics.get('explanation_cache_hit') else 'miss'}"
        )
        download_data = create_download_report(
            rows, st.session_state["ai_summary"], st.session_state["filename"],
            st.session_state["report_type"], st.session_state["prompt_version"],
            st.session_state["level_used"], st.session_state.get("analyzed_at", "Not recorded"),
        )
        st.download_button(
            "⬇️ Download simplified report (.txt)", download_data,
            file_name="Careplain_Simplified_Report.txt", mime="text/plain",
            use_container_width=True, type="primary",
        )


with comparison_tab:
    st.markdown("### Prompt Comparison Lab — Research Mode")
    st.write(
        "Run selected prompt versions against the same extracted report text. "
        "Report type, reading grade and language stay fixed for the comparison."
    )
    st.info(
        "One shared medical extraction is reused. V7 and V10 use it in place of their extraction stage; "
        "V8 keeps its independent verification stage. Up to three versions run at once. "
        "A confirmation shows the request estimate before a live comparison starts."
    )

    comparison_upload = st.file_uploader(
        "Upload the PDF to compare", type=["pdf"], key="comparison_report_pdf",
        help="The PDF text is extracted once and shared unchanged across selected versions.",
        disabled=demo_mode,
    )

    if demo_mode:
        st.success("DEMO MODE — prepared synthetic outputs only. No Gemini requests are made.")
        demo_versions = st.multiselect(
            "Prepared versions to compare", ["V0", "V1", "V2", "V10"],
            default=["V0", "V1", "V2", "V10"], key="demo_comparison_versions",
        )
        st.caption(f"Shared sample settings: Lab Report · {reading_level} · {language}")
        demo_comparison_outputs = {}
        for version in demo_versions:
            output = prepared_explanation(version, language)
            demo_comparison_outputs[version] = output
            with st.expander(f"{version} · Prepared sample structure", expanded=True):
                demo_metric_cols = st.columns(3)
                render_metric(demo_metric_cols[0], count_words(output), "Sample word count")
                render_metric(demo_metric_cols[1], "N/A", "Generation time · prepared")
                render_metric(demo_metric_cols[2], "0", "Gemini requests · demo")
                st.markdown(output)
                st.caption("Prepared sample data. This is not live AI output or an automatic quality score.")
        if demo_comparison_outputs:
            demo_narration_version = st.selectbox(
                "Sample output to narrate", list(demo_comparison_outputs), key="demo_comparison_narration_version",
            )
            render_voice_narration(
                demo_comparison_outputs[demo_narration_version], language, "demo_comparison",
            )

    elif comparison_upload is not None:
        comparison_bytes = comparison_upload.getvalue()
        comparison_file_id = hashlib.sha256(comparison_bytes).hexdigest()
        all_versions = st.checkbox("Select all prompt versions (V0–V10)", key="comparison_select_all")
        selected_versions = (
            PROMPT_VERSIONS
            if all_versions
            else st.multiselect(
                "Prompt versions to compare",
                PROMPT_VERSIONS,
                default=["V0", "V1", "V2", "V10"],
                help="Choose at least two versions. Only these versions will be run.",
                key="comparison_versions",
            )
        )
        if len(selected_versions) < 2:
            st.warning("Select at least two prompt versions to compare.")

        st.caption(
            f"Shared settings: {report_type} · {reading_level} · {language} · "
            f"{len(selected_versions)} selected version(s)"
        )
        start_comparison = st.button(
            "Compare selected versions",
            type="primary",
            use_container_width=True,
            disabled=len(selected_versions) < 2,
            key="start_prompt_comparison",
        )

        if start_comparison:
            try:
                if (
                    st.session_state.get("comparison_pdf_file_id") == comparison_file_id
                    and st.session_state.get("comparison_pdf_text")
                ):
                    comparison_text = st.session_state["comparison_pdf_text"]
                elif comparison_file_id in st.session_state.get("pdf_text_cache", {}):
                    cached_pdf = st.session_state["pdf_text_cache"][comparison_file_id]
                    comparison_text = cached_pdf["text"]
                    st.session_state["comparison_pdf_page_count"] = cached_pdf["pages"]
                else:
                    reader = PdfReader(BytesIO(comparison_bytes))
                    comparison_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
                    pdf_text_cache = st.session_state.setdefault("pdf_text_cache", {})
                    pdf_text_cache[comparison_file_id] = {
                        "text": comparison_text, "pages": len(reader.pages),
                    }
                    while len(pdf_text_cache) > 10:
                        pdf_text_cache.pop(next(iter(pdf_text_cache)))
                    st.session_state["pdf_text_cache"] = pdf_text_cache
                if not comparison_text:
                    raise ValueError("No readable text was found in this PDF.")
                st.session_state["comparison_pdf_text"] = comparison_text
                st.session_state["comparison_pdf_file_id"] = comparison_file_id
                st.session_state["comparison_pdf_name"] = comparison_upload.name
                st.session_state["comparison_pending"] = {
                    "file_id": comparison_file_id,
                    "versions": list(selected_versions),
                    "report_type": report_type,
                    "reading_level": reading_level,
                    "language": language,
                }
                st.rerun()
            except Exception as error:
                message, details = friendly_error(error, None)
                st.error(message)
                if "readable text" not in str(error).lower():
                    with st.expander("PDF details"):
                        st.code(details)

        comparison_text = (
            st.session_state.get("comparison_pdf_text")
            if st.session_state.get("comparison_pdf_file_id") == comparison_file_id
            else None
        )
        pending = st.session_state.get("comparison_pending")

        if pending and comparison_text:
            current_signature = comparison_signature(
                comparison_text, selected_versions, report_type, reading_level, language
            )
            pending_signature = comparison_signature(
                comparison_text, pending["versions"], pending["report_type"],
                pending["reading_level"], pending["language"],
            )
            pending_matches = (
                pending["file_id"] == comparison_file_id
                and current_signature == pending_signature
            )
            if pending_matches:
                comparison_cache = st.session_state.setdefault("comparison_output_cache", {})
                report_hash = content_hash(comparison_text)
                extracted_cache = st.session_state.setdefault("extracted_report_cache", {})
                pending_cache_keys = {
                    version: comparison_cache_key(
                        comparison_text, pending["report_type"],
                        pending["reading_level"], pending["language"], version,
                    )
                    for version in pending["versions"]
                }
                uncached_versions = [
                    version for version in pending["versions"]
                    if pending_cache_keys[version] not in comparison_cache
                ]
                extraction_needed = bool(uncached_versions) and report_hash not in extracted_cache
                expected_calls = sum(
                    EXPECTED_CALLS[version] - (1 if version in ("V7", "V10") else 0)
                    for version in uncached_versions
                ) + int(extraction_needed)
                st.warning(
                    f"Confirm to run {len(pending['versions'])} selected versions. "
                    f"Estimated requests for this operation: {expected_calls}; quota errors stop immediately, "
                    "and one fallback request may be used for other model failures. "
                    "Cached completed outputs will be reused. A daily quota error stops the run."
                )
                confirm_col, cancel_col = st.columns(2)
                confirm = confirm_col.button(
                    "Confirm and run comparison", type="primary", use_container_width=True,
                    key="confirm_prompt_comparison",
                )
                cancel = cancel_col.button("Cancel", use_container_width=True, key="cancel_prompt_comparison")

                if cancel:
                    st.session_state["comparison_pending"] = None
                    st.info("Comparison cancelled. No Gemini requests were sent.")

                if confirm:
                    try:
                        api_key = st.secrets["GEMINI_API_KEY"]
                    except Exception as error:
                        api_key = None
                        message, details = friendly_error(error, None)
                        st.error(message)
                        with st.expander("Configuration details"):
                            st.code(details)

                    if api_key:
                        comparison_started = time.perf_counter()
                        signature = pending_signature
                        comparison_cache = st.session_state.setdefault("comparison_output_cache", {})
                        runs = st.session_state.setdefault("comparison_runs", {})
                        run = {
                            "signature": signature,
                            "report_identifier": report_identifier(comparison_text),
                            "file_id": comparison_file_id,
                            "selected_versions": list(pending["versions"]),
                            "report_type": pending["report_type"],
                            "reading_level": pending["reading_level"],
                            "language": pending["language"],
                            "filename": st.session_state.get("comparison_pdf_name", "Uploaded PDF"),
                            "results": {},
                            "shared_extraction_api_calls": 0,
                        }
                        runs[signature] = run
                        st.session_state["comparison_runs"] = runs
                        st.session_state["comparison_latest_signature"] = signature
                        progress = st.progress(0, text="Preparing selected versions")
                        status = st.status("Running selected prompt versions in parallel", expanded=True)
                        stage_events = Queue()
                        quota_stop = Event()
                        settings = {
                            "report_type": pending["report_type"],
                            "reading_level": pending["reading_level"],
                            "language": pending["language"],
                        }
                        work = []
                        live_output = {}
                        completed_count = 0

                        for version in pending["versions"]:
                            result_cache_key = pending_cache_keys[version]
                            live_output[version] = st.empty()
                            if result_cache_key in comparison_cache:
                                cached_result = dict(comparison_cache[result_cache_key])
                                if not is_usable_explanation(cached_result.get("response", "")):
                                    comparison_cache.pop(result_cache_key, None)
                                    work.append((version, result_cache_key))
                                    continue
                                cached_result["generated_api_calls"] = cached_result.get("api_calls", 0)
                                cached_result.update({"api_calls": 0, "status": "success", "from_cache": True})
                                run["results"][version] = cached_result
                                with live_output[version].container(border=True):
                                    st.markdown(f"#### {version} · Cached result")
                                    st.markdown(cached_result["response"])
                                completed_count += 1
                            else:
                                work.append((version, result_cache_key))

                        extraction_metrics = new_usage_metrics()
                        shared_findings = extracted_cache.get(report_hash)
                        extraction_error = None
                        if work and shared_findings is None:
                            status.update(label="Extracting shared medical information once", state="running", expanded=True)
                            try:
                                shared_findings = extract_medical_tests(
                                    comparison_text, api_key, metrics=extraction_metrics,
                                )
                                extracted_cache[report_hash] = shared_findings
                                while len(extracted_cache) > 10:
                                    extracted_cache.pop(next(iter(extracted_cache)))
                                st.session_state["extracted_report_cache"] = extracted_cache
                            except Exception as error:
                                extraction_error = error
                                if is_quota_exhaustion(error):
                                    quota_stop.set()
                        run["shared_extraction_api_calls"] = extraction_metrics["api_calls"]
                        run["shared_extraction_cached"] = bool(work) and extraction_metrics["api_calls"] == 0

                        if extraction_error is not None and quota_stop.is_set():
                            message, details = friendly_error(extraction_error, api_key)
                            for version, _ in work:
                                run["results"][version] = {
                                    "status": "failed", "strategy": PROMPT_STRATEGIES[version],
                                    "error": message, "details": details,
                                    "processing_seconds": 0.0,
                                    "api_calls": 0, "models": [], "headings": [],
                                    "word_count": 0, "from_cache": False,
                                }
                                with live_output[version].container(border=True):
                                    st.markdown(f"#### {version} · Failed")
                                    st.error(message)
                            work = []
                        elif extraction_error is not None:
                            message, details = friendly_error(extraction_error, api_key)
                            run["shared_extraction_fallback"] = message
                            run["shared_extraction_details"] = details
                            st.warning(
                                "Shared extraction was unavailable. Selected versions will continue from the "
                                "original PDF text; V7 and V10 will use their own extraction stage."
                            )

                        total_versions = len(pending["versions"])
                        progress.progress(
                            completed_count / total_versions,
                            text=f"{completed_count} of {total_versions} versions ready",
                        )
                        max_parallel_versions = 3
                        next_work = [0]
                        futures = {}

                        def submit_available(executor):
                            while (
                                next_work[0] < len(work)
                                and len(futures) < max_parallel_versions
                                and not quota_stop.is_set()
                            ):
                                version, cache_key = work[next_work[0]]
                                next_work[0] += 1
                                future = executor.submit(
                                    run_prompt_comparison_version,
                                    version,
                                    comparison_text,
                                    settings,
                                    api_key,
                                    quota_stop,
                                    stage_events,
                                    {"tests": shared_findings} if shared_findings is not None else None,
                                )
                                futures[future] = (version, cache_key)

                        with ThreadPoolExecutor(max_workers=max_parallel_versions) as executor:
                            submit_available(executor)
                            while futures:
                                while True:
                                    try:
                                        current_version, stage_label, stage_state = stage_events.get_nowait()
                                    except Empty:
                                        break
                                    suffix = "…" if stage_state == "running" else " complete"
                                    status.update(
                                        label=f"{current_version}: {stage_label}{suffix}",
                                        state="running",
                                        expanded=True,
                                    )

                                finished, _ = wait(
                                    futures,
                                    timeout=0.15,
                                    return_when=FIRST_COMPLETED,
                                )
                                if not finished:
                                    continue

                                for future in finished:
                                    version, result_cache_key = futures.pop(future)
                                    result = future.result()
                                    run["results"][version] = result

                                    if result["status"] == "success":
                                        comparison_cache[result_cache_key] = dict(result)
                                        while len(comparison_cache) > 22:
                                            comparison_cache.pop(next(iter(comparison_cache)))
                                        with live_output[version].container(border=True):
                                            st.markdown(f"#### {version} · Result ready")
                                            st.markdown(result["response"])
                                    else:
                                        with live_output[version].container(border=True):
                                            st.markdown(f"#### {version} · {result['status'].replace('_', ' ').title()}")
                                            st.error(result.get("error", "No result returned."))

                                    completed_count += 1
                                    st.session_state["comparison_runs"][signature] = run
                                    st.session_state["comparison_output_cache"] = comparison_cache
                                    progress.progress(
                                        completed_count / total_versions,
                                        text=f"{completed_count} of {total_versions} versions recorded",
                                    )

                                if not quota_stop.is_set():
                                    submit_available(executor)

                        for version, _ in work[next_work[0]:]:
                            if version not in run["results"]:
                                run["results"][version] = {
                                    "status": "not_run",
                                    "strategy": PROMPT_STRATEGIES[version],
                                    "error": "Not run because the daily quota stopped further requests.",
                                    "processing_seconds": 0.0,
                                    "api_calls": 0,
                                    "models": [],
                                    "headings": [],
                                    "word_count": 0,
                                    "from_cache": False,
                                }
                                completed_count += 1

                        st.session_state["comparison_runs"][signature] = run

                        status.update(
                            label="Comparison finished with recorded results",
                            state="complete",
                            expanded=False,
                        )
                        progress.progress(1.0, text="Selected versions recorded")
                        run["total_api_calls"] = (
                            run["shared_extraction_api_calls"]
                            + sum(result.get("api_calls", 0) for result in run["results"].values())
                        )
                        run["processing_seconds"] = time.perf_counter() - comparison_started
                        st.session_state["comparison_pending"] = None
                        st.session_state["comparison_output_cache"] = comparison_cache
                        st.session_state["comparison_runs"] = runs

            elif pending:
                st.info("The PDF or shared settings changed after confirmation was requested. Click Compare again to review the updated request.")
                st.session_state["comparison_pending"] = None

        latest_signature = st.session_state.get("comparison_latest_signature")
        latest_runs = st.session_state.get("comparison_runs", {})
        latest_run = latest_runs.get(latest_signature) if latest_signature else None
        if latest_run and latest_run.get("file_id") == comparison_file_id:
            st.markdown("---")
            st.markdown("### Comparison results")
            st.caption(
                f"Report ID: {latest_run['report_identifier']} · "
                f"{latest_run['report_type']} · {latest_run['reading_level']} · {latest_run['language']}"
            )
            st.caption(
                f"Gemini request attempts this comparison: {latest_run.get('total_api_calls', 0)} "
                f"(shared extraction: {latest_run.get('shared_extraction_api_calls', 0)}; "
                f"version generation: {sum(result.get('api_calls', 0) for result in latest_run['results'].values())}) · "
                f"Total processing time: {latest_run.get('processing_seconds', 0):.2f} seconds"
            )
            if latest_run.get("shared_extraction_fallback"):
                st.warning(
                    "The shared extraction step failed, so this comparison continued from the original PDF text. "
                    "V7/V10 used their own extraction stage."
                )
                if latest_run.get("shared_extraction_details"):
                    with st.expander("Shared extraction details"):
                        st.code(latest_run["shared_extraction_details"])

            successful = [
                version for version in latest_run["selected_versions"]
                if latest_run["results"].get(version, {}).get("status") == "success"
                and is_usable_explanation(latest_run["results"].get(version, {}).get("response", ""))
            ]
            if not successful:
                st.warning("No prompt version produced an explanation. Recorded failures are shown below.")

            for version in latest_run["selected_versions"]:
                result = latest_run["results"].get(version)
                if not result:
                    continue
                with st.expander(f"{version} · {PROMPT_STRATEGIES[version]} · {result['status'].replace('_', ' ').title()}", expanded=False):
                    st.caption(f"Prompt strategy: {PROMPT_STRATEGIES[version]}")
                    if result["status"] == "success" and is_usable_explanation(result.get("response", "")):
                        stat_cols = st.columns(4)
                        render_metric(stat_cols[0], result["word_count"], "Whitespace-counted words")
                        render_metric(stat_cols[1], f"{result['processing_seconds']:.2f} s", "Measured generation time")
                        render_metric(stat_cols[2], result["api_calls"], "Actual API request attempts")
                        render_metric(stat_cols[3], "Cached" if result.get("from_cache") else "Generated", "This comparison")
                        st.markdown("**Detected headings in this response**")
                        st.write(" · ".join(result["headings"]) if result["headings"] else "No explicit headings detected.")
                        st.markdown("**Complete generated explanation**")
                        st.markdown(result["response"])
                        observation_key = f"comparison_observation_{latest_signature}_{version}"
                        st.text_area(
                            "Researcher observations (manual; not an automatic score)",
                            key=observation_key,
                            placeholder="Record structure, readability, preserved values, omissions or unsupported content.",
                        )
                    else:
                        st.error(result.get("error", "The saved response was incomplete. Run this version again."))
                        st.caption(f"Time: {result.get('processing_seconds', 0):.2f} s · API attempts: {result.get('api_calls', 0)}")
                        if result.get("details"):
                            st.code(result["details"])

            if len(successful) >= 2:
                st.markdown("#### Side-by-side output comparison")
                left, right = st.columns(2)
                first_version = left.selectbox("First output", successful, key=f"compare_left_{latest_signature}")
                second_choices = [version for version in successful if version != first_version]
                second_version = right.selectbox("Second output", second_choices, key=f"compare_right_{latest_signature}")
                left.markdown(f"##### {first_version} — {PROMPT_STRATEGIES[first_version]}")
                left.markdown(latest_run["results"][first_version]["response"])
                right.markdown(f"##### {second_version} — {PROMPT_STRATEGIES[second_version]}")
                right.markdown(latest_run["results"][second_version]["response"])

            if successful:
                st.markdown("#### Comparison summary")
                min_words = min(latest_run["results"][v]["word_count"] for v in successful)
                max_words = max(latest_run["results"][v]["word_count"] for v in successful)
                max_headings = max(len(latest_run["results"][v]["headings"]) for v in successful)
                summary_cols = st.columns(3)
                render_metric(summary_cols[0], ", ".join(v for v in successful if latest_run["results"][v]["word_count"] == min_words), "Shortest output (word count)")
                render_metric(summary_cols[1], ", ".join(v for v in successful if latest_run["results"][v]["word_count"] == max_words), "Longest output (word count)")
                render_metric(summary_cols[2], ", ".join(v for v in successful if len(latest_run["results"][v]["headings"]) == max_headings), "Most detected headings")
                st.caption("These are descriptive measurements only; they do not evaluate medical accuracy or determine which prompt is better.")
                st.table([
                    {
                        "Version": version,
                        "Processing time (s)": round(latest_run["results"][version]["processing_seconds"], 2),
                        "API request attempts": latest_run["results"][version]["api_calls"],
                        "Detected headings": len(latest_run["results"][version]["headings"]),
                    }
                    for version in latest_run["selected_versions"]
                    if latest_run["results"].get(version, {}).get("status") == "success"
                ])

                st.markdown("#### Narrate a comparison output")
                narration_version = st.selectbox("Prompt version to narrate", successful, key=f"narration_version_{latest_signature}")
                render_voice_narration(
                    latest_run["results"][narration_version]["response"],
                    latest_run["language"],
                    f"comparison_{latest_signature}_{narration_version}",
                )

            export_rows = []
            for version in latest_run["selected_versions"]:
                result = latest_run["results"].get(version, {})
                observation_key = f"comparison_observation_{latest_signature}_{version}"
                export_rows.append({
                    "report_identifier": latest_run["report_identifier"],
                    "selected_prompt_version": version,
                    "report_type": latest_run["report_type"],
                    "target_reading_grade": latest_run["reading_level"],
                    "language": latest_run["language"],
                    "status": result.get("status", "not_run"),
                    "error": result.get("error", ""),
                    "complete_ai_response": (
                        result.get("response", "")
                        if is_usable_explanation(result.get("response", "")) else ""
                    ),
                    "detected_headings": result.get("headings", []),
                    "word_count": result.get("word_count", 0),
                    "processing_time_seconds": result.get("processing_seconds", 0),
                    "api_request_attempts": result.get("api_calls", 0),
                    "researcher_observations": st.session_state.get(observation_key, ""),
                })

            export_col1, export_col2 = st.columns(2)
            export_col1.download_button(
                "Download comparison JSON",
                data=json.dumps(export_rows, ensure_ascii=False, indent=2),
                file_name=f"Careplain_Comparison_{latest_run['report_identifier']}.json",
                mime="application/json",
                use_container_width=True,
            )
            csv_stream = StringIO()
            csv_fields = list(export_rows[0].keys()) if export_rows else []
            csv_writer = DictWriter(csv_stream, fieldnames=csv_fields)
            if csv_fields:
                csv_writer.writeheader()
                for export_row in export_rows:
                    csv_row = dict(export_row)
                    csv_row["detected_headings"] = " | ".join(csv_row["detected_headings"])
                    csv_writer.writerow(csv_row)
            export_col2.download_button(
                "Download comparison CSV",
                data=csv_stream.getvalue(),
                file_name=f"Careplain_Comparison_{latest_run['report_identifier']}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    elif not demo_mode:
        st.info("Upload a PDF above to configure a prompt comparison. No Gemini calls are made until you confirm the selected versions.")


with research_tab:
    st.markdown("### Prompt engineering research")
    st.write("Compare the operational measurements recorded for the latest prompt comparison. These charts describe response length and generation effort; they do not score clarity, accuracy, or medical quality.")
    if "analysis_metrics" in st.session_state:
        metrics = st.session_state["analysis_metrics"]
        research_cols = st.columns(3)
        render_metric(research_cols[0], st.session_state.get("prompt_version", "—"), "Prompt version")
        render_metric(research_cols[1], f"{metrics.get('processing_seconds', 0):.1f} s", "Processing time")
        render_metric(research_cols[2], metrics.get("api_calls", 0), "Gemini request attempts this run")
        st.markdown("#### Run configuration")
        st.write({
            "Report type": st.session_state.get("report_type", "—"),
            "Target reading grade": st.session_state.get("level_used", "—"),
            "Language": st.session_state.get("language_used", "—"),
            "Gemini models used": ", ".join(metrics.get("models", [])) or "Not recorded",
            "Analysis date and time": st.session_state.get("analyzed_at", "Not recorded"),
        })
        if metrics.get("token_metadata_available"):
            st.write(f"Input tokens reported: {metrics['input_tokens']} · Output tokens reported: {metrics['output_tokens']}")
        else:
            st.info("Token usage metadata: Not reported by the API response.")
    else:
        st.info("Run an analysis to record its prompt configuration, processing time and API request attempts.")

    st.markdown("#### Latest prompt comparison")
    research_signature = st.session_state.get("comparison_latest_signature")
    research_run = st.session_state.get("comparison_runs", {}).get(research_signature)
    if research_run:
        research_results = research_run.get("results", {})
        chart_rows = {
            version: result for version, result in research_results.items()
            if result.get("status") == "success"
            and is_usable_explanation(result.get("response", ""))
        }
        if chart_rows:
            versions = list(chart_rows)
            chart_columns = st.columns(2)
            with chart_columns[0]:
                st.markdown("##### Generation time")
                st.bar_chart({
                    "Seconds": {
                        version: round(chart_rows[version].get("processing_seconds", 0), 2)
                        for version in versions
                    }
                }, y_label="Seconds")
            with chart_columns[1]:
                st.markdown("##### Output length")
                st.bar_chart({
                    "Words": {
                        version: chart_rows[version].get("word_count", 0)
                        for version in versions
                    }
                }, y_label="Whitespace-counted words")
            st.markdown("##### Gemini request attempts")
            st.bar_chart({
                "Requests": {
                    version: chart_rows[version].get("api_calls", 0)
                    for version in versions
                }
            }, y_label="Request attempts")
            st.caption("Charts use successful outputs from the latest comparison. Shorter or faster outputs are not necessarily easier to understand or more medically accurate.")
        else:
            st.info("The latest comparison has no successful outputs to chart.")
    else:
        st.info("Run a prompt comparison in the Prompt Comparison Lab to see charts comparing its successful versions.")


with info_tab:
    st.markdown("### About Careplain")
    st.markdown(
        "**CAREPLAIN — AI-POWERED MEDICAL REPORT SIMPLIFIER USING PROMPT ENGINEERING**\n\n"
        "An academic research prototype exploring how prompt engineering can improve the accessibility and understanding of complex medical information."
    )
    st.markdown("### Safety and interpretation")
    st.markdown(
        "Careplain preserves source values where available and uses deterministic rules to compare test results with printed reference ranges and flags. "
        "A classification does not diagnose a disease or determine clinical risk. Missing ranges, unclear values, or patient-specific context can limit interpretation."
    )
    st.markdown(
        "- Original values and units should be preserved.\n"
        "- Missing results and reference ranges should not be invented.\n"
        "- Uncertain information should be identified.\n"
        "- Careplain does not diagnose or prescribe medicines.\n"
        "- A qualified healthcare professional should interpret medical results."
    )
    st.markdown("### Privacy")
    st.write("Medical report text is sent to Google's Gemini API for processing. Avoid uploading identifiable medical information unless you have the necessary permission and are comfortable with the data handling arrangements.")
    st.markdown(
        '<div class="disclaimer">Careplain provides educational information only and is not a substitute for professional medical advice, diagnosis, or treatment.</div>',
        unsafe_allow_html=True,
    )


st.markdown('<div class="app-footer">CAREPLAIN · Prompt engineering research prototype · Smart Attention Classification</div>', unsafe_allow_html=True)
