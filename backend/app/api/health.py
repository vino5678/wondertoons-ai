from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.providers.registry import AVAILABLE_STORY_PROVIDERS
from app.services import assembly

router = APIRouter(tags=["health"])
APP_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    version: str
    database: str  # "ok" | "error"
    ffmpeg_available: bool
    ffprobe_available: bool
    default_story_provider: str
    available_story_providers: List[str]
    supported_languages: List[str]
    external_llm_configured: bool  # whether a key is set; the key itself is never returned
    network_features_enabled: bool


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Returns 200 with `status: ok`, or `degraded` if the database check fails."""
    try:
        db.execute(text("SELECT 1"))
        db_state = "ok"
    except Exception:  # noqa: BLE001
        db_state = "error"
    return HealthResponse(
        status="ok" if db_state == "ok" else "degraded", version=APP_VERSION, database=db_state,
        ffmpeg_available=assembly.find_ffmpeg() is not None,
        ffprobe_available=assembly.find_ffprobe() is not None,
        default_story_provider=settings.story_provider,
        available_story_providers=list(AVAILABLE_STORY_PROVIDERS),
        supported_languages=list(settings.supported_languages),
        external_llm_configured=bool(settings.llm_api_key),
        network_features_enabled=settings.network_features_enabled,
    )
