from __future__ import annotations

from app.core.config import Settings
from app.core.durations import choose_scene_count, tolerance_seconds
from app.core.errors import ProviderOutputInvalidError, UnsupportedLanguageError
from app.providers.base import StoryProvider
from app.schemas.common import OutputStatus
from app.schemas.story import CharacterRef, StoryPlan, StoryRequest
from app.services import scene_planner


def check_languages(request: StoryRequest, settings: Settings, provider: StoryProvider | None = None) -> None:
    langs = [request.target_language] + request.subtitle_languages
    not_configured = sorted({l for l in langs if l not in settings.supported_languages})
    if not_configured:
        raise UnsupportedLanguageError(
            f"Language(s) not enabled on this server: {', '.join(not_configured)}.",
            hint=f"Enabled: {', '.join(settings.supported_languages)}. Change WONDERTOONS_SUPPORTED_LANGUAGES to add more "
                 "(the chosen provider must also support them).",
        )
    if provider is not None and provider.supported_languages:
        unsupported = sorted({l for l in langs if l not in provider.supported_languages})
        if unsupported:
            raise UnsupportedLanguageError(
                f"Provider '{provider.name}' does not support: {', '.join(unsupported)}.",
                hint=f"Supported by this provider: {', '.join(provider.supported_languages)}.",
            )


def generate_raw(request: StoryRequest, characters: list[dict], provider: StoryProvider, settings: Settings) -> dict:
    check_languages(request, settings, provider)
    n = choose_scene_count(request.duration_seconds, settings.max_scenes)
    raw = provider.generate_story(request.model_dump(mode="json"), characters, n)
    if not isinstance(raw, dict) or not raw.get("title"):
        raise ProviderOutputInvalidError("The story provider returned an invalid story.")
    return raw


def build_plan(request: StoryRequest, raw: dict, characters: list[dict], provider: StoryProvider) -> StoryPlan:
    scenes = scene_planner.plan_scenes(raw, request, characters)
    used_ids = {cid for s in scenes for cid in s.character_ids}
    used = [CharacterRef(id=c["id"], name=c["name"]) for c in characters if c["id"] in used_ids]
    return StoryPlan(
        title=str(raw["title"])[:200],
        synopsis=str(raw.get("synopsis", ""))[:2000],
        target_language=request.target_language,
        subtitle_languages=request.subtitle_languages,
        age_group=request.age_group,
        total_duration_seconds=request.duration_seconds,
        duration_tolerance_seconds=tolerance_seconds(request.duration_seconds),
        provider=provider.name,
        output_status=OutputStatus.MOCK if provider.is_mock else OutputStatus.GENERATED,
        characters_used=used,
        warnings=[str(w) for w in raw.get("warnings", [])],
        scenes=scenes,
    )
