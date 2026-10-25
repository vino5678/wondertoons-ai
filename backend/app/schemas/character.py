from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.errors import InvalidInputError
from app.core.paths import IMAGE_EXTENSIONS, validate_relative_path
from app.schemas.common import OutputStatus, normalise_language


class VoicePreferences(BaseModel):
    language: Optional[str] = None
    style: Optional[str] = Field(default=None, max_length=100)
    pitch: Optional[str] = Field(default=None, max_length=50)
    provider_voice_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("language")
    @classmethod
    def _lang(cls, v):
        return normalise_language(v) if v else v


def _check_paths(paths: List[str]) -> List[str]:
    out = []
    for p in paths:
        try:
            out.append(validate_relative_path(p, IMAGE_EXTENSIONS))
        except InvalidInputError as exc:
            raise ValueError(exc.message) from exc
    return out


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    appearance: str = Field(min_length=1, max_length=1000)
    personality: str = Field(default="", max_length=500)
    voice_preferences: VoicePreferences = Field(default_factory=VoicePreferences)
    reference_image_paths: List[str] = Field(
        default_factory=list, max_length=20,
        description="Paths relative to the data/characters folder. Files need not exist yet.")

    @field_validator("name", "appearance")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("reference_image_paths")
    @classmethod
    def _paths(cls, v):
        return _check_paths(v)


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=1000)
    appearance: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    personality: Optional[str] = Field(default=None, max_length=500)
    voice_preferences: Optional[VoicePreferences] = None
    reference_image_paths: Optional[List[str]] = Field(default=None, max_length=20)

    @field_validator("reference_image_paths")
    @classmethod
    def _paths(cls, v):
        return _check_paths(v) if v is not None else v


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    appearance: str
    personality: str
    voice_preferences: VoicePreferences
    reference_image_paths: List[str]
    created_at: datetime
    updated_at: datetime


class AppearanceOut(BaseModel):
    project_id: str
    project_title: str
    role: str
    selected_at: datetime


class SimilarityCheckRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    appearance: str = Field(min_length=1, max_length=1000)
    exclude_character_id: Optional[str] = None


class SimilarityMatchOut(BaseModel):
    character_id: str
    name: str
    score: float


class SimilarityReport(BaseModel):
    method: str
    guarantees_visual_uniqueness: bool
    threshold: float
    verdict: str  # "possible_duplicate" | "no_text_match"
    matches: List[SimilarityMatchOut]
    note: str


class CharacterGenerationRequest(BaseModel):
    brief: str = Field(min_length=3, max_length=500, description="Short description of the character wanted.")


class CharacterDraft(BaseModel):
    output_status: OutputStatus
    draft: CharacterCreate
    similarity: SimilarityReport
    note: str
