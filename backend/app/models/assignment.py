from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Float, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id                     = Column(Integer, primary_key=True, index=True)
    title                  = Column(String(256), nullable=False)
    description            = Column(Text, nullable=False)
    instructions           = Column(Text, nullable=True)

    # Files
    reference_solution_path= Column(String(512), nullable=True)
    label_file_path        = Column(String(512), nullable=True)
    assignment_file_path   = Column(String(512), nullable=True)

    # Timing
    created_at             = Column(DateTime(timezone=True), server_default=func.now())
    updated_at             = Column(DateTime(timezone=True), onupdate=func.now())
    deadline               = Column(DateTime(timezone=True), nullable=True)

    # Scoring — max_score always 20, set automatically
    max_score              = Column(Float, default=20.0, nullable=False)
    passing_score          = Column(Float, default=10.0, nullable=False)

    # Test cases (auto-generated)
    test_cases             = Column(JSON, default=list, nullable=False)

    # Submission config
    is_published           = Column(Boolean, default=False, nullable=False)
    allow_late_submission  = Column(Boolean, default=False, nullable=False)
    late_penalty_percent   = Column(Float, default=20.0)
    max_files              = Column(Integer, default=1, nullable=False)  # ← NEW

    # Relations
    created_by_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by             = relationship("User", back_populates="assignments")
    submissions            = relationship("Submission", back_populates="assignment",
                                          lazy="select")

    def __repr__(self):
        return f"<Assignment id={self.id} title={self.title}>"