"""Turns raw provider scenes into validated Scene objects with exact durations."""
from __future__ import annotations

from pydantic import ValidationError

from app.core.durations import allocate_durations, durations_within_tolerance, tolerance_seconds
from app.core.errors import InvalidInputError, ProviderOutputInvalidError
from app.models.orm import new_id
from app.schemas.story import Scene, StoryRequest


def build_visual_prompt(request: StoryRequest, visual_description: str, cast: list[dict]) -> str:
    people = "; ".join(
        f"{c['name']} ({c['appearance']})" if c.get("appearance") else c["name"] for c in cast
    )
    parts = [f"{request.animation_style}.", visual_description.rstrip(".") + "."]
    if people:
        parts.append(f"Characters: {people}.")
    parts.append(f"For children aged {request.age_group.value}. Tone: {request.tone}. No on-screen text.")
    return " ".join(parts)


def relink_scenes(scenes: list[Scene]) -> list[Scene]:
    """Set order and previous/next references consistently."""
    for i, s in enumerate(scenes):
        s.order = i + 1
        s.previous_scene_id = scenes[i - 1].scene_id if i > 0 else None
        s.next_scene_id = scenes[i + 1].scene_id if i < len(scenes) - 1 else None
    return scenes


def plan_scenes(raw: dict, request: StoryRequest, characters: list[dict]) -> list[Scene]:
    raw_scenes = raw.get("scenes") if isinstance(raw, dict) else None
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ProviderOutputInvalidError("The story provider returned no scenes.")
    try:
        weights = [float(rs.get("weight", 1.0)) for rs in raw_scenes]
        durations = allocate_durations(request.duration_seconds, weights)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ProviderOutputInvalidError(f"Invalid scene weights from provider: {exc}") from exc

    by_id = {c["id"]: c for c in characters}
    scenes: list[Scene] = []
    try:
        for rs, dur in zip(raw_scenes, durations):
            block = rs["by_language"][request.target_language]
            cast = [by_id[c] for c in rs.get("character_ids", []) if c in by_id]
            captions = {}
            for lang, b in rs["by_language"].items():
                text = b.get("narration") or (b["dialogue"][0]["text"] if b.get("dialogue") else "")
                if text:
                    captions[lang] = text
            scenes.append(Scene(
                scene_id=new_id("scn"),
                order=1,
                title=rs["title"],
                description=rs["description"],
                character_ids=list(rs.get("character_ids", [])),
                dialogue=[{"character_id": d["character_id"], "text": d["text"], "language": request.target_language}
                          for d in block.get("dialogue", [])],
                narration=block.get("narration", ""),
                audio_cues=list(rs.get("audio_cues", [])),
                visual_prompt=build_visual_prompt(request, rs["visual_description"], cast),
                estimated_duration_seconds=dur,
                caption_text=captions,
            ))
    except (KeyError, TypeError, ValidationError, IndexError) as exc:
        raise ProviderOutputInvalidError(f"The story provider returned malformed scene data ({type(exc).__name__}).") from exc

    relink_scenes(scenes)
    validate_total(scenes, request.duration_seconds)
    return scenes


def validate_total(scenes: list[Scene], target_seconds: int) -> None:
    ids = [s.scene_id for s in scenes]
    if len(set(ids)) != len(ids):
        raise InvalidInputError("Scene ids must be unique.")
    total = sum(s.estimated_duration_seconds for s in scenes)
    if not durations_within_tolerance([s.estimated_duration_seconds for s in scenes], target_seconds):
        raise InvalidInputError(
            f"Scene durations add up to {total}s but the planned duration is {target_seconds}s "
            f"(allowed tolerance: +/-{tolerance_seconds(target_seconds):g}s).",
            hint="Adjust scene durations, or use POST /projects/{id}/scenes/plan to rescale to a new total.",
        )


def rescale_scenes(scenes: list[Scene], new_total: int) -> list[Scene]:
    new = allocate_durations(new_total, [float(s.estimated_duration_seconds) for s in scenes])
    for s, d in zip(scenes, new):
        s.estimated_duration_seconds = d
    return scenes
