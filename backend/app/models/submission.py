from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, ForeignKey, JSON, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class SubmissionStatus(str, enum.Enum):
    pending      = "pending"
    queued       = "queued"
    compiling    = "compiling"
    running      = "running"
    evaluating   = "evaluating"
    completed    = "completed"
    failed       = "failed"
    compile_error= "compile_error"
    timeout      = "timeout"


class Submission(Base):
    __tablename__ = "submissions"

    id              = Column(Integer, primary_key=True, index=True)

    # Relations
    student_id      = Column(Integer, ForeignKey("users.id"),    nullable=False)
    assignment_id   = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student         = relationship("User", back_populates="submissions")
    assignment      = relationship("Assignment", back_populates="submissions")

    # Files — JSON list of {path, original_filename}
    # For single-file assignments: list of 1 item
    # For multi-file assignments:  list of N items
    files           = Column(JSON, default=list, nullable=False)

    # Keep these for backwards compat (populated from files[0])
    file_path           = Column(String(512), nullable=True)
    original_filename   = Column(String(256), nullable=True)

    # Status
    status          = Column(SAEnum(SubmissionStatus), default=SubmissionStatus.pending)
    is_late         = Column(Boolean, default=False)
    version         = Column(Integer, default=1, nullable=False)  # increments on replace

    # Results
    score           = Column(Float, nullable=True)
    compile_output  = Column(Text, nullable=True)
    test_results    = Column(JSON, default=list)
    static_analysis = Column(JSON, default=dict)
    feedback        = Column(Text, nullable=True)
    celery_task_id  = Column(String(256), nullable=True)

    # Timestamps
    submitted_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    evaluated_at    = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (f"<Submission id={self.id} student={self.student_id} "
                f"status={self.status} v{self.version}>")