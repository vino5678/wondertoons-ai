from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SECRET_HINTS = ("key", "secret", "token", "password", "credential", "authorization")


def _reject_secrets(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(h in str(k).lower() for h in _SECRET_HINTS):
                raise ValueError(
                    f"provider_settings must not contain secrets (found '{path}{k}'). "
                    "Put API keys in the server's .env file instead."
                )
            _reject_secrets(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for item in obj:
            _reject_secrets(item, path)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(default="", max_length=2000)
    provider_settings: Dict[str, Any] = Field(default_factory=dict, description="Non-secret provider choices only.")

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v

    @field_validator("provider_settings")
    @classmethod
    def _no_secrets(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        _reject_secrets(v)
        return v


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    prompt: Optional[str] = Field(default=None, max_length=2000)
    provider_settings: Optional[Dict[str, Any]] = None

    @field_validator("provider_settings")
    @classmethod
    def _no_secrets(cls, v):
        if v is not None:
            _reject_secrets(v)
        return v


class ProjectOut(BaseModel):
    id: str
    title: str
    prompt: str
    provider_settings: Dict[str, Any]
    has_story: bool
    scene_count: int
    selected_character_ids: List[str]
    created_at: datetime
    updated_at: datetime
