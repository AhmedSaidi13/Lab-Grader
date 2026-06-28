from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class NotificationType(str, enum.Enum):
    evaluation_complete = "evaluation_complete"
    assignment_published = "assignment_published"
    deadline_passed     = "deadline_passed"
    general             = "general"


class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type        = Column(SAEnum(NotificationType), default=NotificationType.general)
    title       = Column(String(256), nullable=False)
    message     = Column(Text, nullable=False)
    is_read     = Column(Boolean, default=False, nullable=False)
    link        = Column(String(512), nullable=True)   # frontend route
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications", lazy="select")

    def __repr__(self):
        return f"<Notification id={self.id} user={self.user_id} read={self.is_read}>"