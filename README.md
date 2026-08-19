# 🎤 IntelliVue v2.0

**AI-powered interview intelligence platform.** IntelliVue turns a candidate's resume into a fully adaptive mock interview, evaluates every answer, generates structured feedback, and produces a recruiter-ready report — with AI question generation, camera-based proctoring, and a multi-provider AI layer that works with Gemini, OpenAI, or Claude.

> Built as a fresh v2 rewrite. Legacy v1 code is preserved in [`legacy/`](legacy/) for reference.

---

## ✨ Features

| Area | What it does |
|------|--------------|
| **Resume Parser** | Extracts text from PDFs (PyMuPDF), detects sections, extracts skills with spaCy + a curated skill dictionary, and enriches the profile with an LLM (projects, education, experience, strengths, weaknesses). Produces an **ATS score**. |
| **Adaptive Interview Engine** | Runs a question pipeline: skill extraction → experience detection → difficulty selection → question generation → answer evaluation → adaptive next question. Difficulty moves one step per answer based on recent performance (easy ↔ medium ↔ hard). |
| **Question Bank & Rounds** | 77 curated questions across 20 domains, all 5 round types (**MCQ, Coding, Theory, Scenario, Rapid Fire**) and all 3 difficulties, stored in MySQL with answer keys. Domain-mode interviews pull from the bank first (no AI cost); AI generation is the fallback. |
| **Domain System** | 31 predefined interview domains across 7 categories — from Python/C++/React to ML/DL/Cybersecurity to Finance/Marketing/Behavioral. |
| **Feedback Engine** | Computes structured metrics (per-difficulty, per-skill, MCQ accuracy, consistency) and generates a hire/maybe/reject recommendation with strengths, weaknesses, and next steps. |
| **Report Generator** | Builds a recruiter-ready report from a completed session: radar/heatmap/timeline chart data, strengths, weaknesses, suggestions, curated learning resources, and a recruiter-facing summary. |
| **Camera Monitoring Service** | Real-time camera analysis with MediaPipe FaceMesh (OpenCV Haar fallback): face detection, eye aspect ratio (blink/drowsiness), gaze/eye contact, head movement, smile detection, attention scoring — logged to `camera_logs`, `eye_tracking`, `warnings`, `activity_logs`, and `analytics`. |
| **Anti-Cheating Module** | Rule engine over camera snapshots and client events (tab switch, copy/paste, fullscreen exit): sustained no-face / looking-away / drowsiness / low-attention / head-movement escalations, weighted risk score (0–100), and a per-session verdict (`clean` / `suspicious` / `flagged`). |
| **Multi-Provider AI Layer** | One router, six AI tasks (`resume_analysis`, `question_generation`, `answer_evaluation`, `behavior_analysis`, `feedback_generation`, `report_generation`), each configurable to run on **Gemini, OpenAI, or Claude**. A built-in `mock` provider lets the whole system run with zero API keys. |
| **Auth** | JWT-based registration/login/refresh with bcrypt password hashing and role support (`user` / `recruiter` / `admin`). |
| **REST API** | 26 endpoints across auth, resume upload/download, domains, question bank, interviews (start/answer/feedback/report), and monitoring — all behind JWT bearer auth. |
| **Web Frontend** | React + Vite + TypeScript + Tailwind SPA: login/register, dashboard, resume upload with parsed-profile preview, guided interview flow (MCQ/text answers, adaptive scoring), results page with radar + timeline charts, and an integrity-monitoring page. |
| **Local File Storage** | Uploaded resumes are stored under `storage/uploads/` on disk, with ownership checks and a download endpoint. |

---

## 🧱 Architecture

```
Resume
   │
   ▼
Resume Parser ──────► structured resume (skills, projects, education, …)
   │
   ▼
Skill Extraction ───► years of experience detection
   │
   ▼
Difficulty Selector ─► adaptive easy/medium/hard
   │
   ▼
Question Generator ─► per round type (MCQ / Coding / Theory / Scenario / Rapid Fire)
   │                     bank-first, AI-fallback
   ▼
Interview State Manager ─► session persistence (MySQL)
   │
   ▼
Answer Evaluation ───────► score + feedback
   │
   ▼
Adaptive Next Question
   │
   ▼
Final Report / Feedback Engine
```

### Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Database | MySQL (raw SQL via PyMySQL — **no ORM**) |
| AI | `google-generativeai`, `openai`, `anthropic` behind a unified router |
| Resume parsing | PyMuPDF, spaCy, Transformers |
| Camera / monitoring | OpenCV, MediaPipe (protobuf pinned to 4.25.9) |
| Frontend | React 18 + Vite + TypeScript + Tailwind v4 |
| Cache | Redis |

