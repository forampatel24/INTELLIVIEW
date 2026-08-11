from typing import Optional

import spacy

from ai.resume_parser.skill_extractor import SKILL_ALIASES, COMMON_SKILLS


class ATSScorer:
    """Heuristic ATS score: penalizes missing sections, low skill match, short text."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = spacy.load(model_name, disable=["ner", "parser"])

    def score(self, sections: dict[str, str], raw_text: str, skills: list[str]) -> dict:
        present = set(sections.keys())
        weights = {
            "summary": 10,
            "experience": 15,
            "education": 10,
            "projects": 15,
            "skills": 20,
            "certifications": 5,
            "achievements": 5,
            "technologies": 10,
        }
        section_score = sum(weights.get(k, 0) for k in present)

        lower = raw_text.lower()
        skill_hits = sum(1 for s in skills if s.lower() in lower)
        skill_score = min(15, skill_hits * 2)

        length_score = 5 if len(raw_text) > 1500 else (2 if len(raw_text) > 500 else 0)

        contact_score = 10
        for token in ("@", "+"):
            if token in lower:
                contact_score -= 3

        total = min(100, section_score + skill_score + length_score + contact_score)
        missing = [k for k in ("summary", "experience", "projects", "certifications") if k not in present]
        return {
            "score": total,
            "section_score": section_score,
            "skill_score": skill_score,
            "length_score": length_score,
            "contact_score": max(0, contact_score),
            "present_sections": sorted(present),
            "missing_sections": missing,
        }
