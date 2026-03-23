import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, Text, Numeric, ForeignKey, JSON
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
    ai_extracted_text = Column(Text)
    ai_analysis_status = Column(String(50), default='pending')
    ai_analysis_result = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="files")

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id"))
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel = Column(String(20), default='telegram')
    message_type = Column(String(20), default='text')
    content = Column(Text)
    content_transcription = Column(Text)
    telegram_message_id = Column(BigInteger)
    telegram_chat_id = Column(BigInteger)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    work = relationship("StudentWork", back_populates="communications")
