from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from app.ai_reports import (
    ReportGenerationError,
    generate_report,
    gemini_configuration,
)


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "growthpilot.db"
DATABASE_PATH = Path(os.getenv("GROWTHPILOT_DB_PATH", str(DEFAULT_DATABASE_PATH)))
logger = logging.getLogger(__name__)

Interest = Literal["web", "data", "mobile", "cloud", "uiux"]
Experience = Literal["none", "beginner", "intermediate", "advanced"]
EducationStage = Literal["highschool", "undergrad", "postgrad", "professional"]
PagePath = Literal["/", "/assessment", "/dashboard"]
AcquisitionSource = Literal["direct", "organic", "paid", "referral", "social"]


class LeadInput(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    consent: bool

    @field_validator("name", "email")
    @classmethod
    def trim_optional_contact(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value.lower() if value else None

    @model_validator(mode="after")
    def require_consented_contact(self) -> "LeadInput":
        if not self.consent:
            raise ValueError("Consent is required to capture lead information.")
        if not self.name and not self.email:
            raise ValueError("Provide a name or email address for lead capture.")
        return self


class AssessmentInput(BaseModel):
    visitor_id: UUID | None = None
    interests: Interest
    coding_experience: Experience
    education_stage: EducationStage
    lead: LeadInput | None = None


class VisitInput(BaseModel):
    visitor_id: UUID
    path: PagePath
    source: AcquisitionSource = "direct"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with closing(connect_database()) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS page_views (
                visitor_id TEXT NOT NULL REFERENCES visitors(visitor_id),
                path TEXT NOT NULL,
                visited_at TEXT NOT NULL,
                PRIMARY KEY (visitor_id, path)
            );
            CREATE TABLE IF NOT EXISTS assessments (
                assessment_id TEXT PRIMARY KEY,
                visitor_id TEXT REFERENCES visitors(visitor_id),
                interests TEXT NOT NULL,
                coding_experience TEXT NOT NULL,
                education_stage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                report_json TEXT,
                report_generation_mode TEXT,
                report_status TEXT NOT NULL DEFAULT 'generated',
                idempotency_key TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS leads (
                lead_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL UNIQUE REFERENCES assessments(assessment_id),
                name TEXT,
                email TEXT,
                consented_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lead_automation_events (
                event_id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL UNIQUE REFERENCES leads(lead_id),
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        assessment_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(assessments)").fetchall()
        }
        migrations = {
            "visitor_id": (
                "ALTER TABLE assessments ADD COLUMN visitor_id TEXT "
                "REFERENCES visitors(visitor_id)"
            ),
            "report_json": "ALTER TABLE assessments ADD COLUMN report_json TEXT",
            "report_generation_mode": (
                "ALTER TABLE assessments ADD COLUMN report_generation_mode TEXT"
            ),
            "report_status": (
                "ALTER TABLE assessments ADD COLUMN report_status TEXT NOT NULL "
                "DEFAULT 'generated'"
            ),
            "idempotency_key": (
                "ALTER TABLE assessments ADD COLUMN idempotency_key TEXT"
            ),
        }
        for column, statement in migrations.items():
            if column not in assessment_columns:
                connection.execute(statement)
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_assessments_idempotency_key
            ON assessments(idempotency_key) WHERE idempotency_key IS NOT NULL
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO app_metadata (key, value)
            VALUES ('linked_analytics_since', ?)
            """,
            (utc_now(),),
        )
        connection.commit()


INTEREST_LABELS = {
    "web": "Web Development",
    "data": "Data Science",
    "mobile": "Mobile App Development",
    "cloud": "Cloud & DevOps",
    "uiux": "UI/UX Design",
}

PATH_RECOMMENDATIONS = {
    "web": [
        "Learn HTML, CSS, and JavaScript fundamentals",
        "Build responsive interfaces with React",
        "Create and publish a small portfolio project",
    ],
    "data": [
        "Learn Python fundamentals and data handling",
        "Practice SQL and exploratory data analysis",
        "Build a project that explains insights with visualizations",
    ],
    "mobile": [
        "Learn programming fundamentals and mobile UI patterns",
        "Explore React Native or native Android/iOS development",
        "Build and test a small app on a device or simulator",
    ],
    "cloud": [
        "Learn Linux, networking, and command-line fundamentals",
        "Practice Git and automate a simple deployment",
        "Explore cloud infrastructure and container basics",
    ],
    "uiux": [
        "Learn user research and interaction design fundamentals",
        "Practice wireframing and prototyping",
        "Build a portfolio case study around a real user problem",
    ],
}


def make_report(payload: AssessmentInput) -> dict[str, object]:
    from app.ai_reports import rule_based_report

    return rule_based_report(payload)


app = FastAPI(
    title="GrowthPilot AI API",
    description="Development API for student assessments and growth analytics.",
    version="0.1.0",
)

allowed_origins = [
    (
        origin.strip().rstrip("/")
        if origin.strip().startswith(("http://", "https://"))
        else f"https://{origin.strip().rstrip('/')}"
    )
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


def n8n_webhook_url() -> str | None:
    configured_url = os.getenv("N8N_WEBHOOK_URL")
    if configured_url:
        return configured_url

    base_url = os.getenv("N8N_BASE_URL")
    if not base_url:
        return None
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return f"{base_url.rstrip('/')}/webhook/growthpilot/consented-lead"


@app.get("/api/health")
def health() -> dict[str, object]:
    gemini = gemini_configuration()
    return {
        "status": "ok",
        "configuration": {
            "gemini_configured": (
                gemini["api_key_configured"] and gemini["model_configured"]
            ),
            "gemini_model_configured": gemini["model_configured"],
            "n8n_configured": bool(
                n8n_webhook_url() and os.getenv("N8N_WEBHOOK_SECRET")
            ),
            "database": "sqlite",
        },
    }


@app.post("/api/visits", status_code=204)
def record_visit(payload: VisitInput) -> None:
    timestamp = utc_now()
    visitor_id = str(payload.visitor_id)
    with closing(connect_database()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO visitors (visitor_id, source, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(visitor_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (visitor_id, payload.source, timestamp, timestamp),
            )
            connection.execute(
                """
                INSERT INTO page_views (visitor_id, path, visited_at)
                VALUES (?, ?, ?)
                ON CONFLICT(visitor_id, path) DO UPDATE SET visited_at = excluded.visited_at
                """,
                (visitor_id, payload.path, timestamp),
            )


def load_idempotent_response(
    connection: sqlite3.Connection,
    idempotency_key: str,
    payload: AssessmentInput,
) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT a.*, l.name AS lead_name, l.email AS lead_email,
               l.consented_at AS lead_consent, e.event_id, e.status AS automation_status
        FROM assessments a
        LEFT JOIN leads l ON l.assessment_id = a.assessment_id
        LEFT JOIN lead_automation_events e ON e.lead_id = l.lead_id
        WHERE a.idempotency_key = ?
        """,
        (idempotency_key,),
    ).fetchone()
    if row is None:
        return None

    same_lead = (
        payload.lead is None and row["lead_consent"] is None
    ) or (
        payload.lead is not None
        and row["lead_consent"] is not None
        and row["lead_name"] == payload.lead.name
        and row["lead_email"] == payload.lead.email
    )
    if (
        row["interests"] != payload.interests
        or row["coding_experience"] != payload.coding_experience
        or row["education_stage"] != payload.education_stage
        or row["visitor_id"]
        != (str(payload.visitor_id) if payload.visitor_id is not None else None)
        or not same_lead
    ):
        raise HTTPException(
            status_code=409,
            detail="This idempotency key was already used for different assessment data.",
        )
    if not row["report_json"]:
        raise HTTPException(
            status_code=409,
            detail="The earlier assessment has no saved report; submit a new request.",
        )
    result: dict[str, object] = {
        "assessment_id": row["assessment_id"],
        "report": json.loads(row["report_json"]),
        "mode": row["report_generation_mode"],
        "idempotent_replay": True,
    }
    if payload.lead is not None:
        result["automation"] = {
            "event_id": row["event_id"],
            "status": row["automation_status"] or "not_configured",
        }
    return result


def dispatch_n8n_event(event_id: str) -> None:
    webhook_url = n8n_webhook_url()
    webhook_secret = os.getenv("N8N_WEBHOOK_SECRET")
    if not webhook_url or not webhook_secret:
        return

    with closing(connect_database()) as connection:
        event = connection.execute(
            """
            SELECT e.event_id, e.lead_id, l.assessment_id, l.consented_at
            FROM lead_automation_events e
            JOIN leads l ON l.lead_id = e.lead_id
            WHERE e.event_id = ? AND e.status IN ('pending', 'failed')
            """,
            (event_id,),
        ).fetchone()
    if event is None:
        return

    event_payload = {
        "event_id": event["event_id"],
        "event_type": "consented_lead.created",
        "lead_id": event["lead_id"],
        "assessment_id": event["assessment_id"],
        "consent": True,
        "created_at": event["consented_at"],
    }
    attempts = 0
    success = False
    last_error = "Webhook response did not confirm this event."
    for attempt in range(1, 3):
        attempts = attempt
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    webhook_url,
                    json=event_payload,
                    headers={"Authorization": webhook_secret},
                )
            response.raise_for_status()
            confirmation = response.json()
            if (
                confirmation.get("accepted") is True
                and confirmation.get("event_id") == event_id
            ):
                success = True
                last_error = ""
                break
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            last_error = f"Webhook delivery failed ({type(exc).__name__})."
            logger.warning("n8n webhook delivery failed (%s).", type(exc).__name__)

    with closing(connect_database()) as connection:
        with connection:
            connection.execute(
                """
                UPDATE lead_automation_events
                SET status = ?, attempts = attempts + ?, last_error = ?, updated_at = ?
                WHERE event_id = ?
                """,
                (
                    "succeeded" if success else "failed",
                    attempts,
                    last_error or None,
                    utc_now(),
                    event_id,
                ),
            )


@app.post("/api/assessments")
def create_assessment(
    payload: AssessmentInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    if idempotency_key and not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", idempotency_key):
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key header.")
    if idempotency_key:
        with closing(connect_database()) as connection:
            existing = load_idempotent_response(connection, idempotency_key, payload)
        if existing is not None:
            return existing

    try:
        report = generate_report(payload)
    except ReportGenerationError as exc:
        raise HTTPException(
            status_code=503,
            detail="The report service is unavailable. Please try again later.",
        ) from exc

    assessment_id = str(uuid4())
    timestamp = utc_now()
    event_id: str | None = None

    try:
        with closing(connect_database()) as connection:
            with connection:
                if payload.visitor_id is not None:
                    visitor_id = str(payload.visitor_id)
                    connection.execute(
                        """
                        INSERT INTO visitors
                            (visitor_id, source, first_seen_at, last_seen_at)
                        VALUES (?, 'direct', ?, ?)
                        ON CONFLICT(visitor_id) DO UPDATE
                        SET last_seen_at = excluded.last_seen_at
                        """,
                        (visitor_id, timestamp, timestamp),
                    )
                    connection.execute(
                        """
                        INSERT INTO page_views (visitor_id, path, visited_at)
                        VALUES (?, '/assessment', ?)
                        ON CONFLICT(visitor_id, path) DO UPDATE
                        SET visited_at = excluded.visited_at
                        """,
                        (visitor_id, timestamp),
                    )
                connection.execute(
                    """
                    INSERT INTO assessments
                        (assessment_id, visitor_id, interests, coding_experience,
                         education_stage, created_at, report_json,
                         report_generation_mode, report_status, idempotency_key)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'generated', ?)
                    """,
                    (
                        assessment_id,
                        str(payload.visitor_id) if payload.visitor_id else None,
                        payload.interests,
                        payload.coding_experience,
                        payload.education_stage,
                        timestamp,
                        json.dumps(report, separators=(",", ":"), sort_keys=True),
                        report["generation_mode"],
                        idempotency_key,
                    ),
                )
                if payload.lead:
                    lead_id = str(uuid4())
                    event_id = str(uuid4())
                    connection.execute(
                        """
                        INSERT INTO leads
                            (lead_id, assessment_id, name, email, consented_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            lead_id,
                            assessment_id,
                            payload.lead.name,
                            payload.lead.email,
                            timestamp,
                        ),
                    )
                    n8n_configured = bool(
                        n8n_webhook_url() and os.getenv("N8N_WEBHOOK_SECRET")
                    )
                    connection.execute(
                        """
                        INSERT INTO lead_automation_events
                            (event_id, lead_id, status, attempts, created_at, updated_at)
                        VALUES (?, ?, ?, 0, ?, ?)
                        """,
                        (
                            event_id,
                            lead_id,
                            "pending" if n8n_configured else "not_configured",
                            timestamp,
                            timestamp,
                        ),
                    )
    except sqlite3.IntegrityError as exc:
        if idempotency_key:
            with closing(connect_database()) as connection:
                existing = load_idempotent_response(connection, idempotency_key, payload)
            if existing is not None:
                return existing
        logger.warning("Assessment persistence rejected by a database constraint.")
        raise HTTPException(status_code=409, detail="Assessment could not be saved.") from exc
    except sqlite3.Error as exc:
        logger.exception("Assessment persistence failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not save assessment.") from exc

    result: dict[str, object] = {
        "assessment_id": assessment_id,
        "report": report,
        "mode": report["generation_mode"],
        "idempotent_replay": False,
    }
    if event_id:
        dispatch_n8n_event(event_id)
        with closing(connect_database()) as connection:
            event = connection.execute(
                "SELECT status FROM lead_automation_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        result["automation"] = {
            "event_id": event_id,
            "status": event["status"] if event else "unknown",
        }
    return result


def get_metrics() -> dict[str, object]:
    with closing(connect_database()) as connection:
        tracking_since = connection.execute(
            "SELECT value FROM app_metadata WHERE key = 'linked_analytics_since'"
        ).fetchone()["value"]
        visitors = connection.execute(
            "SELECT COUNT(*) AS count FROM visitors"
        ).fetchone()["count"]
        starts = connection.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) AS count
            FROM page_views WHERE path = '/assessment'
            """
        ).fetchone()["count"]
        submissions = connection.execute(
            "SELECT COUNT(*) AS count FROM assessments"
        ).fetchone()["count"]
        completions = connection.execute(
            """
            SELECT COUNT(*) AS count FROM assessments
            WHERE report_status = 'generated' AND report_json IS NOT NULL
            """
        ).fetchone()["count"]
        reports = completions
        leads = connection.execute(
            "SELECT COUNT(*) AS count FROM leads"
        ).fetchone()["count"]
        proxy_qualified_leads = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM leads l
            JOIN assessments a ON a.assessment_id = l.assessment_id
            WHERE a.education_stage = 'highschool'
              AND a.report_status = 'generated'
              AND a.report_json IS NOT NULL
              AND (
                  (l.name IS NOT NULL AND TRIM(l.name) != '')
                  OR (l.email IS NOT NULL AND TRIM(l.email) != '')
              )
            """
        ).fetchone()["count"]
        linked_visitors = connection.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) AS count
            FROM page_views
            WHERE visited_at >= ?
            """,
            (tracking_since,),
        ).fetchone()["count"]
        linked_starts = connection.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) AS count
            FROM page_views
            WHERE path = '/assessment' AND visited_at >= ?
            """,
            (tracking_since,),
        ).fetchone()["count"]
        linked_lead_visitors = connection.execute(
            """
            SELECT COUNT(DISTINCT a.visitor_id) AS count
            FROM leads l
            JOIN assessments a ON a.assessment_id = l.assessment_id
            WHERE a.visitor_id IS NOT NULL
              AND a.created_at >= ?
            """,
            (tracking_since,),
        ).fetchone()["count"]
        linked_completed_visitors = connection.execute(
            """
            SELECT COUNT(DISTINCT a.visitor_id) AS count
            FROM assessments a
            WHERE a.visitor_id IS NOT NULL
              AND a.created_at >= ?
              AND a.report_status = 'generated'
              AND a.report_json IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM page_views p
                  WHERE p.visitor_id = a.visitor_id
                    AND p.path = '/assessment'
                    AND p.visited_at >= ?
              )
            """,
            (tracking_since, tracking_since),
        ).fetchone()["count"]
        linked_leads_with_reports = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM leads l
            JOIN assessments a ON a.assessment_id = l.assessment_id
            WHERE a.report_status = 'generated'
              AND a.report_json IS NOT NULL
              AND a.created_at >= ?
            """,
            (tracking_since,),
        ).fetchone()["count"]
        linked_reports = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM assessments
            WHERE report_status = 'generated'
              AND report_json IS NOT NULL
              AND created_at >= ?
            """,
            (tracking_since,),
        ).fetchone()["count"]
        source_rows = connection.execute(
            """
            SELECT source AS name, COUNT(*) AS value
            FROM visitors GROUP BY source
            ORDER BY name
            """
        ).fetchall()
        automation_rows = connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM lead_automation_events GROUP BY status
            """
        ).fetchall()

    source_breakdown = [dict(row) for row in source_rows]
    for source in ("direct", "organic", "paid", "referral", "social"):
        if not any(row["name"] == source for row in source_breakdown):
            source_breakdown.append({"name": source, "value": 0})
    source_breakdown.sort(key=lambda row: row["name"])
    automation_counts = {row["status"]: row["count"] for row in automation_rows}
    return {
        "mode": "live",
        "note": (
            "Live local development measurements from SQLite; not production analytics. "
            f"Linked conversion rates include tracked activity since {tracking_since[:10]}."
        ),
        "tracking_since": tracking_since[:10],
        "metrics": {
            "visitors": visitors,
            "starts": starts,
            "submissions": submissions,
            "completions": completions,
            "reports": reports,
            "leads": leads,
            "qualified": proxy_qualified_leads,
            "counselling_requests": None,
            "conversion_rates": {
                "visitors_to_leads": (
                    round(linked_lead_visitors / linked_visitors, 4)
                    if linked_visitors
                    else None
                ),
                "starts_to_completions": (
                    round(linked_completed_visitors / linked_starts, 4)
                    if linked_starts
                    else None
                ),
                "completions_to_leads": (
                    round(linked_leads_with_reports / linked_reports, 4)
                    if linked_reports
                    else None
                ),
            },
            "conversion_rate_counts": {
                "visitors_to_leads": {
                    "numerator": linked_lead_visitors,
                    "denominator": linked_visitors,
                },
                "starts_to_completions": {
                    "numerator": linked_completed_visitors,
                    "denominator": linked_starts,
                },
                "completions_to_leads": {
                    "numerator": linked_leads_with_reports,
                    "denominator": linked_reports,
                },
            },
        },
        "sources": source_breakdown,
        "automation": {
            "configured": bool(
                os.getenv("N8N_WEBHOOK_URL") and os.getenv("N8N_WEBHOOK_SECRET")
            ),
            "statuses": automation_counts,
        },
        "funnel": [
            {"stage": "Visitors", "value": visitors},
            {"stage": "Assessment starts", "value": starts},
            {"stage": "Assessment submissions", "value": submissions},
            {"stage": "Reports generated", "value": reports},
            {"stage": "Consented leads", "value": leads},
        ],
        "empty": (
            visitors == 0
            and starts == 0
            and submissions == 0
            and completions == 0
            and leads == 0
        ),
        "definitions": {
            "visitors": "Distinct pseudonymous browser visitor IDs in SQLite.",
            "starts": "Distinct visitors recorded on the assessment route.",
            "submissions": "All assessment records saved, including legacy records without a report.",
            "completions": "Assessments with a successfully generated and persisted report.",
            "reports": "Saved assessments with a successfully persisted report.",
            "leads": "Lead records saved with explicit consent.",
            "qualified": (
                "Demo proxy only: high-school education stage, consented contact, "
                "and a successfully persisted report. Not NIAT's official qualification rule."
            ),
            "conversion_rates": (
                "Rates use visitor-linked records created since linked analytics tracking "
                "was enabled. Older unlinked activity is excluded from these rates."
            ),
            "sources": "Approximate attribution from referrer or UTM data.",
        },
    }


@app.get("/api/metrics")
def metrics_endpoint() -> dict[str, object]:
    return get_metrics()


@app.get("/api/automation/status")
def automation_status() -> dict[str, object]:
    return get_metrics()["automation"]  # Only aggregate status is exposed.
