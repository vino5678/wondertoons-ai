"""Placeholder for an optional external LLM story provider.

No real endpoint is implemented: the provider's CURRENT API documentation,
language support and commercial-use terms must be checked first, and endpoints
must not be guessed. This stub exists so missing-credential behaviour is real.
"""
from __future__ import annotations

from app.core.errors import ProviderCredentialsMissingError, ProviderUnavailableError
from app.providers.base import StoryProvider


class ExternalLLMStoryProvider(StoryProvider):
    name = "external_llm"
    is_mock = False
    supported_languages = ()  # to be declared once a real provider is chosen

    def __init__(self, api_key: str | None):
        if not api_key:
            raise ProviderCredentialsMissingError(
                "The 'external_llm' story provider needs an API key, but none is configured.",
                hint="Set WONDERTOONS_LLM_API_KEY in your .env file (see .env.example), or use the 'mock' provider.",
            )
        self._api_key = api_key  # never log or return

    def generate_story(self, request: dict, characters: list[dict], scene_count: int) -> dict:
        raise ProviderUnavailableError(
            "The 'external_llm' provider is not implemented yet.",
            hint="A real integration must be written against the chosen provider's current API docs.",
            code="provider_not_implemented",
        )
