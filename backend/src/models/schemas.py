"""
Pydantic models for API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class StudentRole(str, Enum):
    STUDENT = "student"
    MONITOR = "monitor"
    PHD = "phd"


class AssignmentType(str, Enum):
    BASIC = "basic"
    COURSEWORK = "coursework"
    THESIS = "thesis"
    ARTICLE = "article"
    PROJECT = "project"
    PHD_DISSERTATION = "phd_dissertation"
    PHD_ARTICLE = "phd_article"
    PHD_ESSAY = "phd_essay"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FORM_REVIEWED = "form_reviewed"
    CONTENT_REVIEWED = "content_reviewed"
    APPROVED = "approved"
    REVISION_NEEDED = "revision_needed"
    REJECTED = "rejected"


class ArtifactType(str, Enum):
    FILE = "file"
    URL = "url"
    MIXED = "mixed"


# =============================================================================
# STUDENT SCHEMAS
# =============================================================================

class StudentBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=500)
    group_name: Optional[str] = None
    notes: Optional[str] = None
    role: StudentRole = StudentRole.STUDENT


class StudentCreate(StudentBase):
    telegram_id: int
    telegram_username: Optional[str] = None


class StudentUpdate(BaseModel):
    display_name: Optional[str] = None
    group_name: Optional[str] = None
    notes: Optional[str] = None
    role: Optional[StudentRole] = None
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    id: str
    telegram_id: int
    telegram_username: Optional[str]
    is_active: bool
    created_at: datetime
    last_interaction_at: Optional[datetime]

    class Config:
        from_attributes = True


class StudentWithSubmissions(StudentResponse):
    active_submissions: List["SubmissionBrief"] = []
    total_submissions: int = 0


# =============================================================================
# SUBMISSION SCHEMAS
# =============================================================================

class Stage(BaseModel):
    stage: str
    name: str
    deadline_days: Optional[int] = None


class SubmissionBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class SubmissionCreate(SubmissionBase):
    student_id: str
    assignment_type: AssignmentType
    base_deadline: Optional[date] = None


class SubmissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    current_stage: Optional[str] = None
    status: Optional[SubmissionStatus] = None
    base_deadline: Optional[date] = None
    extended_deadline: Optional[date] = None
    grade: Optional[int] = None


class SubmissionBrief(BaseModel):
    id: str
    title: Optional[str]
    current_stage: str
    status: SubmissionStatus
    actual_deadline: Optional[date]

    class Config:
        from_attributes = True


class SubmissionResponse(SubmissionBase):
    id: str
    student_id: str
    assignment_type: AssignmentType
    current_stage: str
    status: SubmissionStatus
    base_deadline: Optional[date]
    extended_deadline: Optional[date]
    actual_deadline: Optional[date]
    artifact_url: Optional[str]
    artifact_type: Optional[ArtifactType]
    grade: Optional[int]
    grade_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubmissionWithDetails(SubmissionResponse):
    student: StudentResponse
    files: List["FileResponse"] = []
    reviews: List["ReviewResponse"] = []


# =============================================================================
# FILE SCHEMAS
# =============================================================================

class FileBase(BaseModel):
    original_filename: str
    stage: str


class FileCreate(FileBase):
    submission_id: str


class FileResponse(FileBase):
    id: str
    submission_id: str
    storage_path: str
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    checksum_sha256: str
    version_number: int
    previous_version_id: Optional[str]
    uploaded_by_telegram_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    checksum: str
    message: str


# =============================================================================
# REVIEW SCHEMAS
# =============================================================================

class ReviewBase(BaseModel):
    review_type: str
    stage: Optional[str] = None
    comment: Optional[str] = None
    grade: Optional[int] = None


class ReviewCreate(ReviewBase):
    submission_id: str
    file_id: Optional[str] = None
    status: SubmissionStatus


class ReviewResponse(ReviewBase):
    id: str
    submission_id: str
    file_id: Optional[str]
    status: SubmissionStatus
    signature_attached: bool
    signed_at: Optional[datetime]
    ai_analysis: Optional[Dict[str, Any]]
    created_at: datetime
    created_by_telegram_id: int

    class Config:
        from_attributes = True


class AIAnalysisRequest(BaseModel):
    file_id: str
    analysis_type: str = "full"  # "full", "ai_detection", "quality"
    options: Optional[Dict[str, Any]] = None


class AIAnalysisResponse(BaseModel):
    file_id: str
    ai_generated_probability: float
    quality_score: float
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    summary: str


# =============================================================================
# NOTIFICATION SCHEMAS
# =============================================================================

class NotificationTemplateBase(BaseModel):
    name: str
    template: str
    notification_type: str


class NotificationTemplateCreate(NotificationTemplateBase):
    code: str


class MassNotificationRequest(BaseModel):
    template_code: Optional[str] = None
    custom_message: Optional[str] = None
    filter_criteria: Dict[str, Any] = Field(default_factory=dict)
    # Примеры фильтров:
    # {"assignment_type": "coursework", "stage": "structure", "deadline_within_days": 3}


class NotificationResponse(BaseModel):
    id: str
    student_id: Optional[str]
    submission_id: Optional[str]
    notification_type: str
    subject: Optional[str]
    body: str
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# WORKLOAD & DASHBOARD SCHEMAS
# =============================================================================

class DeadlineStatus(BaseModel):
    overdue: int
    today: int
    soon: int  # 1-3 days
    normal: int
    total: int


class WorkloadStats(BaseModel):
    pending_review: int
    submitted_today: int
    deadline_this_week: int
    by_assignment_type: Dict[str, int]
    by_status: Dict[str, int]


class DashboardResponse(BaseModel):
    workload: WorkloadStats
    deadlines: DeadlineStatus
    recent_submissions: List[SubmissionWithDetails]
    upcoming_deadlines: List[SubmissionWithDetails]


# =============================================================================
# TELEGRAM WEBHOOK SCHEMAS
# =============================================================================

class TelegramMessage(BaseModel):
    message_id: int
    from_user: Dict[str, Any]
    chat: Dict[str, Any]
    date: int
    text: Optional[str] = None
    document: Optional[Dict[str, Any]] = None
    photo: Optional[List[Dict[str, Any]]] = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    edited_message: Optional[TelegramMessage] = None
    callback_query: Optional[Dict[str, Any]] = None


# Обновляем forward references
StudentWithSubmissions.model_rebuild()
SubmissionWithDetails.model_rebuild()
