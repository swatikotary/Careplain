import unittest
from threading import Event
from unittest.mock import patch

from api_optimization import (
    explanation_cache_key,
    get_or_create,
    is_quota_exhaustion,
    is_usable_explanation,
)
from gemini_helper import generate_response
from prompts import PROMPT_VERSIONS
from demo_data import SAMPLE_TESTS, prepared_explanation
from classifier import classify_result


class ApiOptimizationTests(unittest.TestCase):
    def test_cached_operation_does_not_call_generator_twice(self):
        cache = {}
        calls = []

        first, first_hit = get_or_create(cache, "same-input", lambda: calls.append(1) or "answer")
        second, second_hit = get_or_create(cache, "same-input", lambda: calls.append(2) or "other")

        self.assertEqual((first, second), ("answer", "answer"))
        self.assertFalse(first_hit)
        self.assertTrue(second_hit)
        self.assertEqual(calls, [1])

    def test_explanation_cache_key_tracks_all_user_settings(self):
        base = explanation_cache_key("report", "V2", "Lab Report", "Grade 7", "English")
        self.assertNotEqual(base, explanation_cache_key("other report", "V2", "Lab Report", "Grade 7", "English"))
        self.assertNotEqual(base, explanation_cache_key("report", "V3", "Lab Report", "Grade 7", "English"))
        self.assertNotEqual(base, explanation_cache_key("report", "V2", "Lab Report", "Grade 8", "English"))
        self.assertNotEqual(base, explanation_cache_key("report", "V2", "Lab Report", "Grade 7", "Hindi"))

    def test_all_prompt_versions_remain_available(self):
        self.assertEqual(PROMPT_VERSIONS, [f"V{i}" for i in range(11)])

    def test_429_resource_exhausted_is_a_hard_quota_error(self):
        self.assertTrue(is_quota_exhaustion("429 RESOURCE_EXHAUSTED"))
        self.assertTrue(is_quota_exhaustion("generate_content_free_tier_requests per day"))
        self.assertFalse(is_quota_exhaustion("503 UNAVAILABLE"))

    def test_unusable_cached_markdown_is_rejected(self):
        self.assertFalse(is_usable_explanation("- * - * - *"))
        self.assertTrue(is_usable_explanation("Hemoglobin is 11.2 g/dL and marked low in this sample."))

    def test_quota_error_is_not_retried_on_another_model(self):
        class FakeModels:
            calls = 0

            def generate_content(self, **kwargs):
                self.calls += 1
                raise RuntimeError("429 RESOURCE_EXHAUSTED: requests per day quota")

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        client = FakeClient()
        stop_event = Event()
        with self.assertRaisesRegex(RuntimeError, "quota was exhausted"):
            generate_response(client, "prompt", stop_event=stop_event)
        self.assertEqual(client.models.calls, 1)
        self.assertTrue(stop_event.is_set())

    def test_extractor_quota_error_is_not_retried(self):
        from medical_extractor import generate_response as extract_response

        class FakeModels:
            calls = 0

            def generate_content(self, **kwargs):
                self.calls += 1
                raise RuntimeError("429 RESOURCE_EXHAUSTED: requests per day quota")

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        client = FakeClient()
        with self.assertRaisesRegex(RuntimeError, "quota was exhausted"):
            extract_response(client, "prompt")
        self.assertEqual(client.models.calls, 1)

    def test_demo_outputs_are_prepared_and_multilingual(self):
        languages = ("English", "Kannada", "Hindi", "Tamil", "Telugu", "Malayalam", "Bengali", "Marathi")
        for language in languages:
            for version in ("V0", "V1", "V2", "V10"):
                output = prepared_explanation(version, language)
                self.assertIn("11.2 g/dL", output)
                self.assertIn("105 mg/dL", output)
        self.assertEqual(classify_result(11.2, 12, 16, "Low"), "Attention")
        self.assertEqual(classify_result(105, 70, 140, "None"), "Within Range")

    def test_gemini_client_has_a_timeout_and_sdk_retries_disabled(self):
        class FakeResponse:
            text = "ready"
            usage_metadata = None

        class FakeModels:
            def generate_content(self, **kwargs):
                return FakeResponse()

        class FakeClient:
            models = FakeModels()

        with patch("gemini_helper.genai.Client", return_value=FakeClient()) as client_factory:
            from gemini_helper import simplify_medical_report
            simplify_medical_report("sample", "Grade 7", "placeholder", prompt_version="V0")
        http_options = client_factory.call_args.kwargs["http_options"]
        self.assertEqual(http_options.timeout, 30_000)
        self.assertEqual(http_options.retry_options.attempts, 1)

    def test_single_fallback_is_tried_after_a_timeout(self):
        class FakeResponse:
            text = "A useful patient-friendly explanation with enough detail to display safely."
            usage_metadata = None

        class FakeModels:
            def __init__(self):
                self.calls = 0

            def generate_content(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TimeoutError("request timed out")
                return FakeResponse()

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        client = FakeClient()
        response = generate_response(client, "prompt")
        self.assertIn("patient-friendly explanation", response)
        self.assertEqual(client.models.calls, 2)

    def test_v7_reuses_extraction_and_v10_keeps_verification(self):
        class FakeResponse:
            text = "A prepared explanation."
            usage_metadata = None

        class FakeModels:
            def __init__(self):
                self.calls = []

            def generate_content(self, **kwargs):
                self.calls.append(kwargs["contents"])
                return FakeResponse()

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        sample_findings = {"tests": [{"test_name": "Hemoglobin", "value": 11.2, "unit": "g/dL"}]}
        with patch("gemini_helper.genai.Client") as factory:
            from gemini_helper import simplify_medical_report
            v7_client = FakeClient()
            factory.return_value = v7_client
            stages = []
            simplify_medical_report(
                "original full report text", "Grade 7", "placeholder", "V7",
                pre_extracted_findings=sample_findings,
                on_stage=lambda label, state: stages.append((label, state)),
            )
            self.assertEqual(len(v7_client.models.calls), 1)
            self.assertNotIn("original full report text", v7_client.models.calls[0])
            self.assertIn("Hemoglobin", v7_client.models.calls[0])
            self.assertFalse(any("Extracting prompt findings" == label and state == "running" for label, state in stages))

            v10_client = FakeClient()
            factory.return_value = v10_client
            stages.clear()
            simplify_medical_report(
                "original full report text", "Grade 7", "placeholder", "V10",
                pre_extracted_findings=sample_findings,
                on_stage=lambda label, state: stages.append((label, state)),
            )
            self.assertEqual(len(v10_client.models.calls), 2)
            self.assertTrue(any(label == "Verifying explanation" and state == "running" for label, state in stages))
            self.assertIn("original full report text", v10_client.models.calls[-1])


if __name__ == "__main__":
    unittest.main()
