import uuid
from datetime import datetime
from sqlalchemy import DECIMAL, Column, String, DateTime, Boolean, Integer, BigInteger, Text, Numeric, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True)
    telegram_username = Column(String(255))
    full_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    role = Column(String(20), default='student')
    group_name = Column(String(50))
    course = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    works = relationship("StudentWork", back_populates="student")

class WorkType(Base):
    __tablename__ = "work_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    gost_requirements = Column(Text)
    max_volume_pages = Column(Integer)
    min_volume_pages = Column(Integer)
    deadline_days = Column(Integer)
    requires_ai_check = Column(Boolean, default=True)

class StudentWork(Base):
    __tablename__ = "student_works"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    work_type_id = Column(UUID(as_uuid=True), ForeignKey("work_types.id"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='draft')
    
    ai_plagiarism_score = Column(Numeric(5, 2))
    ai_structure_score = Column(Numeric(5, 2))
    ai_formatting_score = Column(Numeric(5, 2))
    ai_analysis_json = Column(JSONB)
    
    teacher_comment = Column(Text)
    teacher_reviewed_at = Column(DateTime)
    
    # Antiplagiarism fields
    antiplag_system = Column(String(50))
    antiplag_originality_percent = Column(Numeric(5, 2))
    antiplag_report_url = Column(String(500))
    
    # AI Analysis tracking
    ai_provider = Column(String(50))
    analysis_started_at = Column(DateTime)
    
    # AI Generated Response for Student (Option B)
    ai_student_response = Column(JSONB)  # {greeting, strengths, weaknesses, recommendations, conclusion, full_text}
    ai_student_response_status = Column(String(50), default=None)  # pending_review, approved, sent
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime)
    deadline = Column(DateTime)
    
    student = relationship("User", back_populates="works")
    files = relationship("File", back_populates="work")
    communications = relationship("Communication", back_populates="work")

class File(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id"))
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    mime_type = Column(String(100))
    size_bytes = Column(BigInteger)
    storage_type = Column(String(20), default='minio')
    storage_path = Column(String(500))
    storage_bucket = Column(String(100))
    yandex_file_path = Column(String(500))  # Path on Yandex.Disk
    ai_extracted_text = Column(Text)
    ai_analysis_status = Column(String(50), default='pending')
    ai_analysis_result = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="files")

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel = Column(String(20), default='telegram')
    message_type = Column(String(20), default='text')
    message = Column(Text)  # Alias for content
    content = Column(Text)
    content_transcription = Column(Text)
    telegram_message_id = Column(BigInteger)
    telegram_chat_id = Column(BigInteger)
    from_student = Column(Boolean, default=True)
    from_teacher = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="communications")

class AISkillConfig(Base):
    """Конфигурация AI-провайдеров"""
    __tablename__ = "ai_skills_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_name = Column(String(100), nullable=False)
    provider_name = Column(String(50), nullable=False)
    model_name = Column(String(100))
    api_key_encrypted = Column(Text)
    config_json = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


# ============== AI SYSTEM MODELS ==============

class AIProvider(Base):
    __tablename__ = "ai_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name = Column(String(50), nullable=False, unique=True)
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(255))
    default_model = Column(String(100), default="openai/gpt-4o-mini")
    is_active = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIAnalysisLog(Base):
    __tablename__ = "ai_analysis_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id", ondelete="CASCADE"))
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"))
    provider_used = Column(String(50))
    model_used = Column(String(100))
    prompt_sent = Column(Text)
    response_received = Column(Text)
    analysis_result = Column(JSONB)
    tokens_used = Column(Integer)
    cost_usd = Column(DECIMAL(10, 6))
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # auto_response, bulk_mail, report, ai_check
    trigger_event = Column(String(50))  # on_submit, on_status_change, on_analysis_complete, manual
    subject_template = Column(Text)
    body_template = Column(Text, nullable=False)
    variables = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BulkMessage(Base):
    __tablename__ = "bulk_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    file_path = Column(String(500))
    recipient_type = Column(String(20))  # all, group, student
    recipient_filter = Column(String(255))
    sent_at = Column(DateTime, default=datetime.utcnow)
    recipient_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, sending, sent, failed


# ============== AI QUEUE MODELS ==============

class AIAnalysisQueue(Base):
    __tablename__ = "ai_analysis_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id", ondelete="CASCADE"))
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"))
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=5)
    analysis_types = Column(JSONB, default=list)
    text_content = Column(Text)
    result_antiplagiarism = Column(JSONB)
    result_structure = Column(JSONB)
    result_formatting = Column(JSONB)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processed_by = Column(String(100))


class AIProcessorHeartbeat(Base):
    __tablename__ = "ai_processor_heartbeat"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processor_id = Column(String(100), nullable=False)
    status = Column(String(20))
    last_processed_at = Column(DateTime)
    queue_size = Column(Integer)
    processed_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