---

## 📁 Project structure

```
INTELLIVIEW/
├── ai/
│   ├── resume_parser/        # PDF text extraction, sections, skills, ATS score
│   ├── interview_engine/     # state, adaptive difficulty, question generator, evaluator
│   ├── question_bank/        # 77 curated questions + bank service
│   ├── domains/              # 31 predefined domains + domain service
│   ├── feedback_engine/      # metrics + feedback generation
│   ├── report_generator/     # report data builders + ReportGenerator
│   ├── face_monitor/         # camera monitoring: detector, analyzer, service, monitor
│   ├── eye_tracker/          # gaze/blink tracking (EyeTracker)
│   ├── anti_cheating/        # rule engine, risk scoring, session verdicts
│   ├── emotion_detector/     # (upcoming)
├── auth/                     # security, tokens, dependencies, auth service
├── backend/
│   ├── main.py               # FastAPI app entry point
│   └── routers/              # auth, resumes, domains, questions, interviews, monitoring
├── frontend/
│   ├── src/
│   │   ├── api/              # axios client + typed API functions
│   │   ├── context/          # AuthContext (login/register/logout)
│   │   ├── components/       # shared layout
│   │   └── pages/            # login, register, dashboard, resume, interview, results, monitoring
│   ├── index.html
│   ├── vite.config.ts        # dev proxy /api -> :8000
│   └── package.json
├── database/
│   ├── connection.py         # thread-safe connection pool
│   ├── migrate.py            # auto-create DB + apply migrations
│   ├── schema.sql            # canonical 15-table schema
│   └── migrations/           # numbered .sql migration files
├── services/
│   ├── llm/                  # base, providers (gemini/openai/claude/mock), router
│   └── resume_service.py     # upload → parse → persist
├── storage/
│   ├── uploads/              # uploaded resumes (stored locally, gitignored)
│   └── recordings/           # (upcoming) interview recordings
├── models/                   # model artifacts (spaCy, etc.)
├── prompts/                  # prompt templates
├── utils/config.py           # settings (env-driven)
├── tests/                    # verification scripts (verify_phases_1_9.py)
├── legacy/                   # v1 code preserved for reference
├── docs/
├── .env                      # your local secrets (not committed)
├── requirements.txt
└── README.md
```

---

## 🚀 Getting started

### Prerequisites
- Python 3.12+
- MySQL 8+ (tested with MySQL 9.x)
- (Optional) Redis, and API keys for at least one AI provider

### 1. Clone & create the environment

```bash
git clone <your-repo-url> INTELLIVIEW
cd INTELLIVIEW
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure environment

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

Edit `.env` and set at minimum:

```ini
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=intellivue

# Pick your AI provider — or use mock to run without keys
DEFAULT_AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
```

> **No API keys?** Set `DEFAULT_AI_PROVIDER=mock`. The whole pipeline (resume parsing, question generation, evaluation, feedback) degrades gracefully to rule-based fallbacks — perfect for testing the platform without spending money.

### 3. Run the database migrations

The FastAPI app runs migrations automatically on startup. To apply them manually:

```bash
venv\Scripts\python -m database.migrate
```

This creates the `intellivue` database if missing and applies every pending file in `database/migrations/`.

### 4. Seed reference data

```bash
venv\Scripts\python -c "from ai.domains import DomainService; print(DomainService().seed())"
venv\Scripts\python -c "from ai.question_bank import QuestionBankService; print(QuestionBankService().seed())"
```

Seeding is **idempotent** — safe to run any time.

### 5. Start the API

```bash
venv\Scripts\python -m uvicorn backend.main:app --reload
```

- API docs (Swagger UI): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

### 6. Start the frontend (optional — the API is fully usable on its own)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173 (dev server proxies `/api` → `http://localhost:8000`)
- Production build: `npm run build` (outputs to `frontend/dist/`)

---

