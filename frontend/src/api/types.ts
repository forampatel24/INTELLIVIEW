export interface User {
  id: number;
  name: string;
  email: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Domain {
  id: number;
  name: string;
  category: string;
  description: string | null;
  focus_skills: string[];
}

export interface Question {
  question_id: number;
  type: string;
  difficulty: string;
  text: string;
  options: string[] | null;
  skill_tags: string[];
}

export interface SessionState {
  session_id: number;
  mode: string;
  difficulty: string;
  status: string;
  current_index: number;
  total_questions: number;
  round_type: string;
  focus_skills: string[];
  average_score: number;
  last_score: number | null;
  is_complete: boolean;
}

export interface AnswerResult {
  score: number;
  feedback: string;
  next_difficulty: string;
  is_complete: boolean;
  overall_score: number | null;
  state: SessionState;
}

export interface Feedback {
  feedback_id: number;
  metrics: Record<string, unknown>;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  recommendation: "hire" | "maybe" | "reject";
  suggestions: string[];
}

export interface Report {
  report_id: number;
  session_id: number;
  recommendation: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  learning_resources: { topic: string; resource: string }[];
  recruiter_summary: string;
  radar_data: Record<string, unknown>;
  heatmap_data: Record<string, unknown>;
  timeline_data: Record<string, unknown>;
  metrics: Record<string, unknown>;
}

export interface ResumeSummary {
  resume_id: number;
  original_name: string;
  ats: { score: number; summary?: string };
  parsed: {
    skills: string[];
    projects: unknown[];
    education: unknown[];
    certifications: unknown[];
    experience: unknown[];
    technologies: string[];
    strengths: string[];
    weaknesses: string[];
  };
}

export interface ResumeListItem {
  id: number;
  original_name: string;
  ats_score: number;
  created_at: string;
}

export interface MonitoringVerdict {
  session_id: number;
  risk_score: number;
  status: "clean" | "suspicious" | "flagged";
  warning_count: number;
  warning_types: string[];
  severity_counts: { low: number; medium: number; high: number };
}

export interface MonitoringReport {
  session_id: number;
  verdict: MonitoringVerdict;
  camera_summary: Record<string, unknown>;
  warning_summary: Record<string, string | number>;
}

export interface InterviewSession {
  id: number;
  mode: string;
  difficulty: string;
  status: string;
  total_questions: number;
  current_question_index: number;
  overall_score: number | null;
  integrity_score: number | null;
  created_at: string;
}