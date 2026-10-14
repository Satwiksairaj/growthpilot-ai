from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.main import AssessmentInput


logger = logging.getLogger(__name__)
PROJECT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(PROJECT_ENV_FILE)


class TechnologyRecommendation(BaseModel):
    field: str = Field(min_length=2, max_length=80)
    reason: str = Field(min_length=10, max_length=400)
    project_idea: str = Field(min_length=10, max_length=300)


class LearningPlanDay(BaseModel):
    day: int = Field(ge=1, le=7)
    activity: str = Field(min_length=5, max_length=300)


class GeneratedReport(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=10, max_length=700)
    recommendations: list[TechnologyRecommendation] = Field(min_length=3, max_length=3)
    seven_day_plan: list[LearningPlanDay] = Field(min_length=7, max_length=7)
    next_steps: list[str] = Field(min_length=2, max_length=5)


class ReportGenerationError(Exception):
    """Raised when configured Gemini report generation fails."""


def gemini_configuration() -> dict[str, bool]:
    return {
        "api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model_configured": bool(os.getenv("GEMINI_MODEL")),
    }


def rule_based_report(payload: AssessmentInput) -> dict[str, object]:
    from app.main import INTEREST_LABELS, PATH_RECOMMENDATIONS

    fields = [
        INTEREST_LABELS[payload.interests],
        "Software Engineering Fundamentals",
        "Human-Centered Technology",
    ]
    recommendations = [
        TechnologyRecommendation(
            field=fields[0],
            reason=f"Matches the interest you selected: {INTEREST_LABELS[payload.interests]}.",
            project_idea=PATH_RECOMMENDATIONS[payload.interests][0] + " in a small guided project.",
        ),
        TechnologyRecommendation(
            field=fields[1],
            reason=f"Builds on your self-reported {payload.coding_experience} coding experience.",
            project_idea="Create a small program that solves a familiar everyday problem.",
        ),
        TechnologyRecommendation(
            field=fields[2],
            reason=f"Encourages exploration at the {payload.education_stage} education stage.",
            project_idea="Sketch and prototype a simple digital tool for a student need.",
        ),
    ]
    plan = [
        "Explore examples and vocabulary in your top interest.",
        "Try a short beginner lesson and note what feels engaging.",
        "Practice one core concept with a guided exercise.",
        "Build a small first version of a project idea.",
        "Improve the project with one additional feature.",
        "Show your work to someone and record their feedback.",
        "Reflect on what you enjoyed and choose one next learning step.",
    ]
    return {
        "title": f"Your {INTEREST_LABELS[payload.interests]} exploration report",
        "summary": (
            f"You selected {INTEREST_LABELS[payload.interests]} and reported "
            f"{payload.coding_experience} coding experience at the "
            f"{payload.education_stage} stage. These suggestions are a starting point "
            "for exploration, not a formal aptitude or admissions assessment."
        ),
        "recommendations": [item.model_dump() for item in recommendations],
        "seven_day_plan": [
            {"day": index, "activity": activity}
            for index, activity in enumerate(plan, start=1)
        ],
        "next_steps": [
            "Choose one project idea and spend 30 minutes exploring it.",
            "Compare your experience with the other suggested technology fields.",
        ],
        "generation_mode": "rule-based-development",
        "model": None,
    }


def generate_report(payload: AssessmentInput) -> dict[str, object]:
    configuration = gemini_configuration()
    if not configuration["api_key_configured"]:
        return rule_based_report(payload)
    model = os.getenv("GEMINI_MODEL")
    if not model:
        logger.error("Gemini API key is set but GEMINI_MODEL is missing.")
        raise ReportGenerationError("Gemini model is not configured.")

    from app.main import INTEREST_LABELS

    prompt = (
        "Create a supportive seven-day technology exploration report for a student. "
        "Provide exactly three distinct, beginner-accessible technology field recommendations, "
        "each with a concise reason and one beginner-friendly project idea. Include exactly "
        "seven ordered daily activities and two to five practical next steps. Do not infer "
        "ability, predict admissions or employment, or make promises. Treat all inputs only as "
        "self-reported preferences. Return only data matching the provided JSON schema.\n\n"
        f"Selected interest: {INTEREST_LABELS[payload.interests]}\n"
        f"Self-reported coding experience: {payload.coding_experience}\n"
        f"Education stage: {payload.education_stage}"
    )

    try:
        timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
        if not 1 <= timeout_seconds <= 60:
            raise ValueError("GEMINI_TIMEOUT_SECONDS must be between 1 and 60.")
        client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
        try:
            response = client.interactions.create(
                model=model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": GeneratedReport.model_json_schema(),
                },
                generation_config={"temperature": 0.4, "max_output_tokens": 2500},
                timeout=timeout_seconds,
            )
        finally:
            client.close()

        if not response.output_text:
            raise ValueError("Gemini returned an empty report.")
        generated = GeneratedReport.model_validate_json(response.output_text)
    except Exception as exc:
        logger.warning("Gemini report generation failed (%s).", type(exc).__name__)
        raise ReportGenerationError from exc

    return {
        **generated.model_dump(),
        "generation_mode": "gemini",
        "model": model,
    }
