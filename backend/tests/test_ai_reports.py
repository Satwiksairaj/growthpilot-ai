import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
from app.ai_reports import (
    GeneratedReport,
    LearningPlanDay,
    ReportGenerationError,
    TechnologyRecommendation,
    generate_report,
)
from app.main import AssessmentInput


def valid_report() -> GeneratedReport:
    return GeneratedReport(
        title="Technology exploration report",
        summary="Explore practical technology fields based on your stated interests.",
        recommendations=[
            TechnologyRecommendation(
                field=f"Field {index}",
                reason="This field connects with the preferences shared in your assessment.",
                project_idea="Build a small beginner-friendly project and share what you learn.",
            )
            for index in range(1, 4)
        ],
        seven_day_plan=[
            LearningPlanDay(day=day, activity=f"Complete a short exploration activity for day {day}.")
            for day in range(1, 8)
        ],
        next_steps=["Pick a project idea.", "Reflect on which field felt most engaging."],
    )


class GenerateReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = AssessmentInput(
            interests="web",
            coding_experience="beginner",
            education_stage="undergrad",
        )

    @patch.dict(os.environ, {}, clear=True)
    @patch("app.ai_reports.genai.Client")
    def test_uses_structured_labeled_rules_when_key_missing(
        self, client_factory: MagicMock
    ) -> None:
        report = generate_report(self.payload)

        self.assertEqual(report["generation_mode"], "rule-based-development")
        self.assertEqual(len(report["recommendations"]), 3)
        self.assertEqual(len(report["seven_day_plan"]), 7)
        client_factory.assert_not_called()

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
        clear=True,
    )
    @patch("app.ai_reports.genai.Client")
    def test_returns_pydantic_validated_gemini_report(
        self, client_factory: MagicMock
    ) -> None:
        expected = valid_report()
        response = MagicMock()
        response.output_text = expected.model_dump_json()
        client = client_factory.return_value
        client.interactions.create.return_value = response

        report = generate_report(self.payload)

        self.assertEqual(report["generation_mode"], "gemini")
        self.assertEqual(report["model"], "test-model")
        self.assertEqual(len(report["recommendations"]), 3)
        self.assertEqual(len(report["seven_day_plan"]), 7)
        client.interactions.create.assert_called_once()
        prompt = client.interactions.create.call_args.kwargs["input"]
        self.assertNotIn("email", prompt.lower())
        self.assertNotIn("name", prompt.lower())

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
        clear=True,
    )
    @patch("app.ai_reports.genai.Client")
    def test_rejects_invalid_json_without_fallback(
        self, client_factory: MagicMock
    ) -> None:
        client_factory.return_value.interactions.create.return_value.output_text = (
            '{"title":"partial"}'
        )

        with self.assertRaises(ReportGenerationError):
            generate_report(self.payload)

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
        clear=True,
    )
    @patch("app.ai_reports.genai.Client")
    def test_provider_timeout_is_reported(
        self, client_factory: MagicMock
    ) -> None:
        client_factory.return_value.interactions.create.side_effect = httpx.ReadTimeout(
            "provider timeout"
        )

        with self.assertRaises(ReportGenerationError):
            generate_report(self.payload)

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
        clear=True,
    )
    @patch("app.ai_reports.genai.Client")
    def test_provider_failure_is_not_hidden(
        self, client_factory: MagicMock
    ) -> None:
        client_factory.return_value.interactions.create.side_effect = httpx.ConnectError(
            "provider failure"
        )

        with self.assertRaises(ReportGenerationError):
            generate_report(self.payload)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("app.ai_reports.genai.Client")
    def test_missing_model_configuration_fails_explicitly(
        self, client_factory: MagicMock
    ) -> None:
        with self.assertRaises(ReportGenerationError):
            generate_report(self.payload)
        client_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
