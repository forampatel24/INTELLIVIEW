import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchFeedback, fetchReport } from "../api";
import { apiErrorMessage } from "../api/client";
import type { Feedback, Report } from "../api/types";

const recommendationColors: Record<string, string> = {
  hire: "bg-emerald-100 text-emerald-700",
  maybe: "bg-amber-100 text-amber-700",
  reject: "bg-red-100 text-red-700",
};

export default function ResultPage() {
  const { sessionId } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    Promise.all([fetchReport(Number(sessionId)), fetchFeedback(Number(sessionId))])
      .then(([r, f]) => {
        if (active) {
          setReport(r);
          setFeedback(f);
        }
      })
      .catch((err) => {
        if (active) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  if (loading) return <p className="text-slate-500">Loading report…</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!report || !feedback) return <p className="text-slate-500">Report unavailable for this session.</p>;

  const radar = Array.isArray(report.radar_data) ? report.radar_data : [];
  const timeline = Array.isArray(report.timeline_data) ? report.timeline_data : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Interview results</h1>
          <p className="text-slate-500">Session #{sessionId}</p>
        </div>
        <div className="flex gap-2">
          <Link to="/monitor" className="btn-secondary">Integrity report</Link>
          <Link to="/interview" className="btn-primary">New interview</Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card">
          <p className="text-sm text-slate-500">Overall score</p>
          <p className="text-3xl font-bold text-indigo-700">{String(report.metrics?.overall_score ?? "—")}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Recommendation</p>
          <span className={`mt-1 inline-block rounded-full px-3 py-1 text-sm font-medium capitalize ${recommendationColors[report.recommendation] ?? "bg-slate-100"}`}>
            {report.recommendation}
          </span>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Questions answered</p>
          <p className="text-3xl font-bold text-slate-700">{String(report.metrics?.total_questions ?? "—")}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 text-lg font-semibold">Skill breakdown</h2>
          {radar.length > 0 ? (
            <RadarChart data={radar as { skill: string; score: number }[]} />
          ) : (
            <p className="text-sm text-slate-500">No skill data.</p>
          )}
        </div>
        <div className="card">
          <h2 className="mb-2 text-lg font-semibold">Score timeline</h2>
          {timeline.length > 0 ? (
            <TimelineChart data={timeline as { index: number; score: number; difficulty: string; type: string }[]} />
          ) : (
            <p className="text-sm text-slate-500">No timeline data.</p>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="mb-2 text-lg font-semibold">Feedback summary</h2>
        <p className="text-sm text-slate-700">{feedback.summary}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 text-lg font-semibold text-emerald-700">Strengths</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
            {report.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2 className="mb-2 text-lg font-semibold text-amber-700">Areas to improve</h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
            {report.weaknesses.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">Recruiter summary</h2>
        <p className="text-sm text-slate-700">{report.recruiter_summary}</p>
      </div>

      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">Suggested next steps</h2>
        <ul className="space-y-2 text-sm text-slate-700">
          {report.suggestions.map((s, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-indigo-600">{i + 1}.</span>
              {s}
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2 className="mb-3 text-lg font-semibold">Learning resources</h2>
        <ul className="space-y-2 text-sm">
          {report.learning_resources.map((r, i) => (
            <li key={i} className="flex items-center justify-between gap-3">
              <span className="text-slate-700">{r.topic}</span>
              <a href={r.resource} target="_blank" rel="noreferrer" className="font-medium text-indigo-600 hover:underline">
                Open →
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function RadarChart({ data }: { data: { skill: string; score: number }[] }) {
  const size = 300;
  const center = size / 2;
  const radius = 110;
  const n = data.length;
  const points = data.map((d, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const value = Math.max(0, Math.min(100, d.score)) / 100;
    return {
      x: center + radius * value * Math.cos(angle),
      y: center + radius * value * Math.sin(angle),
    };
  });
  const polygon = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="mx-auto w-full max-w-sm">
      {[0.25, 0.5, 0.75, 1].map((level) => {
        const ring = data.map((_, i) => {
          const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
          return `${(center + radius * level * Math.cos(angle)).toFixed(1)},${(center + radius * level * Math.sin(angle)).toFixed(1)}`;
        });
        return <polygon key={level} points={ring.join(" ")} fill="none" stroke="#e2e8f0" />;
      })}
      {data.map((_, i) => {
        const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={center + radius * Math.cos(angle)}
            y2={center + radius * Math.sin(angle)}
            stroke="#e2e8f0"
          />
        );
      })}
      <polygon points={polygon} fill="rgba(79,70,229,0.25)" stroke="#4f46e5" strokeWidth={2} />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={4} fill="#4f46e5" />
          <text x={center + (radius + 24) * Math.cos((Math.PI * 2 * i) / n - Math.PI / 2)} y={center + (radius + 24) * Math.sin((Math.PI * 2 * i) / n - Math.PI / 2) + 4} textAnchor="middle" fontSize="11" fill="#475569">
            {data[i].skill}
          </text>
        </g>
      ))}
    </svg>
  );
}

function TimelineChart({ data }: { data: { index: number; score: number; difficulty: string; type: string }[] }) {
  const width = 360;
  const height = 160;
  const max = 100;
  const pts = data.map((d, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * width;
    const y = height - (Math.max(0, Math.min(max, d.score)) / max) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={0} y1={height - (v / max) * height} x2={width} y2={height - (v / max) * height} stroke="#e2e8f0" strokeDasharray="4 4" />
          <text x={4} y={height - (v / max) * height - 3} fontSize="10" fill="#94a3b8">
            {v}
          </text>
        </g>
      ))}
      {pts.length > 1 && <polyline points={pts.join(" ")} fill="none" stroke="#4f46e5" strokeWidth={2} />}
      {pts.map((p, i) => {
        const [x, y] = p.split(",").map(Number);
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={4} fill="#4f46e5" />
            <text x={x} y={y - 8} textAnchor="middle" fontSize="10" fill="#475569">
              {data[i].score}
            </text>
          </g>
        );
      })}
    </svg>
  );
}