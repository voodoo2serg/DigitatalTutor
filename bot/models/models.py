"""
DigitalTutor Bot - Models
Модели базы данных
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """Пользователь (студент)"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    telegram_id = Column(BigInteger, unique=True, index=True)
    telegram_username = Column(String(255))
    full_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    role = Column(String(50), default='Студент')
    group_name = Column(String(50))
    course = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    yandex_folder = Column(String(500))
    
    works = relationship("StudentWork", back_populates="student", lazy="selectin")


class WorkType(Base):
    """Тип работы"""
    __tablename__ = "work_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    gost_requirements = Column(Text)
    max_volume_pages = Column(Integer)
    min_volume_pages = Column(Integer)
    deadline_days = Column(Integer)
    requires_ai_check = Column(Boolean, default=True)
    
    works = relationship("StudentWork", back_populates="work_type")


class StudentWork(Base):
    """Работа студента"""
    __tablename__ = "student_works"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    work_type_id = Column(UUID(as_uuid=True), ForeignKey("work_types.id"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='submitted')
    
    ai_plagiarism_score = Column(Numeric(5, 2))
    ai_structure_score = Column(Numeric(5, 2))
    ai_formatting_score = Column(Numeric(5, 2))
    ai_analysis_json = Column(JSONB)
    
    teacher_comment = Column(Text)
    teacher_reviewed_at = Column(DateTime)
    
    # TICKET-3.1: Grading fields
    grade_classic = Column(Integer)  # 1-5
    grade_100 = Column(Integer)      # 0-100
    grade_letter = Column(String(2))   # A, B, C, D, E
    grade_comment = Column(Text)
    is_archived = Column(Boolean, default=False)
    graded_at = Column(DateTime)
    
    # Antiplagiarism
    antiplag_system = Column(String(100))
    antiplag_originality_percent = Column(Numeric(5, 2))
    antiplag_report_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime)
    deadline = Column(DateTime)
    
    student = relationship("User", back_populates="works")
    work_type = relationship("WorkType", back_populates="works")
    files = relationship("File", back_populates="work", lazy="selectin")
    communications = relationship("Communication", back_populates="work")


class File(Base):
    """Файл работы"""
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id"), index=True)
    milestone_submission_id = Column(UUID(as_uuid=True), ForeignKey("milestone_submissions.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    mime_type = Column(String(100))
    size_bytes = Column(BigInteger)
    storage_type = Column(String(20), default='yandex')
    storage_path = Column(String(500))
    storage_bucket = Column(String(100))
    yandex_file_path = Column(String(500))
    ai_extracted_text = Column(Text)
    ai_analysis_status = Column(String(50), default='pending')
    ai_analysis_result = Column(JSONB)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="files")


class Communication(Base):
    """Коммуникация (сообщения)"""
    __tablename__ = "communications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id"), nullable=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    channel = Column(String(20), default='telegram')
    message_type = Column(String(20), default='text')
    content = Column(Text)
    message = Column(Text)
    content_transcription = Column(Text)
    telegram_message_id = Column(BigInteger)
    telegram_chat_id = Column(BigInteger)
    from_student = Column(Boolean, default=True)
    from_teacher = Column(Boolean, default=False)
    attachment_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="communications")


class AIProvider(Base):
    """Настройки AI-провайдеров"""
    __tablename__ = "ai_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_name = Column(String(50), unique=True, nullable=False)
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(255))
    default_model = Column(String(100), default="openai/gpt-4o-mini")
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIAnalysisLog(Base):
    """История AI-анализов"""
    __tablename__ = "ai_analysis_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id", ondelete="CASCADE"))
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"))
    provider_used = Column(String(50))
    model_used = Column(String(100))
    prompt_sent = Column(Text)
    response_received = Column(Text)
    analysis_result = Column(JSONB)
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebAuthCode(Base):
    """Коды для веб-доступа (QR-коды, одноразовые коды)"""
    __tablename__ = "web_auth_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    generated_by = Column(String(50), default='admin')  # 'admin' or 'bot'
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageTemplate(Base):
    """Шаблоны сообщений"""
    __tablename__ = "message_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    trigger_event = Column(String(50))
    subject_template = Column(Text)
    body_template = Column(Text, nullable=False)
    variables = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Milestone(Base):
    """Этап работы (deadline milestone)"""
    __tablename__ = "milestones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_type_id = Column(UUID(as_uuid=True), ForeignKey("work_types.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    order_number = Column(Integer, nullable=False)
    weight_percent = Column(Integer, default=0)
    deadline_offset_days = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class MilestoneSubmission(Base):
    """Сдача этапа работы"""
    __tablename__ = "milestone_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id", ondelete="CASCADE"))
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"))
    status = Column(String(50), default="pending")  # pending, submitted, approved, revision_required
    student_comment = Column(Text)
    teacher_feedback = Column(Text)
    submitted_files = Column(JSONB)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

