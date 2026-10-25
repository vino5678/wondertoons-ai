from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JobStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    kind: str
    status: JobStatus
    stage: str
    progress: int = Field(ge=0, le=100, description="0-100. See progress_kind.")
    progress_kind: str = Field(description="'stage_based' = a fixed value per pipeline stage, NOT measured work.")
    error_message: Optional[str] = None
    output_files: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
