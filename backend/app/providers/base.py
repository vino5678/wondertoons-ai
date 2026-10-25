"""Provider interfaces. Providers return plain dicts which the services validate
with Pydantic, so untrusted provider output is never trusted blindly."""
from __future__ import annotations

from abc import ABC, abstractmethod


class StoryProvider(ABC):
    name: str = "base"
    is_mock: bool = False
    # Languages this provider can write. An empty tuple means "the provider validates itself".
    supported_languages: tuple = ()

    @abstractmethod
    def generate_story(self, request: dict, characters: list[dict], scene_count: int) -> dict:
        """Return {"title", "synopsis", "warnings": [..], "scenes": [raw_scene, ...]}.

        raw_scene = {"kind", "title", "description", "visual_description", "weight",
                     "character_ids": [..], "audio_cues": [..],
                     "by_language": {lang: {"narration": str,
                                            "dialogue": [{"character_id", "text"}]}}}
        """
