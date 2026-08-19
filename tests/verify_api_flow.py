"""End-to-end verification of Phases 15 & 16 API integration.

Exercises the new routers (resumes/domains/questions/interviews/monitoring)
over HTTP via FastAPI TestClient, including local file upload storage.

Run: venv\\Scripts\\python.exe tests\\verify_api_flow.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["RESUME_PROVIDER"] = "mock"
os.environ["QUESTION_PROVIDER"] = "mock"
os.environ["EVALUATION_PROVIDER"] = "mock"
os.environ["BEHAVIOR_PROVIDER"] = "mock"
os.environ["FEEDBACK_PROVIDER"] = "mock"
os.environ["REPORT_PROVIDER"] = "mock"

from services.llm.router import get_router
get_router.cache_clear()

passed: list[str] = []
failed: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        passed.append(name)
        print(f"  [PASS] {name}")
    else:
        failed.append(name)
        print(f"  [FAIL] {name} {detail}")


print("=" * 64)
print("PHASES 15/16 - API INTEGRATION + LOCAL FILE STORAGE")
print("=" * 64)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

with client:  # triggers lifespan -> migrate
    # --- Auth ---
    from database.connection import execute
    EMAIL = "__apiflow__@test.local"
    client.delete("/x")
    r = client.post("/api/auth/register", json={"name": "API Flow", "email": EMAIL, "password": "secret123"})
    check("register over HTTP", r.status_code == 201, str(r.status_code))
    if r.status_code == 400:
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": "secret123"})
        token = r.json()["access_token"]
    else:
        token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/auth/me", headers=headers)
    check("me endpoint", r.status_code == 200 and r.json()["email"] == EMAIL, str(r.status_code))

    # --- Domains ---
    r = client.get("/api/domains", headers=headers)
    domains = r.json()
    check("list domains", r.status_code == 200 and isinstance(domains, list) and len(domains) >= 20, str(len(domains) if isinstance(domains, list) else r.text))
    domain_id = next((d["id"] for d in domains if d["name"] == "Python"), domains[0]["id"])
    r = client.get("/api/domains/categories", headers=headers)
    check("list categories", r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1, str(r.json())[:80])

    # --- Question bank ---
    r = client.get("/api/questions", headers=headers, params={"domain_id": domain_id, "limit": 5})
    qs = r.json()
    check("list bank questions", r.status_code == 200 and isinstance(qs, list) and len(qs) >= 1, str(r.status_code))
    r = client.get("/api/questions/counts", headers=headers, params={"domain_id": domain_id})
    check("question counts", r.status_code == 200 and isinstance(r.json(), dict), str(r.json())[:80])

    # --- Resume upload (phase 16 local file storage) ---
    sample = Path("storage/uploads/sample_resume.pdf").read_bytes()
    r = client.post("/api/resumes/upload", headers=headers, files={"file": ("sample_resume.pdf", sample, "application/pdf")})
    upload = r.json()
    check("resume upload", r.status_code == 201 and "resume_id" in upload, f"{r.status_code} {str(upload)[:120]}")
    resume_id = upload.get("resume_id")
    check("upload parsed skills", isinstance(upload.get("parsed", {}).get("skills"), list) and len(upload["parsed"]["skills"]) > 0, str(upload.get("parsed", {}).get("skills"))[:80])

    r = client.get("/api/resumes", headers=headers)
    check("resume list", r.status_code == 200 and any(x["id"] == resume_id for x in r.json()), str(r.json())[:120])
    r = client.get(f"/api/resumes/{resume_id}", headers=headers)
    check("resume detail", r.status_code == 200 and isinstance(r.json().get("skills"), list), str(r.status_code))
    r = client.get(f"/api/resumes/{resume_id}/download", headers=headers)
    check("resume download", r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"), r.headers.get("content-type", ""))

    # --- Interview flow ---
    r = client.post("/api/interviews/start", headers=headers, json={
        "mode": "domain", "total_questions": 3, "domain_id": domain_id, "round_type": "theory"})
    start = r.json()
    check("start interview", r.status_code == 201 and "session_id" in start and "question" in start, f"{r.status_code} {str(start)[:160]}")
    session_id = start["session_id"]

    r = client.get(f"/api/interviews/{session_id}/state", headers=headers)
    check("session state", r.status_code == 200 and r.json().get("session_id") == session_id, str(r.status_code))

    # Answer all questions
    scores = []
    for i in range(3):
        r = client.post(f"/api/interviews/{session_id}/answer", headers=headers, json={
            "answer_text": "I have hands-on experience building web applications with Python, SQL and REST APIs.", "time_taken_sec": 30})
        body = r.json()
        check(f"answer {i+1} submitted", r.status_code == 200 and "score" in body, f"{r.status_code} {str(body)[:120]}")
        scores.append(body.get("score"))
    check("all answers scored", len(scores) == 3 and all(s is not None for s in scores), str(scores))
    check("interview completed", r.json().get("is_complete") is True, str(r.json().get("is_complete")))

    r = client.post(f"/api/interviews/{session_id}/feedback", headers=headers)
    fb = r.json()
    check("generate feedback", r.status_code == 200 and "recommendation" in fb and "metrics" in fb, f"{r.status_code} {str(fb)[:120]}")
    r = client.get(f"/api/interviews/{session_id}/feedback", headers=headers)
    check("fetch feedback", r.status_code == 200 and "overall_score" in r.json(), str(r.status_code))

    r = client.get(f"/api/interviews/{session_id}/report", headers=headers)
    rep = r.json()
    check("generate report", r.status_code == 200 and "radar_data" in rep and "recruiter_summary" in rep, f"{r.status_code} {str(rep)[:120]}")

    # --- Anti-cheating event + monitoring ---
    r = client.post(f"/api/interviews/{session_id}/events", headers=headers, json={"event_type": "tab_switch"})
    check("cheat event accepted", r.status_code == 200 and r.json().get("accepted") is True, str(r.json()))
    r = client.get(f"/api/monitoring/{session_id}", headers=headers)
    verdict = r.json()
    check("monitoring verdict", r.status_code == 200 and "risk_score" in verdict and verdict["status"] in ("clean", "suspicious", "flagged"), str(verdict)[:120])
    r = client.get(f"/api/monitoring/{session_id}/report", headers=headers)
    check("monitoring report", r.status_code == 200 and "verdict" in r.json() and "camera_summary" in r.json(), str(r.status_code))

    # --- Sessions list ---
    r = client.get("/api/interviews", headers=headers)
    check("sessions list", r.status_code == 200 and any(s["id"] == session_id for s in r.json()), str(r.status_code))

    # --- Negative checks ---
    r = client.post("/api/interviews/999999/answer", headers=headers, json={"answer_text": "x"})
    check("404 for missing session", r.status_code == 404, str(r.status_code))
    r = client.get("/api/resumes/999999", headers=headers)
    check("404 for missing resume", r.status_code == 404, str(r.status_code))
    r = client.get("/api/auth/me")
    check("401 without token", r.status_code == 401, str(r.status_code))

    # cleanup
    execute("DELETE FROM analytics")
    execute("DELETE FROM activity_logs")
    execute("DELETE FROM warnings")
    execute("DELETE FROM eye_tracking")
    execute("DELETE FROM camera_logs")
    execute("DELETE FROM feedback")
    execute("DELETE FROM reports")
    execute("DELETE FROM answers")
    execute("DELETE FROM questions WHERE session_id IS NOT NULL")
    execute("DELETE FROM interview_sessions")
    execute("DELETE FROM resumes WHERE user_id = (SELECT id FROM users WHERE email=%s)", (EMAIL,))
    execute("DELETE FROM users WHERE email=%s", (EMAIL,))

print("=" * 64)
print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
print("=" * 64)
if failed:
    print("FAILED:", failed)
print("\ncleanup done")
sys.exit(1 if failed else 0)