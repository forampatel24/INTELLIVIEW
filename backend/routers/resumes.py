"""Resume upload, parsing, and local file storage (phase 16).

Files are stored under storage/uploads/ by ResumeService; this router exposes
upload, listing, detail, and original-file download over HTTP.
"""

import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from auth.dependencies import get_current_user
from database.connection import fetch_one, query
from services.resume_service import ResumeService

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    try:
        content = await file.read()
        result = ResumeService().upload_and_parse(user["id"], file.filename or "resume.pdf", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    parsed = result["parsed"]
    return {
        "resume_id": result["resume_id"],
        "original_name": file.filename,
        "ats": result["ats"],
        "parsed": {
            "skills": parsed.get("skills", [])[:20],
            "projects": parsed.get("projects", []),
            "education": parsed.get("education", []),
            "certifications": parsed.get("certifications", []),
            "experience": parsed.get("experience", []),
            "technologies": parsed.get("technologies", [])[:20],
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
        },
    }


@router.get("")
def list_resumes(user: dict = Depends(get_current_user)):
    return ResumeService().list_for_user(user["id"])


@router.get("/{resume_id}")
def get_resume(resume_id: int, user: dict = Depends(get_current_user)):
    row = ResumeService().get(resume_id)
    if not row or _owner_mismatch(resume_id, user):
        raise HTTPException(status_code=404, detail="Resume not found")
    for key in (
        "skills", "projects", "education", "certifications",
        "experience", "technologies", "strengths", "weaknesses",
    ):
        if isinstance(row.get(key), str):
            try:
                row[key] = json.loads(row[key])
            except json.JSONDecodeError:
                row[key] = None
    return row


@router.get("/{resume_id}/download")
def download_resume(resume_id: int, user: dict = Depends(get_current_user)):
    row = ResumeService().get(resume_id)
    if not row or _owner_mismatch(resume_id, user):
        raise HTTPException(status_code=404, detail="Resume not found")
    path = row.get("file_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(
        path,
        filename=row.get("original_name") or "resume.pdf",
        media_type="application/pdf",
    )


def _owner_mismatch(resume_id: int, user: dict) -> bool:
    owner = fetch_one("SELECT user_id FROM resumes WHERE id = %s", (resume_id,))
    return owner is None or owner["user_id"] != user["id"]