from __future__ import annotations

from app.core.config import Settings
from app.core.errors import ProviderUnavailableError
from app.providers.base import StoryProvider
from app.providers.external_llm import ExternalLLMStoryProvider
from app.providers.mock_story import MockStoryProvider

AVAILABLE_STORY_PROVIDERS = ("mock", "external_llm")


def get_story_provider(name: str, settings: Settings) -> StoryProvider:
    if name == "mock":
        return MockStoryProvider()
    if name == "external_llm":
        if not settings.network_features_enabled:
            raise ProviderUnavailableError(
                "Optional network-dependent providers are disabled on this studio.",
                hint="Local story and video features do not need network access. "
                     "Set WONDERTOONS_ALLOW_NETWORK_FEATURES=true only when deliberately enabling a reviewed provider.",
            )
        return ExternalLLMStoryProvider(settings.llm_api_key)
    raise ProviderUnavailableError(
        f"Unknown story provider '{name}'.",
        hint=f"Available providers: {', '.join(AVAILABLE_STORY_PROVIDERS)}.",
    )
