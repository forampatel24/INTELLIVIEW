import json
from typing import Optional

from ai.feedback_engine.metrics import FeedbackMetrics
from ai.interview_engine.session_service import InterviewSessionService
from ai.interview_engine.state import InterviewState, SessionStatus
from database.connection import execute, fetch_one, query
from services.llm import LLMError, router

FEEDBACK_PROMPT = """
You are an interview coach. Based on the candidate's interview metrics, produce a concise feedback summary.

METRICS (JSON):
{metrics}

Return ONLY JSON:
{{
  "summary": "2-4 sentence feedback summary for the candidate",
  "strengths": ["3 strengths"],
  "weaknesses": ["3 areas to improve"],
  "recommendation": "hire" | "maybe" | "reject",
  "suggestions": ["concrete next steps"]
}}
"""


class FeedbackEngine:
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.session_service = InterviewSessionService()

    def generate_feedback(self, state: InterviewState) -> dict:
        """Computes metrics, optionally enriches with AI, persists to feedback table."""
        if not state.answers:
            raise ValueError("Cannot generate feedback: no answers in session")

        metrics = FeedbackMetrics.compute(state)
        overall = metrics["overall_score"]
        recommendation = self._recommend(overall, metrics)

        ai_summary = {}
        if self.use_ai:
            ai_summary = self._ai_feedback(metrics)
            if ai_summary.get("recommendation"):
                recommendation = ai_summary["recommendation"]

        summary = ai_summary.get("summary") or (
            f"Overall score {overall:.0f}/100 across {metrics['total_questions']} questions. "
            f"Strong areas: {', '.join(list(metrics['skills'])[:3]) or 'none'}. "
            f"Focus on {', '.join(ai_summary.get('weaknesses', [])[:2]) or 'consistent practice'}."
        )
        strengths = ai_summary.get("strengths") or FeedbackEngine._default_strengths(metrics)
        weaknesses = ai_summary.get("weaknesses") or FeedbackEngine._default_weaknesses(metrics)
        suggestions = ai_summary.get("suggestions") or []

        feedback_id = execute(
            """
            INSERT INTO feedback (session_id, metrics, overall_score, recommendation, summary)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                state.session_id,
                json.dumps(metrics),
                round(overall, 2),
                recommendation,
                summary,
            ),
        )
        return {
            "feedback_id": feedback_id,
            "metrics": metrics,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendation": recommendation,
            "suggestions": suggestions,
        }

    # --- AI ---

    def _ai_feedback(self, metrics: dict) -> dict:
        prompt = FEEDBACK_PROMPT.format(metrics=json.dumps(metrics))
        try:
            response = router.generate("feedback_generation", prompt, max_tokens=600, temperature=0.3)
            data = self._parse_json(response.text)
            return data if isinstance(data, dict) else {}
        except LLMError:
            return {}

    @staticmethod
    def _parse_json(text: str) -> dict:
        import re

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
    def _recommend(overall: float, metrics: dict) -> str:
        if overall >= 75:
            return "hire"
        if overall >= 55:
            return "maybe"
        return "reject"

    @staticmethod
    def _default_strengths(metrics: dict) -> list[str]:
        strengths = []
        if metrics["mcq"]["accuracy"] is not None and metrics["mcq"]["accuracy"] >= 0.7:
            strengths.append("Strong MCQ accuracy")
        if metrics["overall_score"] >= 70:
            strengths.append("Good overall performance")
        top_skills = list(metrics["skills"].items())[:2]
        strengths.extend(f"Strong in {skill}" for skill, score in top_skills if score >= 70)
        return strengths[:3] or ["Consistent participation"]

    @staticmethod
    def _default_weaknesses(metrics: dict) -> list[str]:
        weaknesses = []
        low_skills = [(skill, score) for skill, score in metrics["skills"].items() if score < 60]
        weaknesses.extend(f"Needs improvement in {skill}" for skill, score in low_skills[:2])
        if metrics["unanswered"] > 0:
            weaknesses.append(f"{metrics['unanswered']} questions unanswered")
        return weaknesses[:3] or ["Deeper practice recommended"]

    # --- Reads ---

    def get_feedback(self, session_id: int) -> Optional[dict]:
        return fetch_one(
            "SELECT session_id, metrics, overall_score, recommendation, summary, created_at "
            "FROM feedback WHERE session_id = %s",
            (session_id,),
        )

    def list_for_user(self, user_id: int) -> list[dict]:
        return query(
            """
            SELECT f.id, f.session_id, f.overall_score, f.recommendation, f.summary, f.created_at
            FROM feedback f
            JOIN interview_sessions s ON s.id = f.session_id
            WHERE s.user_id = %s ORDER BY f.created_at DESC
            """,
            (user_id,),
        )