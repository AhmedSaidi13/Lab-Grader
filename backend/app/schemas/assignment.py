from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any
from datetime import datetime, timezone


# ── Shared deadline validator (write-only) ────────────────────

def _validate_future_deadline(v):
    """Only call this on create/update, never on response schemas."""
    if v is None:
        return v
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("Invalid deadline format. Use ISO 8601.")
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError(
                "Deadline must be in the future. "
                f"Provided: {v.isoformat()}"
            )
    return v


# ── Write schemas (with future deadline validation) ───────────

class AssignmentCreate(BaseModel):
    title:                 str
    description:           str
    instructions:          Optional[str]      = None
    deadline:              Optional[datetime] = None
    passing_score:         float              = 10.0
    allow_late_submission: bool               = False
    late_penalty_percent:  float              = 20.0
    max_files:             int                = 1

    @field_validator("deadline", mode="before")
    @classmethod
    def deadline_must_be_future(cls, v):
        return _validate_future_deadline(v)

    @field_validator("max_files")
    @classmethod
    def max_files_range(cls, v):
        if v < 1 or v > 10:
            raise ValueError("max_files must be between 1 and 10")
        return v


class AssignmentUpdate(BaseModel):
    title:                 Optional[str]      = None
    description:           Optional[str]      = None
    instructions:          Optional[str]      = None
    deadline:              Optional[datetime] = None
    is_published:          Optional[bool]     = None
    allow_late_submission: Optional[bool]     = None
    late_penalty_percent:  Optional[float]    = None
    passing_score:         Optional[float]    = None
    max_files:             Optional[int]      = None

    @field_validator("deadline", mode="before")
    @classmethod
    def deadline_must_be_future(cls, v):
        return _validate_future_deadline(v)

    @field_validator("max_files")
    @classmethod
    def max_files_range(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("max_files must be between 1 and 10")
        return v


# ── Read schemas (NO deadline validation — deadline may be past) ──

class AssignmentResponse(BaseModel):
    """
    Used for GET responses — no deadline validation.
    Deadline is allowed to be in the past (assignment already expired).
    """
    id:                      int
    title:                   str
    description:             str
    instructions:            Optional[str]      = None
    deadline:                Optional[datetime] = None   # no validator here
    passing_score:           float
    allow_late_submission:   bool
    late_penalty_percent:    float
    max_files:               int                = 1
    is_published:            bool
    max_score:               float
    reference_solution_path: Optional[str]      = None
    label_file_path:         Optional[str]      = None
    assignment_file_path:    Optional[str]      = None
    test_cases:              List[Any]          = []
    created_by_id:           int
    created_at:              datetime
    updated_at:              Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssignmentListResponse(BaseModel):
    """
    Used for list responses — no deadline validation.
    """
    id:              int
    title:           str
    description:     str
    deadline:        Optional[datetime] = None   # no validator here
    is_published:    bool
    max_score:       float
    max_files:       int   = 1
    test_case_count: int   = 0
    created_at:      datetime

    model_config = {"from_attributes": True}