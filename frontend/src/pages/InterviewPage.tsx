import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDomains, fetchResumes, fetchCurrentQuestion, startInterview, submitAnswer } from "../api";
import { apiErrorMessage } from "../api/client";
import type { Domain, Question, ResumeListItem, SessionState } from "../api/types";

const ROUND_TYPES = ["theory", "coding", "mcq", "scenario", "rapid_fire"];

export default function InterviewPage() {
  const navigate = useNavigate();
  const [domains, setDomains] = useState<Domain[]>([]);
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [mode, setMode] = useState<"resume" | "domain">("domain");
  const [roundType, setRoundType] = useState("theory");
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [domainId, setDomainId] = useState<number | undefined>();
  const [resumeId, setResumeId] = useState<number | undefined>();
  const [error, setError] = useState("");

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [state, setState] = useState<SessionState | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedOption, setSelectedOption] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<{ score: number; feedback: string; nextDifficulty: string } | null>(null);

  useEffect(() => {
    fetchDomains().then(setDomains).catch(() => setDomains([]));
    fetchResumes().then(setResumes).catch(() => setResumes([]));
  }, []);

  async function onStart() {
    setError("");
    setBusy(true);
    try {
      const res = await startInterview({
        mode,
        total_questions: totalQuestions,
        domain_id: domainId,
        resume_id: mode === "resume" ? resumeId : undefined,
        round_type: roundType,
      });
      setSessionId(res.session_id);
      setState(res.state);
      setQuestion(res.question);
      setLastResult(null);
      setSelectedOption("");
      setAnswerText("");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onNextQuestion() {
    if (!sessionId) return;
    setBusy(true);
    setError("");
    setLastResult(null);
    setSelectedOption("");
    setAnswerText("");
    try {
      const res = await fetchCurrentQuestion(sessionId);
      setState(res.state);
      setQuestion(res.question);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmitAnswer() {
    if (!sessionId || !question) return;
    setBusy(true);
    setError("");
    try {
      const res = await submitAnswer(sessionId, {
        selected_option: selectedOption || undefined,
        answer_text: answerText || undefined,
        time_taken_sec: 30,
      });
      setState(res.state);
      setLastResult({
        score: res.score,
        feedback: res.feedback,
        nextDifficulty: res.next_difficulty,
      });
      if (res.is_complete) {
        navigate(`/result/${sessionId}`);
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const progress = useCallback(() => {
    if (!state) return 0;
    return Math.round((state.current_index / state.total_questions) * 100);
  }, [state]);

  // --- Setup view ---
  if (!sessionId) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Start an interview</h1>
          <p className="text-slate-500">Pick a mode and difficulty; questions adapt as you answer.</p>
        </div>
        <div className="card space-y-4">
          <div>
            <label className="label">Mode</label>
            <div className="flex gap-2">
              <button
                className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium ${mode === "domain" ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-300"}`}
                onClick={() => setMode("domain")}
              >
                Domain based
              </button>
              <button
                className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium ${mode === "resume" ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-300"}`}
                onClick={() => setMode("resume")}
              >
                Resume based
              </button>
            </div>
          </div>

          {mode === "domain" ? (
            <div>
              <label className="label">Domain</label>
              <select className="input" value={domainId ?? ""} onChange={(e) => setDomainId(e.target.value ? Number(e.target.value) : undefined)}>
                <option value="">Select a domain…</option>
                {domains.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.category})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className="label">Resume</label>
              <select className="input" value={resumeId ?? ""} onChange={(e) => setResumeId(e.target.value ? Number(e.target.value) : undefined)}>
                <option value="">Select a resume…</option>
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.original_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="label">Round type</label>
            <div className="flex flex-wrap gap-2">
              {ROUND_TYPES.map((rt) => (
                <button
                  key={rt}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium capitalize ${roundType === rt ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-300"}`}
                  onClick={() => setRoundType(rt)}
                >
                  {rt.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label">Total questions</label>
            <input
              className="input"
              type="number"
              min={1}
              max={30}
              value={totalQuestions}
              onChange={(e) => setTotalQuestions(Math.max(1, Math.min(30, Number(e.target.value) || 1)))}
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn-primary w-full" onClick={onStart} disabled={busy || (mode === "domain" && !domainId)}>
            {busy ? "Starting…" : "Start interview"}
          </button>
        </div>
      </div>
    );
  }

  // --- Interview view ---
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">
            Question {state?.current_index ?? 0}/{state?.total_questions}
          </h1>
          <span className="text-sm text-slate-500">
            {state?.difficulty} · {state?.round_type}
          </span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div className="h-full bg-indigo-600 transition-all" style={{ width: `${progress()}%` }} />
        </div>
      </div>

      <div className="card">
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 uppercase">
            {question?.type}
          </span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
            {question?.difficulty}
          </span>
          {question?.skill_tags?.map((t) => (
            <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
              {t}
            </span>
          ))}
        </div>
        <p className="text-lg font-medium text-slate-800">{question?.text}</p>
      </div>

      {question?.options && question.options.length > 0 ? (
        <div className="space-y-2">
          {question.options.map((opt) => (
            <button
              key={opt}
              className={`w-full rounded-lg border px-4 py-3 text-left text-sm ${selectedOption === opt ? "border-indigo-500 bg-indigo-50 text-indigo-800" : "border-slate-300 hover:border-slate-400"}`}
              onClick={() => setSelectedOption(opt)}
              disabled={lastResult !== null}
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <div className="card">
          <label className="label" htmlFor="answer">Your answer</label>
          <textarea
            id="answer"
            className="input min-h-40"
            placeholder="Type your answer here…"
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            disabled={lastResult !== null}
          />
        </div>
      )}

      {lastResult ? (
        <div className="card border-indigo-200 bg-indigo-50">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-lg font-semibold text-indigo-700">Score: {lastResult.score}/100</span>
            <span className="text-sm text-slate-500">Next: {lastResult.nextDifficulty}</span>
          </div>
          <p className="text-sm text-slate-700">{lastResult.feedback}</p>
          <div className="mt-4">
            <button className="btn-primary" onClick={onNextQuestion} disabled={busy}>
              {busy ? "Loading…" : "Next question →"}
            </button>
          </div>
        </div>
      ) : (
        <button className="btn-primary w-full" onClick={onSubmitAnswer} disabled={busy}>
          {busy ? "Submitting…" : "Submit answer"}
        </button>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}