## 🔌 API endpoints (current)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/` | App info | — |
| `GET` | `/api/health` | Health check | — |
| `POST` | `/api/auth/register` | Create account (`{name, email, password, role}`) | — |
| `POST` | `/api/auth/login` | Login → access + refresh tokens | — |
| `POST` | `/api/auth/refresh` | Exchange refresh token for new access token | — |
| `GET` | `/api/auth/me` | Current user profile | Bearer token |
| `POST` | `/api/resumes/upload` | Upload PDF → store locally + parse + ATS score | Bearer token |
| `GET` | `/api/resumes` | List my resumes | Bearer token |
| `GET` | `/api/resumes/{id}` | Resume details (skills, experience, strengths…) | Bearer token |
| `GET` | `/api/resumes/{id}/download` | Download the stored original PDF | Bearer token |
| `GET` | `/api/domains` | List interview domains (`?category=`) | Bearer token |
| `GET` | `/api/domains/categories` | Domain categories | Bearer token |
| `GET` | `/api/questions` | Question bank (`?domain_id&question_type&difficulty`) | Bearer token |
| `GET` | `/api/questions/counts` | Bank question counts by difficulty | Bearer token |
| `POST` | `/api/interviews/start` | Start an interview → session + first question | Bearer token |
| `GET` | `/api/interviews` | My interview sessions | Bearer token |
| `GET` | `/api/interviews/{id}/state` | Session progress/score state | Bearer token |
| `GET` | `/api/interviews/{id}/question` | Current question (generates if needed) | Bearer token |
| `POST` | `/api/interviews/{id}/answer` | Submit an answer → score + feedback | Bearer token |
| `POST` | `/api/interviews/{id}/feedback` | Generate candidate feedback | Bearer token |
| `GET` | `/api/interviews/{id}/feedback` | Fetch stored feedback | Bearer token |
| `GET` | `/api/interviews/{id}/report` | Recruiter report (radar/heatmap/timeline data) | Bearer token |
| `POST` | `/api/interviews/{id}/events` | Log anti-cheat event (tab switch, copy/paste…) | Bearer token |
| `GET` | `/api/monitoring/{id}` | Anti-cheating verdict + risk score | Bearer token |
| `GET` | `/api/monitoring/{id}/report` | Full monitoring report (camera + warnings) | Bearer token |

> The React frontend (`frontend/`) calls all of these through an axios client with automatic bearer-token injection and a dev-server proxy (`/api` → `:8000`).

---

## 🧪 Testing

```bash
venv\Scripts\python tests\verify_phases_1_9.py
venv\Scripts\python tests\verify_phase_10.py
venv\Scripts\python tests\verify_phase_11.py
venv\Scripts\python tests\verify_phase_12.py
venv\Scripts\python tests\verify_api_flow.py
```

The first script runs **55 checks** across phases 1–9: scaffolding, AI router, database, auth, resume parsing, interview engine, domains, question bank, and feedback. The phase 10 script runs **25 checks** for the report generator, the phase 11 script runs **28 checks** for the camera monitoring service, the phase 12 script runs **39 checks** for the anti-cheating module, and the API-flow script runs **28 checks** over HTTP against the routers (auth → domains → resume upload/download → interview → feedback → report → monitoring) — all against a live MySQL connection, then clean up after themselves. (Run the suites one at a time — they share the same test tables.)

---

## 🔑 AI provider routing

Each AI task can run on a different provider via `.env`:

```ini
DEFAULT_AI_PROVIDER=gemini          # global default

RESUME_PROVIDER=gemini              # per-task overrides (optional)
QUESTION_PROVIDER=openai
EVALUATION_PROVIDER=claude
BEHAVIOR_PROVIDER=gemini
FEEDBACK_PROVIDER=gemini
REPORT_PROVIDER=gemini
```

Available providers: `gemini`, `openai`, `claude`, `mock`.

---

## 🗄️ Database schema (16 tables)

`users`, `resumes`, `domains`, `skills`, `interview_sessions`, `questions`, `answers`, `feedback`, `reports`, `achievements`, `warnings`, `camera_logs`, `eye_tracking`, `activity_logs`, `analytics`, plus `schema_migrations`.

Full DDL lives in [`database/schema.sql`](database/schema.sql). Schema changes go in `database/migrations/` as numbered `.sql` files.

---

## 🗺️ Roadmap

| Phase | Status |
|-------|--------|
| 1 — Scaffolding | ✅ |
| 2 — AI Multi-Provider Layer | ✅ |
| 3 — Database Setup | ✅ |
| 4 — Auth Module | ✅ |
| 5 — Resume Parser | ✅ |
| 6 — Interview Engine | ✅ |
| 7 — Domain System | ✅ |
| 8 — Question Bank & Rounds | ✅ |
| 9 — Feedback Engine | ✅ |
| 10 — Report Generator | ✅ |
| 11 — Camera Monitoring Service | ✅ |
| 12 — Anti-Cheating Module | ✅ |
| 13 — React Frontend Setup | ✅ |
| 14 — Frontend Pages | ✅ |
| 15 — API Integration | ✅ |
| 16 — Local File Storage | ✅ |
| 17 — Testing | ⏳ |
| 18 — Documentation | ⏳ |
| 19 — Security Audit | ⏳ |
| Post-MVP — Emotion/Stress Detection | ⏳ |

---

## 📄 License

Released under the [MIT License](LICENSE). See the LICENSE file for the full terms — you are free to use, copy, modify, and distribute this software.
