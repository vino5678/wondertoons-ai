from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import AgeGroup, OutputStatus, normalise_language


class StoryRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000, description="The one-line idea for the video.")
    target_language: str = Field(default="en", description="Primary spoken/written language code, e.g. 'ta' or 'en'.")
    subtitle_languages: List[str] = Field(default_factory=list, max_length=5)
    age_group: AgeGroup = AgeGroup.AGE_3_5
    duration_seconds: int = Field(default=60, ge=10, le=3600, description="Planned total video length in seconds.")
    animation_style: str = Field(default="colorful 2D cartoon", min_length=1, max_length=120)
    educational_objectives: List[str] = Field(default_factory=list, max_length=10)
    character_ids: List[str] = Field(default_factory=list, max_length=10,
                                     description="Characters to use. Empty = the project's selected characters.")
    character_preferences: str = Field(default="", max_length=1000)
    tone: str = Field(default="warm and playful", max_length=200)

    @field_validator("target_language")
    @classmethod
    def _lang(cls, v: str) -> str:
        return normalise_language(v)

    @field_validator("subtitle_languages")
    @classmethod
    def _subs(cls, v: List[str]) -> List[str]:
        out: List[str] = []
        for item in v:
            n = normalise_language(item)
            if n not in out:
                out.append(n)
        return out

    @field_validator("educational_objectives")
    @classmethod
    def _objectives(cls, v: List[str]) -> List[str]:
        cleaned = [o.strip() for o in v if o.strip()]
        if any(len(o) > 200 for o in cleaned):
            raise ValueError("Each educational objective must be at most 200 characters.")
        return cleaned


class DialogueLine(BaseModel):
    character_id: str
    text: str = Field(min_length=1, max_length=1000)
    language: str


class Scene(BaseModel):
    scene_id: str
    order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=2000)
    character_ids: List[str] = Field(default_factory=list)
    dialogue: List[DialogueLine] = Field(default_factory=list)
    narration: str = Field(default="", max_length=2000)
    audio_cues: List[str] = Field(default_factory=list)
    visual_prompt: str = Field(min_length=1, max_length=4000)
    estimated_duration_seconds: int = Field(ge=1, le=3600)
    caption_text: Dict[str, str] = Field(default_factory=dict, description="language code -> caption text")
    previous_scene_id: Optional[str] = None
    next_scene_id: Optional[str] = None


class CharacterRef(BaseModel):
    id: str
    name: str


class StoryPlan(BaseModel):
    title: str
    synopsis: str
    target_language: str
    subtitle_languages: List[str]
    age_group: AgeGroup
    total_duration_seconds: int
    duration_tolerance_seconds: float
    provider: str
    output_status: OutputStatus
    characters_used: List[CharacterRef]
    warnings: List[str] = Field(default_factory=list)
    scenes: List[Scene]


class ScenePlanUpdate(BaseModel):
    scenes: List[Scene] = Field(min_length=1, max_length=500)


class ScenePlanRescale(BaseModel):
    total_duration_seconds: int = Field(ge=10, le=3600)
