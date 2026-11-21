
import json
import re

from google import genai
from google.genai import types
from api_optimization import is_quota_exhaustion


# ==========================================
# GEMINI MODEL CONFIGURATION
# ==========================================

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash"
]
REQUEST_TIMEOUT_MS = 30_000


# ==========================================
# GEMINI RESPONSE WITH BOUNDED MODEL FALLBACK
# ==========================================

def generate_response(client, prompt, metrics=None, stop_event=None):

    last_error = None

    for model in MODELS:
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("Gemini quota is exhausted; stopped before another call.")
        try:
            if metrics is not None:
                metrics["api_calls"] += 1
                if model not in metrics["models"]:
                    metrics["models"].append(model)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )
            if not response.text:
                raise ValueError("Gemini returned an empty response.")
            usage = getattr(response, "usage_metadata", None)
            if usage is not None and metrics is not None:
                prompt_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
                if prompt_tokens is not None or output_tokens is not None:
                    metrics["token_metadata_available"] = True
                    metrics["input_tokens"] += prompt_tokens or 0
                    metrics["output_tokens"] += output_tokens or 0
            return response.text
        except Exception as error:
            last_error = error
            if is_quota_exhaustion(error):
                if stop_event is not None:
                    stop_event.set()
                raise RuntimeError(
                    "Gemini quota was exhausted (429 RESOURCE_EXHAUSTED). "
                    "Wait for the quota reset or review the project's limits."
                ) from error
            fallback_error = str(error).upper()
            if not any(code in fallback_error for code in (
                "503", "UNAVAILABLE", "500", "INTERNAL", "404", "NOT_FOUND",
                "504", "GATEWAY TIMEOUT", "TIMED OUT", "TIMEOUT", "DEADLINE EXCEEDED",
            )):
                break

    raise RuntimeError(f"Gemini API request failed: {last_error}") from last_error


# ==========================================
# EXTRACT MEDICAL TEST RESULTS
# ==========================================

def extract_medical_tests(report, api_key, metrics=None, on_stage=None, stop_event=None):

    if not api_key:
        raise ValueError("Gemini API key is required.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    prompt = f"""
You are a medical report information extraction assistant.

Read the medical report carefully.

Extract ALL medical test results.

For every test, identify:

1. Test name
2. Original numerical value
3. Measurement unit
4. Lower reference range
5. Upper reference range
6. Laboratory flag (High, Low, Critical or None)

IMPORTANT RULES:

- Extract every available medical test.
- Preserve original numerical values.
- Preserve original measurement units.
- Never invent missing values.
- Never create reference ranges.
- If information is missing, use null.
- Preserve the laboratory's original flag.
- If the report explicitly states High, Low or Critical,
  preserve that flag.
- Do not diagnose diseases.
- Do not prescribe medicines.

Return ONLY valid JSON in this format:

{{
    "tests": [
        {{
            "test_name": "Hemoglobin",
            "value": 13.5,
            "unit": "g/dL",
            "lower_range": 12.0,
            "upper_range": 16.0,
            "flag": "None"
        }}
    ]
}}

If no tests are found, return:

{{
    "tests": []
}}

MEDICAL REPORT:

{report}
"""

    if on_stage:
        on_stage("Extracting medical test results", "running")
    response_text = generate_response(
        client, prompt, metrics=metrics, stop_event=stop_event
    )

    try:
        result = json.loads(response_text)

    except json.JSONDecodeError:

        cleaned_text = re.sub(
            r"```(?:json)?|```",
            "",
            response_text
        ).strip()

        result = json.loads(cleaned_text)

    if not isinstance(result, dict):
        raise ValueError("Invalid medical test data: expected a JSON object.")

    tests = result.get("tests", [])

    if not isinstance(tests, list) or any(not isinstance(test, dict) for test in tests):
        raise ValueError("Invalid medical test data returned by Gemini.")

    if on_stage:
        on_stage("Extracting medical test results", "complete")

    return tests
