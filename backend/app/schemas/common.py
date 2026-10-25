import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel

LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})*$")


class OutputStatus(str, Enum):
    """Never present MOCK output as GENERATED."""
    MOCK = "mock"
    GENERATED = "generated"
    PENDING = "pending"
    FAILED = "failed"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgeGroup(str, Enum):
    AGE_3_5 = "3-5"
    AGE_6_8 = "6-8"
    AGE_9_12 = "9-12"


class ErrorBody(BaseModel):
    code: str
    message: str
    hint: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def normalise_language(value: str) -> str:
    v = value.strip().lower()
    if not LANG_RE.match(v):
        raise ValueError(f"'{value}' is not a valid language code (examples: en, ta, pt-br).")
    return v
