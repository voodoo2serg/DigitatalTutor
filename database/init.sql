-- DigitalTutor Database Schema
-- Система управления учебными проектами

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS (Студенты и преподаватели)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE,
    telegram_username VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'admin')),
    group_name VARCHAR(50),
    course INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    yandex_folder VARCHAR(500)
);

-- ============================================
-- WORK_TYPES (Типы работ)
-- ============================================
CREATE TABLE work_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    gost_requirements TEXT,
    max_volume_pages INTEGER,
    min_volume_pages INTEGER,
    deadline_days INTEGER,
    requires_ai_check BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- MILESTONES (Этапы работы)
-- ============================================
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_type_id UUID REFERENCES work_types(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    order_number INTEGER NOT NULL,
    weight_percent INTEGER DEFAULT 0,
    deadline_offset_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- STUDENT_WORKS (Работы студентов)
-- ============================================
CREATE TABLE student_works (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES users(id) ON DELETE CASCADE,
    work_type_id UUID REFERENCES work_types(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'in_review', 'revision_required', 'accepted', 'rejected', 'graded')),
    current_milestone_id UUID,
    
    -- AI Analysis Results
    ai_plagiarism_score DECIMAL(5,2),
    ai_structure_score DECIMAL(5,2),
    ai_formatting_score DECIMAL(5,2),
    ai_analysis_json JSONB,
    
    -- Teacher Review
    teacher_comment TEXT,
    teacher_reviewed_at TIMESTAMP,
    
    -- Antiplagiarism
    antiplag_system VARCHAR(100),
    antiplag_report_url TEXT,
    antiplag_originality_percent DECIMAL(5,2),
    
    -- Grading fields
    grade_classic INTEGER,
    grade_100 INTEGER,
    grade_letter VARCHAR(2),
    grade_comment TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    graded_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    deadline TIMESTAMP
);

-- ============================================
-- MILESTONE_SUBMISSIONS (Сдачи этапов)
-- ============================================
CREATE TABLE milestone_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID REFERENCES student_works(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES milestones(id),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'approved', 'revision_required')),
    student_comment TEXT,
    teacher_feedback TEXT,
    submitted_files JSONB,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FILES (Файлы работ)
-- ============================================
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID REFERENCES student_works(id) ON DELETE CASCADE,
    milestone_submission_id UUID REFERENCES milestone_submissions(id),
    
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    
    -- Storage
    storage_type VARCHAR(20) DEFAULT 'minio' CHECK (storage_type IN ('minio', 'yandex_disk')),
    storage_path VARCHAR(500),
    storage_bucket VARCHAR(100),
    
    -- AI Processing
    ai_extracted_text TEXT,
    ai_analysis_status VARCHAR(50) DEFAULT 'pending',
    ai_analysis_result JSONB,
    
    -- Upload metadata
    uploaded_by UUID REFERENCES users(id),
    yandex_file_path VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- COMMUNICATIONS (История коммуникаций)
