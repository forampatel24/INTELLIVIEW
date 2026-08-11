import json
import re
from typing import Optional

from ai.resume_parser.section_detector import detect_contact_info, detect_sections
from ai.resume_parser.skill_extractor import SkillExtractor
from ai.resume_parser.text_extractor import ResumeTextExtractor
from services.llm import LLMError, router

RESUME_PROMPT_TEMPLATE = """
You are a resume parsing assistant. Analyze the following resume text and return STRICT JSON only.

Return this exact JSON structure:
{{
  "name": "Candidate name or empty string",
  "contact": {{"email": "", "phone": "", "linkedin": "", "github": ""}},
  "summary": "one paragraph or empty",
  "education": [{{"degree": "", "institution": "", "year": "", "details": ""}}],
  "experience": [{{"title": "", "company": "", "years": "", "details": ""}}],
  "projects": [{{"title": "", "tech": [], "details": ""}}],
  "certifications": [{{"name": "", "issuer": "", "year": ""}}],
  "technologies": ["list"],
  "strengths": ["list"],
  "weaknesses": ["list"],
  "years_of_experience": "string"
}}

Rules:
- Return ONLY valid JSON, no markdown, no code fences, no extra text.
- strengths/weaknesses: infer from the resume content. If unclear, give reasonable professional assessments.
- Do not invent data not present. Use empty arrays for missing sections.

RESUME TEXT:
{resume_text}
"""


class ResumeParser:
    def __init__(self, use_ai: bool = True, model_name: str = "en_core_web_sm"):
        self.text_extractor = ResumeTextExtractor()
        self.section_detector = detect_sections
        self.skill_extractor = SkillExtractor(model_name=model_name)
        self.use_ai = use_ai

    def parse_pdf(self, file_path: str) -> dict:
        raw_text = self.text_extractor.extract_text(file_path)
        metadata = self.text_extractor.extract_metadata(file_path)
        return self.parse_text(raw_text, metadata=metadata)

    def parse_text(self, raw_text: str, metadata: Optional[dict] = None) -> dict:
        sections = self.section_detector(raw_text)
        contact = detect_contact_info(raw_text)
        skills = self.skill_extractor.extract_from_sections(sections)

        result: dict = {
            "contact": contact,
            "skills": skills,
            "sections": sections,
            "parsed_text": raw_text[:5000],
            "metadata": metadata or {},
        }

        if self.use_ai:
            try:
                ai_data = self._ai_structured(raw_text)
                result.update(ai_data)
                if skills:
                    merged = list(dict.fromkeys([*skills, *ai_data.get("technologies", [])]))
                    result["skills"] = merged
            except LLMError as exc:
                result["ai_error"] = str(exc)
                result["name"] = ""
                result["summary"] = ""
                result["education"] = []
                result["experience"] = []
                result["projects"] = []
                result["certifications"] = []
                result["technologies"] = skills
                result["strengths"] = []
                result["weaknesses"] = []
                result["years_of_experience"] = ""
        return result

    def _ai_structured(self, raw_text: str) -> dict:
        prompt = RESUME_PROMPT_TEMPLATE.format(resume_text=raw_text[:20000])
        response = router.generate("resume_analysis", prompt, max_tokens=2048, temperature=0.1)
        return self._parse_json(response.text)

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
