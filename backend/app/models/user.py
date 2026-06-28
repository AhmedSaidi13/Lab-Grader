from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin   = "admin"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(64),  unique=True, nullable=False, index=True)
    email           = Column(String(128), unique=True, nullable=False, index=True)
    full_name       = Column(String(256), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role            = Column(SAEnum(UserRole), default=UserRole.student, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    avatar_path     = Column(String(512), nullable=True)   # ← NEW
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    submissions = relationship("Submission", back_populates="student", lazy="select")
    assignments = relationship("Assignment", back_populates="created_by", lazy="select")