import json
import re
from typing import Optional

from ai.interview_engine.state import AnswerRecord, QuestionRecord
from services.llm import LLMError, router

EVALUATION_PROMPT = """
You are a strict but fair interview evaluator. Evaluate the candidate's answer to the given question.

QUESTION: {question}
TYPE: {question_type}
CORRECT ANSWER (if MCQ): {correct_answer}

CANDIDATE ANSWER:
{answer}

Return ONLY JSON:
{{
  "score": <integer 0-100>,
  "feedback": "constructive feedback in 2-3 sentences",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggested_answer": "a model answer in 1-2 sentences"
}}
"""


class AnswerEvaluator:
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai

    def evaluate(self, question: QuestionRecord, answer: AnswerRecord) -> AnswerRecord:
        answer_text = answer.answer_text or answer.code_submitted or ""

        if question.question_type.value == "mcq" and question.correct_answer:
            if not (answer.selected_option or "").strip():
                answer.ai_score = 0
                answer.ai_feedback = "No option was selected."
                return answer
            score = 100 if answer.selected_option.strip().upper() == question.correct_answer.strip().upper() else 0
            answer.ai_score = float(score)
            answer.ai_feedback = (
                "Correct answer." if score == 100
                else f"Incorrect. The correct answer was {question.correct_answer}."
            )
            return answer

        if not answer_text.strip():
            answer.ai_score = 0
            answer.ai_feedback = "No answer was provided."
            return answer

        if not self.use_ai:
            answer.ai_score = 50.0
            answer.ai_feedback = "Evaluated without AI: placeholder score."
            return answer

        prompt = EVALUATION_PROMPT.format(
            question=question.text,
            question_type=question.question_type.value,
            correct_answer=question.correct_answer or "",
            answer=answer_text[:6000],
        )
        try:
            response = router.generate("answer_evaluation", prompt, max_tokens=500, temperature=0.2)
            data = self._parse_json(response.text)
            score = data.get("score")
            if score is None:
                raise LLMError("No score in evaluation")
            answer.ai_score = float(min(100, max(0, int(score))))
            answer.ai_feedback = data.get("feedback") or ""
            return answer
        except LLMError:
            answer.ai_score = 50.0
            answer.ai_feedback = "Evaluation failed; default score assigned."
            return answer

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