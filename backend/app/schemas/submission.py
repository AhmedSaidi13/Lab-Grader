from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.submission import SubmissionStatus


class SubmissionFileInfo(BaseModel):
    path:              str
    original_filename: str


class SubmissionCreate(BaseModel):
    assignment_id: int


class SubmissionResponse(BaseModel):
    id:                int
    assignment_id:     int
    student_id:        int
    original_filename: Optional[str] = None
    files:             List[Any]     = []
    version:           int           = 1
    status:            SubmissionStatus
    is_late:           bool
    score:             Optional[float]     = None
    compile_output:    Optional[str]       = None
    test_results:      List[Any]           = []
    static_analysis:   Dict[str, Any]      = {}
    feedback:          Optional[str]       = None
    celery_task_id:    Optional[str]       = None
    submitted_at:      datetime
    updated_at:        Optional[datetime]  = None
    evaluated_at:      Optional[datetime]  = None

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    id:                int
    assignment_id:     int
    original_filename: Optional[str] = None
    files:             List[Any]     = []
    version:           int           = 1
    status:            SubmissionStatus
    score:             Optional[float] = None
    is_late:           bool
    submitted_at:      datetime

    model_config = {"from_attributes": True}