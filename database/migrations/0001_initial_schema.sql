-- ============================================================
-- IntelliVue v2.0 - MySQL Schema
-- Tables: Users, Resumes, Interview Sessions, Questions, Answers,
--         Feedback, Reports, Skills, Domains, Achievements,
--         Warnings, Camera Logs, Eye Tracking, Activity Logs, Analytics
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 1. USERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('user', 'recruiter', 'admin') NOT NULL DEFAULT 'user',
    avatar_url      VARCHAR(500) NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 2. RESUMES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resumes (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    file_path       VARCHAR(500) NOT NULL,
    original_name   VARCHAR(255) NOT NULL,
    file_size       BIGINT NOT NULL DEFAULT 0,
    parsed_text     LONGTEXT NULL,
    parsed_json     JSON NULL,
    skills          JSON NULL,
    projects        JSON NULL,
    education       JSON NULL,
    certifications  JSON NULL,
    experience      JSON NULL,
    technologies    JSON NULL,
    strengths       JSON NULL,
    weaknesses      JSON NULL,
    ats_score       INT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resumes_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_resumes_user (user_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3. DOMAINS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS domains (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120) NOT NULL UNIQUE,
    category        VARCHAR(80) NOT NULL,
    description     TEXT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_domains_category (category)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. SKILLS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120) NOT NULL UNIQUE,
    category        VARCHAR(80) NULL,
    aliases         JSON NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 5. INTERVIEW SESSIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_sessions (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    resume_id       BIGINT UNSIGNED NULL,
    domain_id       BIGINT UNSIGNED NULL,
    mode            ENUM('resume', 'domain') NOT NULL DEFAULT 'resume',
    difficulty      ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium',
    status          ENUM('pending', 'in_progress', 'completed', 'aborted') NOT NULL DEFAULT 'pending',
    current_question_index INT NOT NULL DEFAULT 0,
    total_questions INT NOT NULL DEFAULT 0,
    overall_score   DECIMAL(5, 2) NULL,
    integrity_score DECIMAL(5, 2) NULL,
    started_at      TIMESTAMP NULL,
    ended_at        TIMESTAMP NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_sessions_resume FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE SET NULL,
    CONSTRAINT fk_sessions_domain FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE SET NULL,
    INDEX idx_sessions_user (user_id),
    INDEX idx_sessions_status (status)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 6. QUESTIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    domain_id       BIGINT UNSIGNED NULL,
    session_id      BIGINT UNSIGNED NULL,
    question_type   ENUM('mcq', 'coding', 'theory', 'scenario', 'rapid_fire') NOT NULL DEFAULT 'theory',
    difficulty      ENUM('easy', 'medium', 'hard') NOT NULL DEFAULT 'medium',
    text            TEXT NOT NULL,
    options         JSON NULL,
    correct_answer  TEXT NULL,
    skill_tags      JSON NULL,
    is_ai_generated BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_questions_domain FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE SET NULL,
    CONSTRAINT fk_questions_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_questions_domain (domain_id),
    INDEX idx_questions_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 7. ANSWERS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS answers (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    question_id     BIGINT UNSIGNED NOT NULL,
    answer_text     LONGTEXT NULL,
    selected_option VARCHAR(20) NULL,
    code_submitted  LONGTEXT NULL,
    time_taken_sec  INT NOT NULL DEFAULT 0,
    ai_score        DECIMAL(5, 2) NULL,
    ai_feedback     TEXT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_answers_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_answers_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    UNIQUE KEY uq_answers_session_question (session_id, question_id),
    INDEX idx_answers_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 8. FEEDBACK
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    metrics         JSON NULL,
    overall_score   DECIMAL(5, 2) NULL,
    recommendation  ENUM('hire', 'maybe', 'reject') NULL,
    summary         TEXT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedback_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_feedback_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 9. REPORTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    radar_data      JSON NULL,
    heatmap_data    JSON NULL,
    timeline_data   JSON NULL,
    strengths       JSON NULL,
    weaknesses      JSON NULL,
    suggestions     JSON NULL,
    learning_resources JSON NULL,
    recruiter_summary TEXT NULL,
    full_report     JSON NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reports_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_reports_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 10. ACHIEVEMENTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    title           VARCHAR(255) NOT NULL,
    description     TEXT NULL,
    badge           VARCHAR(120) NULL,
    earned_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_achievements_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_achievements_user (user_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 11. WARNINGS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS warnings (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    warning_type    VARCHAR(80) NOT NULL,
    severity        ENUM('low', 'medium', 'high') NOT NULL DEFAULT 'medium',
    message         VARCHAR(500) NULL,
    occurred_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_warnings_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_warnings_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 12. CAMERA LOGS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS camera_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    face_detected   BOOLEAN NOT NULL DEFAULT FALSE,
    face_count      INT NOT NULL DEFAULT 0,
    attention_score DECIMAL(5, 2) NULL,
    eye_contact     BOOLEAN NULL,
    looking_away    BOOLEAN NULL,
    head_movement   DECIMAL(5, 2) NULL,
    drowsy          BOOLEAN NOT NULL DEFAULT FALSE,
    smile_detected  BOOLEAN NOT NULL DEFAULT FALSE,
    confidence      DECIMAL(5, 2) NULL,
    CONSTRAINT fk_camera_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_camera_session_time (session_id, timestamp)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 13. EYE TRACKING
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS eye_tracking (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    timestamp       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    gaze_x          FLOAT NULL,
    gaze_y          FLOAT NULL,
    eye_contact     BOOLEAN NOT NULL DEFAULT FALSE,
    blink_rate      DECIMAL(5, 2) NULL,
    CONSTRAINT fk_eye_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_eye_session_time (session_id, timestamp)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 14. ACTIVITY LOGS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT UNSIGNED NOT NULL,
    event_type      VARCHAR(80) NOT NULL,
    event_data      JSON NULL,
    severity        ENUM('info', 'warning', 'critical') NOT NULL DEFAULT 'info',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    INDEX idx_activity_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 15. ANALYTICS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         BIGINT UNSIGNED NOT NULL,
    session_id      BIGINT UNSIGNED NULL,
    metric_name     VARCHAR(120) NOT NULL,
    metric_value    DECIMAL(10, 2) NULL,
    metric_data     JSON NULL,
    recorded_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_analytics_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_analytics_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE SET NULL,
    INDEX idx_analytics_user_metric (user_id, metric_name),
    INDEX idx_analytics_session (session_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
