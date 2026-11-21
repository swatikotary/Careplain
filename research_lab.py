"""Pure helpers for the prompt comparison research interface."""

import hashlib
import json
import re

from prompts import PROMPTS
from gemini_helper import MODELS as TEXT_MODELS, TEMPERATURE as TEXT_TEMPERATURE


PROMPT_STRATEGIES = {
    "V0": "Basic zero-shot baseline",
    "V1": "Patient-education persona and supportive tone",
    "V2": "Report context, reading-grade and language control",
    "V3": "Structured explanation sections",
    "V4": "Explicit medical safety guardrails",
    "V5": "Plain-language optimization and short output target",
    "V6": "Evidence-grounded explanation with source support",
    "V7": "Structured findings extraction followed by explanation",
    "V8": "Explanation generation followed by independent verification",
    "V9": "Abstention and uncertainty handling",
    "V10": "Structured extraction, grounded explanation and verification",
}

EXPECTED_CALLS = {
    "V0": 1, "V1": 1, "V2": 1, "V3": 1, "V4": 1, "V5": 1,
    "V6": 1, "V7": 2, "V8": 2, "V9": 1, "V10": 3,
}

_KNOWN_HEADINGS = {
    "report summary", "simple summary", "key findings", "test results",
    "results within range", "within range", "attention", "what this means",
    "important information", "missing information", "next steps",
    "medical disclaimer", "questions for your doctor", "limitations",
    "important findings", "results outside printed reference ranges",
}
_NUMBERED_HEADING = re.compile(r"^\s*\d{1,2}[.)]\s+(.+?)\s*$")
_PROMPT_KEYS = {
    "V7": ("V7_EXTRACT", "V7_EXPLAIN"),
    "V8": ("V8_GENERATE", "V8_VERIFY"),
    "V10": ("V10_EXTRACT", "V10_EXPLAIN", "V10_VERIFY"),
}


def report_identifier(report_text):
    """Return a short, non-reversible identifier for a report's exact text."""
    return hashlib.sha256(report_text.encode("utf-8")).hexdigest()[:16]


def comparison_cache_key(report_text, report_type, reading_level, language,
                         prompt_version):
    """Key one version's output to the report and every generation setting."""
    settings = {
        "report_sha256": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        "report_type": report_type,
        "reading_level": reading_level,
        "language": language,
        "prompt_version": prompt_version,
        "text_models": TEXT_MODELS,
        "temperature": TEXT_TEMPERATURE,
        "prompt_template_sha256": hashlib.sha256(
            "\n".join(
                PROMPTS[key]
                for key in _PROMPT_KEYS.get(prompt_version, (prompt_version,))
            ).encode("utf-8")
        ).hexdigest(),
    }
    return hashlib.sha256(
        json.dumps(settings, sort_keys=True).encode("utf-8")
    ).hexdigest()


def count_words(response):
    """Count whitespace-separated words consistently across selected scripts."""
    return len(response.split())


def detect_headings(response):
    """Return headings visibly present in a response, without inferring content."""
    found = []
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        candidate = line
        explicit_heading = False
        if candidate.startswith("#"):
            candidate = candidate.lstrip("# ").strip()
            explicit_heading = True
        else:
            numbered = _NUMBERED_HEADING.match(candidate)
            if numbered:
                candidate = numbered.group(1).strip()
                explicit_heading = True
            if candidate.startswith("**") and candidate.endswith("**"):
                candidate = candidate[2:-2].strip()
                explicit_heading = True
            if candidate.endswith(":") and len(candidate) <= 90:
                candidate = candidate[:-1].strip()
                explicit_heading = True

        normalized = re.sub(r"\s+", " ", candidate).strip().casefold()
        if (explicit_heading or normalized in _KNOWN_HEADINGS) and candidate:
            if candidate not in found:
                found.append(candidate)
    return found


def looks_like_daily_quota_error(error):
    message = str(error).casefold()
    return (
        "resource_exhausted" in message
        or "429" in message
        or "daily request quota is exhausted" in message
        or "generate_content_free_tier_requests" in message
        or "requests per day" in message
        or "per day" in message and ("quota" in message or "resource_exhausted" in message)
    )
