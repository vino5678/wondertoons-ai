from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import JobStatus, normalise_language


class AspectRatio(str, Enum):
    WIDE = "16:9"
    VERTICAL = "9:16"
    SQUARE = "1:1"


class Resolution(str, Enum):
    P480 = "480p"
    P720 = "720p"
    P1080 = "1080p"


class Renderer(str, Enum):
    PROCEDURAL_2D = "procedural_2d"
    STORYBOARD_PREVIEW = "storyboard_preview"


class ExportRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    renderer: Renderer = Renderer.PROCEDURAL_2D
    aspect_ratio: AspectRatio = AspectRatio.WIDE
    resolution: Resolution = Resolution.P720
    caption_languages: List[str] = Field(
        default_factory=list, max_length=3,
        description="Languages to burn in and export as subtitle files. Empty = the story's target language "
                    "plus its subtitle languages. Each must exist in the scene plan.")
    burn_captions: bool = True
    narration: bool = Field(default=False, description="Use an installed local Windows speech voice if available.")
    background_music: bool = Field(default=False, description="Generate an original soft tone bed locally with FFmpeg.")
    include_silent_audio: bool = Field(
        default=True, description="Adds a silent AAC track if optional local narration/music is unavailable.")

    @field_validator("title")
    @classmethod
    def _title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value

    @field_validator("caption_languages")
    @classmethod
    def _langs(cls, v: List[str]) -> List[str]:
        out: List[str] = []
        for item in v:
            n = normalise_language(item)
            if n not in out:
                out.append(n)
        return out


class ExportFile(BaseModel):
    name: str
    kind: str  # video | subtitles_srt | subtitles_vtt | manifest
    size_bytes: int
    url: str = Field(description="Path on this API; append ?download=1 to force a download.")


class ExportOut(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    kind: str = "storyboard_preview"
    files: List[Dict[str, Any]] = Field(default_factory=list)
    manifest: Optional[Dict[str, Any]] = None
