"""Report Generator — builds a recruiter-ready report from a completed session.

Produces radar/heatmap/timeline chart data, strengths/weaknesses/suggestions,
curated learning resources, and a recruiter summary. AI enriches the narrative
parts; heuristics provide full fallback so reports always generate.
"""

import json
import re
from typing import Optional

from ai.feedback_engine.metrics import FeedbackMetrics
from ai.interview_engine.session_service import InterviewSessionService
from ai.interview_engine.state import InterviewState
from ai.report_generator import data_builder
from database.connection import execute, fetch_one, query
from services.llm import LLMError, router

REPORT_PROMPT = """
You are a senior recruiter writing an interview report. Based on the candidate's
metrics and recommendation, produce a concise recruiter-facing summary.

METRICS (JSON):
{metrics}

RECOMMENDATION: {recommendation}

Return ONLY JSON:
{{
  "recruiter_summary": "2-3 sentence summary for a recruiter",
  "suggestions": ["3 concrete next steps for the candidate"],
  "learning_resources": [{{"topic": "area to improve", "resource": "URL or course name"}}]
}}
"""


class ReportGenerator:
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.session_service = InterviewSessionService()

    def generate_report(self, state: InterviewState) -> dict:
        """Builds all report sections, optionally AI-enriches, persists to reports."""
        if not state.answers:
            raise ValueError("Cannot generate report: no answers in session")

        metrics = FeedbackMetrics.compute(state)
        recommendation = self._recommend(metrics)

        strengths = data_builder.build_strengths(metrics)
        weaknesses = data_builder.build_weaknesses(metrics)

        ai = {}
        if self.use_ai:
            ai = self._ai_report(metrics, recommendation)
            if ai.get("recruiter_summary"):
                strengths = ai.get("strengths") or strengths
                weaknesses = ai.get("weaknesses") or weaknesses

        recruiter_summary = ai.get("recruiter_summary") or data_builder.build_recruiter_summary(
            metrics, recommendation, strengths
        )
        suggestions = ai.get("suggestions") or data_builder.build_suggestions(metrics, weaknesses)
        learning_resources = ai.get("learning_resources") or data_builder.build_learning_resources(
            weaknesses, metrics
        )

        radar_data = data_builder.build_radar_data(state, metrics)
        heatmap_data = data_builder.build_heatmap_data(state, metrics)
        timeline_data = data_builder.build_timeline_data(state, metrics)

        full_report = {
            "session_id": state.session_id,
            "metrics": metrics,
            "recommendation": recommendation,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "learning_resources": learning_resources,
            "recruiter_summary": recruiter_summary,
            "radar_data": radar_data,
            "heatmap_data": heatmap_data,
            "timeline_data": timeline_data,
        }

        report_id = self._persist(state.session_id, full_report)
        full_report["report_id"] = report_id
        return full_report

    # --- Persistence ---

    def _persist(self, session_id: int, report: dict) -> int:
        report_id = execute(
            """
            INSERT INTO reports
                (session_id, radar_data, heatmap_data, timeline_data,
                 strengths, weaknesses, suggestions, learning_resources,
                 recruiter_summary, full_report)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                session_id,
                json.dumps(report["radar_data"]),
                json.dumps(report["heatmap_data"]),
                json.dumps(report["timeline_data"]),
                json.dumps(report["strengths"]),
                json.dumps(report["weaknesses"]),
                json.dumps(report["suggestions"]),
                json.dumps(report["learning_resources"]),
                report["recruiter_summary"],
                json.dumps(report),
            ),
        )
        return report_id

    # --- AI ---

    def _ai_report(self, metrics: dict, recommendation: str) -> dict:
        prompt = REPORT_PROMPT.format(
            metrics=json.dumps(metrics), recommendation=recommendation
        )
        try:
            response = router.generate(
                "report_generation", prompt, max_tokens=700, temperature=0.3
            )
            data = self._parse_json(response.text)
            return data if isinstance(data, dict) else {}
        except LLMError:
            return {}

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {}

    # --- Helpers ---

    @staticmethod
    def _recommend(metrics: dict) -> str:
        overall = metrics.get("overall_score", 0)
        if overall >= 75:
            return "hire"
        if overall >= 55:
            return "maybe"
        return "reject"

    # --- Reads ---

    def get_report(self, session_id: int) -> Optional[dict]:
        row = fetch_one(
            "SELECT id, session_id, radar_data, heatmap_data, timeline_data, strengths, "
            "weaknesses, suggestions, learning_resources, recruiter_summary, created_at "
            "FROM reports WHERE session_id = %s",
            (session_id,),
        )
        if not row:
            return None
        for key in (
            "radar_data",
            "heatmap_data",
            "timeline_data",
            "strengths",
            "weaknesses",
            "suggestions",
            "learning_resources",
        ):
            if row.get(key) is not None:
                row[key] = json.loads(row[key])
        return row

    def list_for_user(self, user_id: int) -> list[dict]:
        return query(
            """
            SELECT r.id, r.session_id, r.recruiter_summary, r.created_at
            FROM reports r
            JOIN interview_sessions s ON s.id = r.session_id
            WHERE s.user_id = %s ORDER BY r.created_at DESC
            """,
            (user_id,),
        )
