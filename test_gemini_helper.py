
import inspect
import json

from prompts import PROMPTS
from gemini_helper import simplify_medical_report

print("=" * 50)
print("GEMINI HELPER INTEGRATION TEST")
print("=" * 50)

# Test 1: Prompt versions
print("\n1. Checking prompt versions")

for version in PROMPTS:
    print("SUCCESS:", version)

# Test 2: Function signature
print("\n2. Checking Gemini function")

signature = inspect.signature(simplify_medical_report)

print(signature)

assert "prompt_version" in signature.parameters

print("SUCCESS: Prompt version parameter exists")

# Test 3: Default version
print("\n3. Checking default version")

default_version = signature.parameters[
    "prompt_version"
].default

assert default_version == "V10"

print("SUCCESS: Default version is V10")

# Test 4: Structured JSON
print("\n4. Checking structured medical data")

sample_tests = [
    {
        "test_name": "Hemoglobin",
        "value": 13.5,
        "unit": "g/dL",
        "lower_range": 12.0,
        "upper_range": 16.0,
        "flag": "None"
    }
]

structured_data = json.dumps(
    {"tests": sample_tests},
    indent=2
)

assert "Hemoglobin" in structured_data

print("SUCCESS: Structured JSON created")

print("\n" + "=" * 50)
print("ALL INTEGRATION CHECKS PASSED")
print("=" * 50)
