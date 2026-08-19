import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSessions, fetchVerdict } from "../api";
import { apiErrorMessage } from "../api/client";
import type { InterviewSession, MonitoringVerdict } from "../api/types";

const statusColors: Record<string, string> = {
  clean: "bg-emerald-100 text-emerald-700",
  suspicious: "bg-amber-100 text-amber-700",
  flagged: "bg-red-100 text-red-700",
};

export default function MonitorPage() {
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [verdicts, setVerdicts] = useState<Record<number, MonitoringVerdict>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetchSessions()
      .then(async (sessions) => {
        if (!active) return;
        setSessions(sessions);
        const entries = await Promise.all(
          sessions.slice(0, 10).map(async (s) => {
            try {
              const v = await fetchVerdict(s.id);
              return [s.id, v] as const;
            } catch {
              return [s.id, null] as const;
            }
          })
        );
        if (active) {
          setVerdicts(Object.fromEntries(entries.filter((e): e is readonly [number, MonitoringVerdict] => e[1] !== null)));
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
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Integrity monitoring</h1>
        <p className="text-slate-500">
          Anti-cheating risk scores and warning summaries for your interviews.
        </p>
      </div>

      {loading && <p className="text-slate-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && sessions.length === 0 && (
        <div className="card">
          <p className="text-slate-500">No interviews yet — monitoring data will appear here.</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {sessions.slice(0, 10).map((s) => {
          const v = verdicts[s.id];
          return (
            <div key={s.id} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold">Session #{s.id}</p>
                  <p className="text-xs text-slate-400">
                    {s.mode} · {s.difficulty} · {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </div>
                {v ? (
                  <span className={`rounded-full px-3 py-1 text-xs font-medium uppercase ${statusColors[v.status] ?? "bg-slate-100"}`}>
                    {v.status}
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500">no data</span>
                )}
              </div>
              {v && (
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-slate-500">Risk score</span>
                    <span className="font-semibold">{v.risk_score}/100</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className={`h-full ${v.status === "flagged" ? "bg-red-500" : v.status === "suspicious" ? "bg-amber-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(100, v.risk_score)}%` }}
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                      {v.warning_count} warnings
                    </span>
                    {v.warning_types.map((t) => (
                      <span key={t} className="rounded-full bg-red-50 px-2 py-0.5 text-red-600">
                        {t}
                      </span>
                    ))}
                  </div>
                  <Link to={`/result/${s.id}`} className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:underline">
                    View report →
                  </Link>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}