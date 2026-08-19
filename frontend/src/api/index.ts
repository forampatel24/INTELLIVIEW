import { client } from "./client";
import type {
  AnswerResult,
  AuthResponse,
  Domain,
  Feedback,
  InterviewSession,
  MonitoringReport,
  MonitoringVerdict,
  Question,
  Report,
  ResumeListItem,
  ResumeSummary,
  SessionState,
  User,
} from "./types";

// --- Auth ---

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>("/auth/login", { email, password });
  return data;
}

export async function register(
  name: string,
  email: string,
  password: string,
  role = "user"
): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>("/auth/register", { name, email, password, role });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await client.get<User>("/auth/me");
  return data;
}

// --- Domains ---

export async function fetchDomains(category?: string): Promise<Domain[]> {
  const { data } = await client.get<Domain[]>("/domains", { params: { category } });
  return data;
}

export async function fetchCategories(): Promise<string[]> {
  const { data } = await client.get<string[]>("/domains/categories");
  return data;
}

// --- Resumes (phase 16: upload stores the file locally) ---

export async function uploadResume(file: File): Promise<ResumeSummary> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<ResumeSummary>("/resumes/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchResumes(): Promise<ResumeListItem[]> {
  const { data } = await client.get<ResumeListItem[]>("/resumes");
  return data;
}

export function resumeDownloadUrl(resumeId: number): string {
  return `/api/resumes/${resumeId}/download`;
}

// --- Interviews ---

export async function startInterview(params: {
  mode: "resume" | "domain";
  total_questions: number;
  resume_id?: number;
  domain_id?: number;
  round_type?: string;
}): Promise<{ session_id: number; state: SessionState; question: Question }> {
  const { data } = await client.post("/interviews/start", params);
  return data;
}

export async function fetchSessions(): Promise<InterviewSession[]> {
  const { data } = await client.get<InterviewSession[]>("/interviews");
  return data;
}

export async function fetchSessionState(sessionId: number): Promise<SessionState> {
  const { data } = await client.get<SessionState>(`/interviews/${sessionId}/state`);
  return data;
}

export async function fetchCurrentQuestion(sessionId: number): Promise<{ state: SessionState; question: Question }> {
  const { data } = await client.get(`/interviews/${sessionId}/question`);
  return data;
}

export async function submitAnswer(
  sessionId: number,
  payload: {
    answer_text?: string;
    selected_option?: string;
    code_submitted?: string;
    time_taken_sec?: number;
  }
): Promise<AnswerResult> {
  const { data } = await client.post<AnswerResult>(`/interviews/${sessionId}/answer`, payload);
  return data;
}

export async function generateFeedback(sessionId: number): Promise<Feedback> {
  const { data } = await client.post<Feedback>(`/interviews/${sessionId}/feedback`);
  return data;
}

export async function fetchFeedback(sessionId: number): Promise<Feedback> {
  const { data } = await client.get<Feedback>(`/interviews/${sessionId}/feedback`);
  return data;
}

export async function fetchReport(sessionId: number): Promise<Report> {
  const { data } = await client.get<Report>(`/interviews/${sessionId}/report`);
  return data;
}

export async function logCheatEvent(
  sessionId: number,
  event_type: string,
  event_data?: Record<string, unknown>
): Promise<{ accepted: boolean; warning: { warning_type: string; message: string; severity: string } | null }> {
  const { data } = await client.post(`/interviews/${sessionId}/events`, { event_type, event_data });
  return data;
}

// --- Monitoring (anti-cheating) ---

export async function fetchVerdict(sessionId: number): Promise<MonitoringVerdict> {
  const { data } = await client.get<MonitoringVerdict>(`/monitoring/${sessionId}`);
  return data;
}

export async function fetchMonitoringReport(sessionId: number): Promise<MonitoringReport> {
  const { data } = await client.get<MonitoringReport>(`/monitoring/${sessionId}/report`);
  return data;
}