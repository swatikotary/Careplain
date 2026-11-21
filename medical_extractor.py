
import json
import re
import time

from google import genai


# ==========================================
# GEMINI MODEL CONFIGURATION
# ==========================================

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash"
]


# ==========================================
# GEMINI RESPONSE WITH RETRY
# ==========================================

def generate_response(client, prompt):

    last_error = None
    quota_error = None

    for model in MODELS:

        for attempt in range(2):

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1
                    }
                )

                if not response.text:
                    raise ValueError("Gemini returned an empty response.")

                return response.text

            except Exception as e:

                last_error = e
                error_message = str(e).upper()
                daily_quota = (
                    "GENERATE_CONTENT_FREE_TIER_REQUESTS" in error_message
                    or "PER DAY" in error_message
                    or "REQUESTS PER DAY" in error_message
                )

                if daily_quota:
                    # Daily quota limits will not clear after a short retry.
                    quota_error = e
                    break

                temporary_error = any(
                    code in error_message
                    for code in [
                        "503",
                        "UNAVAILABLE",
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "500",
                        "INTERNAL"
                    ]
                )

                if temporary_error and attempt == 0:
                    time.sleep(2)
                    continue

                break

    if quota_error is not None:
        raise RuntimeError(
            "Gemini's daily request quota is exhausted for the available "
            "model(s). Wait for the quota reset or enable billing/increase "
            f"the API quota. Details: {quota_error}"
        ) from quota_error

    raise RuntimeError(f"Gemini API request failed: {last_error}") from last_error


# ==========================================
# EXTRACT MEDICAL TEST RESULTS
# ==========================================

def extract_medical_tests(report, api_key):

    if not api_key:
        raise ValueError("Gemini API key is required.")

    client = genai.Client(api_key=api_key)

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

    response_text = generate_response(client, prompt)

    try:
        result = json.loads(response_text)

    except json.JSONDecodeError:

        cleaned_text = re.sub(
            r"```(?:json)?|```",
            "",
            response_text
        ).strip()

        result = json.loads(cleaned_text)

    tests = result.get("tests", [])

    if not isinstance(tests, list):
        raise ValueError("Invalid medical test data returned by Gemini.")

    return tests
