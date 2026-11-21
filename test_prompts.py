
from prompts import PROMPT_VERSIONS, get_prompt

print("=" * 50)
print("CAREPLAIN - PROMPT ENGINEERING TEST")
print("=" * 50)

sample_report = """
Hemoglobin: 13.5 g/dL
Reference range: 12.0 - 16.0
Glucose: 180 mg/dL
Reference range: 70 - 140
"""

print("\n1. Checking all prompt versions...")

for version in PROMPT_VERSIONS:
    print("Available:", version)

print("\n2. Testing prompt generation...")

for version in PROMPT_VERSIONS:
    try:
        generated_prompt = get_prompt(
            version,
            sample_report,
            report_type="Lab Report",
            reading_level="Grade 7"
        )

        assert isinstance(generated_prompt, str)
        assert len(generated_prompt) > 0
        assert sample_report in generated_prompt

        print("SUCCESS:", version)

    except Exception as error:
        print("FAILED:", version, "|", error)

print("\n" + "=" * 50)
print("PROMPT TEST COMPLETED")
print("=" * 50)
