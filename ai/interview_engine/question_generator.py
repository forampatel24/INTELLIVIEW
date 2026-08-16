import json
import re
from typing import Optional

from ai.interview_engine.state import Difficulty, QuestionRecord, QuestionType
from services.llm import LLMError, router

PROMPTS = {
    QuestionType.THEORY: (
        "You are a technical interviewer. Ask a {difficulty} theory question about {focus}. "
        "The candidate's relevant skills: {skills}. Return ONLY JSON: "
        '{{"question": "...", "skill_tags": ["..."]}}. No options, no code fences.'
    ),
    QuestionType.CODING: (
        "You are a coding interviewer. Ask a {difficulty} coding problem about {focus}. "
        "Return ONLY JSON: "
        '{{"question": "...", "skill_tags": ["..."]}}. '
        "Describe the problem clearly with input/output expectations but do NOT provide the solution."
    ),
    QuestionType.MCQ: (
        "You are a technical interviewer. Ask a {difficulty} multiple-choice question about {focus}. "
        "Return ONLY JSON: "
        '{{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], '
        '"correct_answer": "A", "skill_tags": ["..."]}}. '
        "correct_answer must be the option letter."
    ),
    QuestionType.SCENARIO: (
        "You are a behavioral interviewer. Ask a {difficulty} scenario question about {focus}. "
        "The candidate's skills: {skills}. Return ONLY JSON: "
        '{{"question": "...", "skill_tags": ["..."]}}.'
    ),
    QuestionType.RAPID_FIRE: (
        "You are a rapid-fire interviewer. Ask a quick {difficulty} factual question about {focus}. "
        "Return ONLY JSON: "
        '{{"question": "...", "skill_tags": ["..."]}}. Keep it short and answerable in 1-2 sentences.'
    ),
}


class QuestionGenerator:
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai

    def generate(
        self,
        round_type: QuestionType,
        difficulty: Difficulty,
        focus_skills: list[str],
        asked_texts: Optional[list[str]] = None,
    ) -> QuestionRecord:
        asked_texts = asked_texts or []
        focus = ", ".join(focus_skills[:5]) if focus_skills else "general programming"
        template = PROMPTS.get(round_type, PROMPTS[QuestionType.THEORY])

        if not self.use_ai:
            return self._fallback(round_type, difficulty, focus_skills, asked_texts)

        prompt = template.format(difficulty=difficulty.value, focus=focus, skills=", ".join(focus_skills[:10]))
        if asked_texts:
            prompt += f"\n\nIMPORTANT: do NOT repeat any of these already-asked questions:\n{chr(10).join(f'- {t}' for t in asked_texts[-8:])}"

        try:
            response = router.generate("question_generation", prompt, max_tokens=500, temperature=0.8)
            data = self._parse_json(response.text)
            if not data or not data.get("question"):
                raise LLMError("Empty question from provider")
            return QuestionRecord(
                question_type=round_type,
                difficulty=difficulty,
                text=data["question"].strip(),
                options=data.get("options"),
                correct_answer=data.get("correct_answer"),
                skill_tags=data.get("skill_tags") or focus_skills[:3],
            )
        except LLMError:
            return self._fallback(round_type, difficulty, focus_skills, asked_texts)

    def _fallback(
        self,
        round_type: QuestionType,
        difficulty: Difficulty,
        focus_skills: list[str],
        asked_texts: Optional[list[str]] = None,
    ) -> QuestionRecord:
        # Rotate through skills so fallback questions vary across a session.
        asked_count = len(asked_texts or [])
        focus = focus_skills[asked_count % len(focus_skills)] if focus_skills else "the topic"
        text = (
            f"Explain the core concept of {focus} and give a practical example "
            f"(difficulty: {difficulty.value})."
        )
        if round_type == QuestionType.CODING:
            text = f"Write a short program that demonstrates your understanding of {focus}."
        elif round_type == QuestionType.MCQ:
            return QuestionRecord(
                question_type=round_type,
                difficulty=difficulty,
                text=f"Which statement about {focus} is correct?",
                options=["A. Statement 1", "B. Statement 2", "C. Statement 3", "D. Statement 4"],
                correct_answer="A",
                skill_tags=focus_skills[:3],
            )
        elif round_type == QuestionType.RAPID_FIRE:
            text = f"Give a one-line definition of {focus}."
        elif round_type == QuestionType.SCENARIO:
            text = f"Describe a situation where you applied {focus} to solve a real problem."
        return QuestionRecord(
            question_type=round_type, difficulty=difficulty, text=text, skill_tags=focus_skills[:3]
        )

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