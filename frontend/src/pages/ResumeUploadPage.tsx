import { useCallback, useEffect, useRef, useState } from "react";
import { fetchResumes, uploadResume } from "../api";
import { apiErrorMessage } from "../api/client";
import type { ResumeListItem, ResumeSummary } from "../api/types";

export default function ResumeUploadPage() {
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [result, setResult] = useState<ResumeSummary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    fetchResumes().then(setResumes).catch(() => setResumes([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleFile(file: File) {
    setError("");
    setBusy(true);
    try {
      const res = await uploadResume(file);
      setResult(res);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Resume upload</h1>
        <p className="text-slate-500">
          Upload a PDF — it is stored locally and parsed for skills, experience, and an ATS score.
        </p>
      </div>

      <div
        className={`card flex cursor-pointer flex-col items-center justify-center border-2 border-dashed py-12 text-center ${
          dragOver ? "border-indigo-400 bg-indigo-50" : "border-slate-300"
        }`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void handleFile(file);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
        <p className="text-lg font-medium text-slate-700">
          {busy ? "Uploading & parsing…" : "Click or drop a PDF here"}
        </p>
        <p className="text-sm text-slate-400">Max 10 MB, PDF only</p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="card">
          <h2 className="mb-3 text-lg font-semibold">Parsed resume</h2>
          <p className="mb-4 text-sm text-slate-600">
            {result.original_name} — ATS score:{" "}
            <span className="font-semibold text-indigo-700">{result.ats.score}/100</span>
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <h3 className="mb-1 text-sm font-semibold text-slate-500">Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {result.parsed.skills.map((s) => (
                  <span key={s} className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-1 text-sm font-semibold text-slate-500">Technologies</h3>
              <div className="flex flex-wrap gap-1.5">
                {result.parsed.technologies.map((t) => (
                  <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-1 text-sm font-semibold text-slate-500">Strengths</h3>
              <ul className="list-inside list-disc text-sm text-slate-700">
                {result.parsed.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-1 text-sm font-semibold text-slate-500">Weaknesses</h3>
              <ul className="list-inside list-disc text-sm text-slate-700">
                {result.parsed.weaknesses.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">Your resumes</h2>
        {resumes.length === 0 && <p className="text-sm text-slate-500">No resumes uploaded yet.</p>}
        <ul className="divide-y">
          {resumes.map((r) => (
            <li key={r.id} className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-slate-700">{r.original_name}</p>
                <p className="text-xs text-slate-400">
                  ATS {r.ats_score} · {new Date(r.created_at).toLocaleDateString()}
                </p>
              </div>
              <a
                className="text-sm font-medium text-indigo-600 hover:underline"
                href={`/api/resumes/${r.id}/download`}
                target="_blank"
                rel="noreferrer"
              >
                Download
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}