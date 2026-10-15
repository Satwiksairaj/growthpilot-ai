import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app import main
from app.ai_reports import ReportGenerationError, rule_based_report


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(
            main, "DATABASE_PATH", Path(self.temp_dir.name) / "test.sqlite3"
        )
        self.database_patch.start()
        self.environment_patch = patch.dict(os.environ, {}, clear=True)
        self.environment_patch.start()
        main.initialize_database()
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()
        self.payload = {
            "interests": "web",
            "coding_experience": "beginner",
            "education_stage": "undergrad",
        }

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.environment_patch.stop()
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_health_reports_safe_configuration_status(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertFalse(response.json()["configuration"]["gemini_configured"])
        self.assertNotIn("GEMINI_API_KEY", json.dumps(response.json()))

    def test_health_reports_postgres_without_exposing_connection_string(self) -> None:
        database_url = "postgresql://test-user:test-password@example.test/growthpilot"
        with patch.object(main, "DATABASE_URL", database_url):
            response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["configuration"]["database"], "postgresql")
        self.assertNotIn("test-password", response.text)

    def test_health_supports_render_n8n_service_reference(self) -> None:
        with patch.dict(
            os.environ,
            {
                "N8N_BASE_URL": "growthpilot-ai-n8n.onrender.com",
                "N8N_WEBHOOK_SECRET": "test-webhook-secret",
            },
        ):
            response = self.client.get("/api/health")
            webhook_url = main.n8n_webhook_url()

        self.assertTrue(response.json()["configuration"]["n8n_configured"])
        self.assertEqual(
            webhook_url,
            "https://growthpilot-ai-n8n.onrender.com/webhook/growthpilot/consented-lead",
        )

    def test_metrics_reports_automation_configured_from_render_service_reference(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "N8N_BASE_URL": "growthpilot-ai-n8n.onrender.com",
                "N8N_WEBHOOK_SECRET": "test-webhook-secret",
            },
        ):
            metrics = self.client.get("/api/metrics").json()

        self.assertTrue(metrics["automation"]["configured"])
        self.assertIn("temporary SQLite database", metrics["note"])

    def test_metrics_note_reflects_postgres_configuration_without_secrets(self) -> None:
        with patch.object(
            main, "DATABASE_URL", "postgresql://user:password@example.test/growthpilot"
        ):
            note = main.metrics_note("2026-10-15T00:00:00+00:00")

        self.assertIn("configured PostgreSQL database", note)
        self.assertIn("Availability and backups depend on the database provider", note)
        self.assertNotIn("password", note)

    def test_postgres_connection_translates_parameters_and_returns_mapping_rows(
        self,
    ) -> None:
        class FakeCursor:
            def fetchone(self):
                return {"event_id": "event-1", "status": "pending"}

            def fetchall(self):
                return [{"event_id": "event-1", "status": "pending"}]

        class FakeConnection:
            def execute(self, statement, parameters):
                self.statement = statement
                self.parameters = parameters
                return FakeCursor()

        fake_connection = FakeConnection()
        errors = SimpleNamespace(
            IntegrityError=type("IntegrityError", (Exception,), {}),
            Error=Exception,
        )
        connection = main.PostgresConnection(fake_connection, errors)

        cursor = connection.execute(
            "SELECT event_id, status FROM events WHERE event_id = ?",
            ("event-1",),
        )
        row = cursor.fetchone()

        self.assertEqual(
            fake_connection.statement,
            "SELECT event_id, status FROM events WHERE event_id = %s",
        )
        self.assertEqual(fake_connection.parameters, ("event-1",))
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row[0], "event-1")

    def test_postgres_database_url_selects_psycopg_connection(self) -> None:
        fake_connection = MagicMock()
        with (
            patch.object(main, "DATABASE_URL", "postgresql://example.test/database"),
            patch("psycopg.connect", return_value=fake_connection) as connect,
        ):
            connection = main.connect_database()

        self.assertIsInstance(connection, main.PostgresConnection)
        self.assertEqual(
            connect.call_args.kwargs["connect_timeout"],
            10,
        )
        self.assertIsNotNone(connect.call_args.kwargs["row_factory"])

    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_assessment_returns_and_persists_rule_based_report(
        self, _generator: MagicMock
    ) -> None:
        response = self.client.post(
            "/api/assessments",
            json=self.payload,
            headers={"Idempotency-Key": "assessment-test-0001"},
        )

        self.assertEqual(response.status_code, 200)
        report = response.json()["report"]
        self.assertEqual(report["generation_mode"], "rule-based-development")
        self.assertEqual(len(report["recommendations"]), 3)
        self.assertEqual(len(report["seven_day_plan"]), 7)
        with closing(main.connect_database()) as connection:
            row = connection.execute(
                "SELECT report_json, report_status FROM assessments"
            ).fetchone()
        self.assertEqual(row["report_status"], "generated")
        self.assertEqual(json.loads(row["report_json"]), report)

    def test_invalid_assessment_is_rejected(self) -> None:
        response = self.client.post(
            "/api/assessments",
            json={**self.payload, "interests": "undecided"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/metrics").json()["metrics"]["completions"], 0)

    @patch("app.main.generate_report", side_effect=ReportGenerationError())
    def test_provider_failure_does_not_create_success_record(
        self, _generator: MagicMock
    ) -> None:
        response = self.client.post("/api/assessments", json=self.payload)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get("/api/metrics").json()["metrics"]["reports"], 0)

    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_lead_is_persisted_only_with_explicit_consent(
        self, _generator: MagicMock
    ) -> None:
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {
                    "name": "Example Student",
                    "email": "STUDENT@example.com",
                    "consent": True,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["automation"]["status"], "not_configured")
        with closing(main.connect_database()) as connection:
            lead = connection.execute(
                "SELECT name, email, consented_at FROM leads"
            ).fetchone()
        self.assertEqual(lead["name"], "Example Student")
        self.assertEqual(lead["email"], "student@example.com")
        self.assertTrue(lead["consented_at"])

    def test_unconsented_lead_is_rejected(self) -> None:
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {"email": "student@example.com", "consent": False},
            },
        )

        self.assertEqual(response.status_code, 422)
        with closing(main.connect_database()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0], 0)

    def test_invalid_lead_submissions_create_no_assessment_or_lead(self) -> None:
        invalid_leads = [
            {"email": "student@example.com", "consent": False},
            {"email": "not-an-email", "consent": True},
            {"name": "   ", "email": " ", "consent": True},
        ]

        with patch("app.main.generate_report", side_effect=rule_based_report) as generator:
            for lead in invalid_leads:
                with self.subTest(lead=lead):
                    response = self.client.post(
                        "/api/assessments",
                        json={**self.payload, "lead": lead},
                    )
                    self.assertEqual(response.status_code, 422)

        generator.assert_not_called()
        with closing(main.connect_database()) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM assessments").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0],
                0,
            )

    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_idempotency_key_prevents_duplicate_assessment_and_lead(
        self, _generator: MagicMock
    ) -> None:
        payload = {
            **self.payload,
            "lead": {"email": "student@example.com", "consent": True},
        }
        headers = {"Idempotency-Key": "assessment-idempotent-001"}
        first = self.client.post("/api/assessments", json=payload, headers=headers)
        replay = self.client.post("/api/assessments", json=payload, headers=headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(first.json()["assessment_id"], replay.json()["assessment_id"])
        with closing(main.connect_database()) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM assessments").fetchone()[0], 1
            )
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0], 1)

    def test_duplicate_visit_is_counted_once(self) -> None:
        event = {
            "visitor_id": str(uuid4()),
            "path": "/assessment",
            "source": "organic",
        }
        first = self.client.post("/api/visits", json=event)
        second = self.client.post("/api/visits", json=event)

        self.assertEqual(first.status_code, 204)
        self.assertEqual(second.status_code, 204)
        metrics = self.client.get("/api/metrics").json()
        self.assertEqual(metrics["metrics"]["visitors"], 1)
        self.assertEqual(metrics["metrics"]["starts"], 1)
        self.assertEqual(metrics["sources"][1], {"name": "organic", "value": 1})

    @patch.dict(
        os.environ,
        {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/test",
            "N8N_WEBHOOK_SECRET": "server-only-test-secret",
        },
    )
    @patch("app.main.httpx.Client")
    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_confirmed_n8n_event_is_marked_and_not_resent(
        self,
        _generator: MagicMock,
        client_factory: MagicMock,
    ) -> None:
        http_client = client_factory.return_value.__enter__.return_value

        def confirm_event(*_args, **kwargs):
            confirmation = MagicMock()
            confirmation.json.return_value = {
                "accepted": True,
                "event_id": kwargs["json"]["event_id"],
            }
            return confirmation

        http_client.post.side_effect = confirm_event
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {"email": "student@example.com", "consent": True},
            },
        )

        self.assertEqual(response.status_code, 200)
        event_id = response.json()["automation"]["event_id"]
        self.assertEqual(response.json()["automation"]["status"], "succeeded")
        request = http_client.post.call_args
        self.assertEqual(
            request.kwargs["headers"]["Authorization"],
            os.environ["N8N_WEBHOOK_SECRET"],
        )
        self.assertNotIn("student@example.com", json.dumps(request.kwargs["json"]))
        main.dispatch_n8n_event(event_id)
        self.assertEqual(http_client.post.call_count, 1)

    @patch.dict(
        os.environ,
        {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/test",
            "N8N_WEBHOOK_SECRET": "server-only-test-secret",
        },
    )
    @patch("app.main.httpx.Client")
    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_assessment_to_consented_lead_updates_database_webhook_and_metrics(
        self,
        _generator: MagicMock,
        client_factory: MagicMock,
    ) -> None:
        visitor_id = str(uuid4())
        self.client.post(
            "/api/visits",
            json={
                "visitor_id": visitor_id,
                "path": "/assessment",
                "source": "organic",
            },
        )
        http_client = client_factory.return_value.__enter__.return_value

        def confirm_event(*_args, **kwargs):
            confirmation = MagicMock()
            confirmation.json.return_value = {
                "accepted": True,
                "event_id": kwargs["json"]["event_id"],
            }
            return confirmation

        http_client.post.side_effect = confirm_event
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "visitor_id": visitor_id,
                "lead": {
                    "name": "Integration Test Student",
                    "email": "integration@example.test",
                    "consent": True,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["report"]["generation_mode"], "rule-based-development")
        self.assertEqual(result["automation"]["status"], "succeeded")
        webhook_request = http_client.post.call_args
        self.assertEqual(
            webhook_request.args[0],
            "https://n8n.example.test/webhook/test",
        )
        self.assertTrue(webhook_request.kwargs["json"]["consent"])
        self.assertNotIn(
            "integration@example.test",
            json.dumps(webhook_request.kwargs["json"]),
        )

        with closing(main.connect_database()) as connection:
            assessment = connection.execute(
                """
                SELECT a.report_json, l.email, l.consented_at, e.status
                FROM assessments a
                JOIN leads l ON l.assessment_id = a.assessment_id
                JOIN lead_automation_events e ON e.lead_id = l.lead_id
                WHERE a.assessment_id = ?
                """,
                (result["assessment_id"],),
            ).fetchone()
        self.assertEqual(assessment["email"], "integration@example.test")
        self.assertTrue(assessment["consented_at"])
        self.assertEqual(assessment["status"], "succeeded")
        self.assertIsNotNone(assessment["report_json"])

        metrics = self.client.get("/api/metrics").json()
        self.assertEqual(metrics["metrics"]["submissions"], 1)
        self.assertEqual(metrics["metrics"]["reports"], 1)
        self.assertEqual(metrics["metrics"]["leads"], 1)
        self.assertEqual(metrics["automation"]["statuses"], {"succeeded": 1})

    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_conversion_rates_use_documented_funnel_denominators(
        self, _generator: MagicMock
    ) -> None:
        visitor_event = {
            "visitor_id": str(uuid4()),
            "path": "/assessment",
            "source": "paid",
        }
        self.client.post("/api/visits", json=visitor_event)
        self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "visitor_id": visitor_event["visitor_id"],
                "education_stage": "highschool",
                "lead": {"email": "student@example.com", "consent": True},
            },
        )

        metrics = self.client.get("/api/metrics").json()["metrics"]

        self.assertEqual(metrics["visitors"], 1)
        self.assertEqual(metrics["starts"], 1)
        self.assertEqual(metrics["submissions"], 1)
        self.assertEqual(metrics["completions"], 1)
        self.assertEqual(metrics["reports"], 1)
        self.assertEqual(metrics["leads"], 1)
        self.assertEqual(metrics["qualified"], 1)
        self.assertEqual(
            metrics["conversion_rates"],
            {
                "visitors_to_leads": 1.0,
                "starts_to_completions": 1.0,
                "completions_to_leads": 1.0,
            },
        )
        self.assertEqual(
            metrics["conversion_rate_counts"],
            {
                "visitors_to_leads": {"numerator": 1, "denominator": 1},
                "starts_to_completions": {"numerator": 1, "denominator": 1},
                "completions_to_leads": {"numerator": 1, "denominator": 1},
            },
        )

    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_non_highschool_consent_lead_is_not_qualified_demo_proxy(
        self, _generator: MagicMock
    ) -> None:
        visitor_id = str(uuid4())
        self.client.post(
            "/api/visits",
            json={
                "visitor_id": visitor_id,
                "path": "/assessment",
                "source": "direct",
            },
        )
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "visitor_id": visitor_id,
                "education_stage": "undergrad",
                "lead": {"email": "student@example.com", "consent": True},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/metrics").json()["metrics"]["qualified"], 0)

    def test_legacy_assessments_without_reports_are_not_counted_as_completions(
        self,
    ) -> None:
        with closing(main.connect_database()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO assessments
                        (assessment_id, interests, coding_experience, education_stage,
                         created_at, report_json, report_generation_mode, report_status)
                    VALUES (?, 'web', 'beginner', 'highschool', ?, NULL, NULL, 'generated')
                    """,
                    (str(uuid4()), main.utc_now()),
                )

        metrics = self.client.get("/api/metrics").json()["metrics"]

        self.assertEqual(metrics["submissions"], 1)
        self.assertEqual(metrics["completions"], 0)
        self.assertEqual(metrics["reports"], 0)

    @patch.dict(
        os.environ,
        {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/test",
            "N8N_WEBHOOK_SECRET": "server-only-test-secret",
        },
    )
    @patch("app.main.httpx.Client")
    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_n8n_failure_does_not_rollback_consented_lead(
        self,
        _generator: MagicMock,
        client_factory: MagicMock,
    ) -> None:
        client_factory.return_value.__enter__.return_value.post.side_effect = (
            httpx.ConnectError("offline")
        )
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {"email": "student@example.com", "consent": True},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["automation"]["status"], "failed")
        self.assertEqual(client_factory.return_value.__enter__.return_value.post.call_count, 2)
        request_kwargs = (
            client_factory.return_value.__enter__.return_value.post.call_args.kwargs
        )
        self.assertNotIn("student@example.com", json.dumps(request_kwargs["json"]))
        with closing(main.connect_database()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0], 1)
            event = connection.execute(
                "SELECT status, attempts FROM lead_automation_events"
            ).fetchone()
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["attempts"], 2)

    @patch.dict(
        os.environ,
        {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/test",
            "N8N_WEBHOOK_SECRET": "server-only-test-secret",
        },
    )
    @patch("app.main.httpx.Client")
    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_n8n_mismatched_acknowledgement_is_not_reported_as_success(
        self,
        _generator: MagicMock,
        client_factory: MagicMock,
    ) -> None:
        http_client = client_factory.return_value.__enter__.return_value
        http_client.post.return_value.json.return_value = {
            "accepted": True,
            "event_id": "00000000-0000-4000-8000-000000000000",
        }
        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {"email": "test-student@example.test", "consent": True},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["automation"]["status"], "failed")
        self.assertEqual(http_client.post.call_count, 2)
        with closing(main.connect_database()) as connection:
            event = connection.execute(
                "SELECT status, attempts FROM lead_automation_events"
            ).fetchone()
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["attempts"], 2)

    @patch.dict(
        os.environ,
        {
            "N8N_WEBHOOK_URL": "https://n8n.example.test/webhook/inactive",
            "N8N_WEBHOOK_SECRET": "server-only-test-secret",
        },
    )
    @patch("app.main.httpx.Client")
    @patch("app.main.generate_report", side_effect=rule_based_report)
    def test_inactive_n8n_webhook_404_does_not_claim_delivery_success(
        self,
        _generator: MagicMock,
        client_factory: MagicMock,
    ) -> None:
        request = httpx.Request("POST", "https://n8n.example.test/webhook/inactive")
        response_404 = httpx.Response(404, request=request)
        client_factory.return_value.__enter__.return_value.post.return_value = (
            response_404
        )

        response = self.client.post(
            "/api/assessments",
            json={
                **self.payload,
                "lead": {"email": "test-student@example.test", "consent": True},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["automation"]["status"], "failed")
        self.assertEqual(
            client_factory.return_value.__enter__.return_value.post.call_count,
            2,
        )
        with closing(main.connect_database()) as connection:
            event = connection.execute(
                "SELECT status, attempts FROM lead_automation_events"
            ).fetchone()
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["attempts"], 2)

    def test_empty_metrics_are_zero_and_not_fabricated(self) -> None:
        response = self.client.get("/api/metrics")
        metrics = response.json()

        self.assertTrue(metrics["empty"])
        self.assertEqual(metrics["metrics"]["visitors"], 0)
        self.assertIsNone(metrics["metrics"]["conversion_rates"]["visitors_to_leads"])
        self.assertEqual(
            metrics["metrics"]["conversion_rate_counts"],
            {
                "visitors_to_leads": {"numerator": 0, "denominator": 0},
                "starts_to_completions": {"numerator": 0, "denominator": 0},
                "completions_to_leads": {"numerator": 0, "denominator": 0},
            },
        )
        self.assertEqual(metrics["metrics"]["qualified"], 0)
        self.assertEqual(len(metrics["sources"]), 5)


if __name__ == "__main__":
    unittest.main()