-- ============================================
CREATE TABLE communications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID REFERENCES student_works(id) ON DELETE CASCADE,
    
    from_user_id UUID REFERENCES users(id),
    to_user_id UUID REFERENCES users(id),
    
    channel VARCHAR(20) DEFAULT 'telegram' CHECK (channel IN ('telegram', 'web', 'email')),
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'voice', 'file', 'system')),
    
    content TEXT,
    content_transcription TEXT, -- для голосовых
    
    -- Telegram metadata
    telegram_message_id BIGINT,
    telegram_chat_id BIGINT,
    
    -- File attachment
    attachment_file_id UUID REFERENCES files(id),
    
    -- Student reference for filtering
    student_id UUID REFERENCES users(id),
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- DEADLINES (Дедлайны и напоминания)
-- ============================================
CREATE TABLE deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID REFERENCES student_works(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES milestones(id),
    
    title VARCHAR(255) NOT NULL,
    description TEXT,
    deadline_at TIMESTAMP NOT NULL,
    
    reminder_1day_sent BOOLEAN DEFAULT FALSE,
    reminder_3days_sent BOOLEAN DEFAULT FALSE,
    reminder_week_sent BOOLEAN DEFAULT FALSE,
    
    is_notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AI_SKILLS_CONFIG (Настройки AI-скиллов)
-- ============================================
CREATE TABLE ai_skills_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name VARCHAR(50) UNIQUE NOT NULL,
    skill_type VARCHAR(50) NOT NULL, -- 'plagiarism', 'structure', 'formatting'
    is_enabled BOOLEAN DEFAULT TRUE,
    model_name VARCHAR(100) DEFAULT 'gemma3:4b',
    prompt_template TEXT,
    weight_percent INTEGER DEFAULT 33,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- SYSTEM_LOGS (Логи системы)
-- ============================================
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,
    source VARCHAR(100),
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AI PROVIDERS (Настройки AI-провайдеров)
-- ============================================
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name VARCHAR(50) NOT NULL UNIQUE,
    api_key VARCHAR(500) NOT NULL,
    base_url VARCHAR(255),
    default_model VARCHAR(100) DEFAULT 'openai/gpt-4o-mini',
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AI ANALYSIS LOGS (История AI-анализов)
-- ============================================
CREATE TABLE ai_analysis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID REFERENCES student_works(id) ON DELETE CASCADE,
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    provider_used VARCHAR(50),
    model_used VARCHAR(100),
    prompt_sent TEXT,
    response_received TEXT,
    analysis_result JSONB,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- MESSAGE TEMPLATES (Шаблоны сообщений)
-- ============================================
CREATE TABLE message_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    trigger_event VARCHAR(50),
    subject_template TEXT,
    body_template TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_works_student ON student_works(student_id);
CREATE INDEX idx_works_status ON student_works(status);
CREATE INDEX idx_communications_work ON communications(work_id);
CREATE INDEX idx_files_work ON files(work_id);
CREATE INDEX idx_deadlines_work ON deadlines(work_id);
CREATE INDEX idx_milestones_work_type ON milestones(work_type_id);
CREATE INDEX idx_ai_providers_active ON ai_providers(is_active);
CREATE INDEX idx_ai_logs_work ON ai_analysis_logs(work_id);
CREATE INDEX idx_templates_category ON message_templates(category);

-- ============================================
-- DEFAULT DATA
-- ============================================

-- Work Types
INSERT INTO work_types (code, name, description, gost_requirements, max_volume_pages, min_volume_pages, deadline_days) VALUES
('coursework', 'Курсовая работа', 'Курсовая работа по дисциплине', 'ГОСТ 7.32-2017', 50, 25, 30),
('vkr_bachelor', 'ВКР (Бакалавр)', 'Выпускная квалификационная работа бакалавра', 'ГОСТ 7.32-2017', 100, 60, 90),
('vkr_master', 'ВКР (Магистр)', 'Выпускная квалификационная работа магистра', 'ГОСТ 7.32-2017', 120, 80, 120),
('article', 'Научная статья', 'Научная статья для публикации', 'Требования журнала', 20, 8, 60),
('essay', 'Реферат', 'Реферат по дисциплине', 'ГОСТ 7.32-2017', 20, 10, 14),
('project', 'Проект', 'Учебный проект', 'Требования курса', 50, 20, 45);

-- AI Skills
INSERT INTO ai_skills_config (skill_name, skill_type, model_name, prompt_template, weight_percent) VALUES
('antiplagiarism', 'plagiarism', 'gemma3:4b', 'Проанализируй текст на признаки плагиата и AI-генерации...', 40),
('structure', 'structure', 'gemma3:4b', 'Проанализируй структуру научной работы...', 30),
('formatting', 'formatting', 'gemma3:4b', 'Проверь соответствие оформления ГОСТ...', 30);
