import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSessions } from "../api";
import { apiErrorMessage } from "../api/client";
import type { InterviewSession } from "../api/types";
import { useAuth } from "../context/AuthContext";

const statusColors: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  in_progress: "bg-amber-100 text-amber-700",
  completed: "bg-emerald-100 text-emerald-700",
  aborted: "bg-red-100 text-red-700",
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchSessions()
      .then((data) => {
        if (active) setSessions(data);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Welcome back, {user?.name}</h1>
          <p className="text-slate-500">Run an interview, review your reports, or monitor integrity.</p>
        </div>
        <Link to="/interview" className="btn-primary">
          New Interview
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link to="/resume" className="card hover:border-indigo-300">
          <h3 className="font-semibold text-indigo-700">Upload resume</h3>
          <p className="text-sm text-slate-500">Parse your PDF and get an ATS score.</p>
        </Link>
        <Link to="/interview" className="card hover:border-indigo-300">
          <h3 className="font-semibold text-indigo-700">Start interview</h3>
          <p className="text-sm text-slate-500">Adaptive AI questions across 31 domains.</p>
        </Link>
        <Link to="/monitor" className="card hover:border-indigo-300">
          <h3 className="font-semibold text-indigo-700">Monitoring</h3>
          <p className="text-sm text-slate-500">Anti-cheating verdicts and risk scores.</p>
        </Link>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold">Recent interviews</h2>
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && sessions.length === 0 && (
          <p className="text-sm text-slate-500">No interviews yet — start your first one.</p>
        )}
        {sessions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">ID</th>
                  <th className="py-2 pr-4">Mode</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Difficulty</th>
                  <th className="py-2 pr-4">Progress</th>
                  <th className="py-2 pr-4">Score</th>
                  <th className="py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id} className="border-b last:border-0">
                    <td className="py-2 pr-4">#{s.id}</td>
                    <td className="py-2 pr-4 capitalize">{s.mode}</td>
                    <td className="py-2 pr-4">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${statusColors[s.status] ?? "bg-slate-100"}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 capitalize">{s.difficulty}</td>
                    <td className="py-2 pr-4">
                      {s.current_question_index}/{s.total_questions}
                    </td>
                    <td className="py-2 pr-4">{s.overall_score ?? "—"}</td>
                    <td className="py-2">{new Date(s.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}