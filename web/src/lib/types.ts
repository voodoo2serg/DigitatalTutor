/**
 * DigitalTutor Web Interface — Type Definitions
 */

// ==================== User ====================
export interface User {
  id: string;
  telegram_id: number;
  telegram_username?: string;
  full_name: string;
  email?: string;
  phone?: string;
  role: string;
  group_name?: string;
  course?: number;
  is_active: boolean;
  yandex_folder?: string;
  created_at: string;
}

// ==================== Work ====================
export interface WorkType {
  id: string;
  code: string;
  name: string;
  description?: string;
  gost_requirements?: string;
  max_volume_pages?: number;
  min_volume_pages?: number;
  deadline_days?: number;
  requires_ai_check: boolean;
}

export interface StudentWork {
  id: string;
  student_id: string;
  work_type_id?: string;
  title: string;
  description?: string;
  status: WorkStatus;
  work_type?: WorkType;
  student?: User;

  // AI scores (VISIBLE ONLY TO ADMIN)
  ai_plagiarism_score?: number;
  ai_structure_score?: number;
  ai_formatting_score?: number;
  ai_analysis_json?: Record<string, unknown>;

  // Teacher review
  teacher_comment?: string;
  teacher_reviewed_at?: string;

  // Antiplagiarism (VISIBLE ONLY TO ADMIN)
  antiplag_system?: string;
  antiplag_originality_percent?: number;
  antiplag_report_url?: string;

  // Grading
  grade_classic?: number;
  grade_100?: number;
  grade_letter?: string;
  grade_comment?: string;
  is_archived: boolean;
  graded_at?: string;

  created_at: string;
  updated_at: string;
  submitted_at?: string;
  deadline?: string;

  // Relations
  files?: FileRecord[];
  communications?: Communication[];
}

export type WorkStatus =
  | 'draft'
  | 'submitted'
  | 'in_review'
  | 'revision_required'
  | 'accepted'
  | 'rejected'
  | 'graded';

// ==================== File ====================
export interface FileRecord {
  id: string;
  work_id: string;
  filename: string;
  original_name: string;
  mime_type?: string;
  size_bytes?: number;
  storage_type: string;
  storage_path?: string;
  yandex_file_path?: string;
  created_at: string;
}

// ==================== Communication ====================
export interface Communication {
  id: string;
  work_id?: string;
  student_id?: string;
  from_user_id?: string;
  to_user_id?: string;
  channel: 'telegram' | 'web' | 'email';
  message_type: 'text' | 'voice' | 'file' | 'system';
  content?: string;
  content_transcription?: string;
  from_student?: boolean;
  from_teacher?: boolean;
  is_read: boolean;
  created_at: string;
  from_user?: User;
  to_user?: User;
  attachment_file?: FileRecord;
}

// ==================== Auth ====================
export type AuthRole = 'student' | 'admin';

export interface AuthState {
  isAuthenticated: boolean;
  role: AuthRole | null;
  user: User | null;
  token: string | null;
  sessionExpiresAt: number | null;
}

export interface LoginRequest {
  code: string;
}

export interface AdminLoginRequest {
  masterCode: string;
}

export interface LoginResponse {
  success: boolean;
  token?: string;
  user?: User;
  error?: string;
}

// ==================== QR Code ====================
export interface QRCodeData {
  code: string;
  student_id: string;
  student_name: string;
  expires_at: string;
}

// ==================== File Explorer ====================
export interface FileTreeNode {
  name: string;
  path: string;
  type: 'folder' | 'file';
  children?: FileTreeNode[];
  file?: FileRecord;
  size?: number;
  modified?: string;
}

// ==================== App View ====================
export type AppView =
  | 'landing'
  | 'student-login'
  | 'admin-login'
  | 'student-dashboard'
  | 'admin-dashboard';

export type StudentTab = 'works' | 'archive' | 'files' | 'help';
export type AdminTab = 'students' | 'works' | 'files' | 'ai' | 'qr-codes' | 'settings';
