-- Migration: Add grading fields to student_works table
-- TICKET-3.1: Three-component grading system
-- TICKET-3.2: Auto-archiving

-- Add grading columns
ALTER TABLE student_works 
ADD COLUMN IF NOT EXISTS grade_classic INTEGER CHECK (grade_classic BETWEEN 1 AND 5),
ADD COLUMN IF NOT EXISTS grade_100 INTEGER CHECK (grade_100 BETWEEN 0 AND 100),
ADD COLUMN IF NOT EXISTS grade_letter VARCHAR(1) CHECK (grade_letter IN ('A', 'B', 'C', 'D', 'E')),
ADD COLUMN IF NOT EXISTS grade_comment TEXT,
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS graded_at TIMESTAMP;

-- Create index for archived filter
CREATE INDEX IF NOT EXISTS idx_student_works_archived ON student_works(is_archived);
CREATE INDEX IF NOT EXISTS idx_student_works_status_archived ON student_works(status, is_archived);

-- Update comment on table
COMMENT ON COLUMN student_works.grade_classic IS 'Классическая оценка 1-5';
COMMENT ON COLUMN student_works.grade_100 IS '100-бальная оценка 0-100';
COMMENT ON COLUMN student_works.grade_letter IS 'Буквенная оценка A-E';
COMMENT ON COLUMN student_works.grade_comment IS 'Комментарий к оценке';
COMMENT ON COLUMN student_works.is_archived IS 'Архивная работа (скрыта из активных списков)';
COMMENT ON COLUMN student_works.graded_at IS 'Дата и время выставления оценки';
