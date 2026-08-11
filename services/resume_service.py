import json
import os
import time
import uuid
from typing import Optional

from ai.resume_parser.ats_scorer import ATSScorer
from ai.resume_parser.parser import ResumeParser
from database.connection import execute, fetch_one
from utils.config import settings

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "uploads")


class ResumeService:
    def __init__(self):
        self.parser = ResumeParser(use_ai=True)
        self.ats_scorer = ATSScorer()

    def upload_and_parse(self, user_id: int, filename: str, content: bytes) -> dict:
        if not filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported")
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("File too large (max 10MB)")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(file_path, "wb") as fh:
            fh.write(content)

        parsed = self.parser.parse_pdf(file_path)
        ats = self.ats_scorer.score(parsed.get("sections", {}), parsed.get("parsed_text", ""), parsed.get("skills", []))

        sections = parsed.get("sections", {})
        resume_id = execute(
            """
            INSERT INTO resumes
                (user_id, file_path, original_name, file_size, parsed_text, parsed_json,
                 skills, projects, education, certifications, experience, technologies,
                 strengths, weaknesses, ats_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                user_id,
                file_path,
                filename,
                len(content),
                parsed.get("parsed_text", ""),
                json.dumps(parsed),
                json.dumps(parsed.get("skills", [])),
                json.dumps(parsed.get("projects", [])),
                json.dumps(parsed.get("education", [])),
                json.dumps(parsed.get("certifications", [])),
                json.dumps(parsed.get("experience", [])),
                json.dumps(parsed.get("technologies", [])),
                json.dumps(parsed.get("strengths", [])),
                json.dumps(parsed.get("weaknesses", [])),
                ats.get("score", 0),
            ),
        )
        return {"resume_id": resume_id, "parsed": parsed, "ats": ats}

    def get(self, resume_id: int) -> Optional[dict]:
        return fetch_one(
            """
            SELECT id, original_name, file_path, skills, projects, education, certifications,
                   experience, technologies, strengths, weaknesses, ats_score, created_at
            FROM resumes WHERE id = %s
            """,
            (resume_id,),
        )

    def list_for_user(self, user_id: int) -> list[dict]:
        from database.connection import query

        return query(
            """
            SELECT id, original_name, ats_score, created_at
            FROM resumes WHERE user_id = %s ORDER BY created_at DESC
            """,
            (user_id,),
        )
