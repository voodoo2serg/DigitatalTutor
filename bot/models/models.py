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
    message = Column(Text)
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
