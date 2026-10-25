"""Deterministic mock story provider (no network, no API keys).

Output is TEMPLATED text, not AI-written. Tamil lines are fixed phrases; the
topic words from the prompt are inserted as typed and are NOT translated.
"""
from __future__ import annotations

import re

from app.core.errors import UnsupportedLanguageError
from app.providers.base import StoryProvider

_EN = {
    "intro": ("Today we are going to explore {topic}!",
              ["Hello, friends! Are you ready to learn?", "Yes! Let's begin!"]),
    "learn": ("Let's discover part {i} of {topic}.",
              ["Look at this! Here is something new about {topic}.", "Wow, that is so interesting!"]),
    "recap": ("Let's remember what we learned.",
              ["Great job! We learned so much today!", "Let's say it together once more!"]),
    "outro": ("Thank you for learning with us!",
              ["Goodbye, friends. See you next time!", "Bye bye!"]),
}
_EN_OBJECTIVE = "Remember: {objective}."

_TA = {
    "intro": ("இன்று நாம் {topic} பற்றி கற்றுக்கொள்வோம்!",
              ["வணக்கம் நண்பர்களே! கற்றுக்கொள்ள தயாரா?", "ஆம்! தொடங்குவோம்!"]),
    "learn": ("{topic} பற்றிய பகுதி {i}-ஐ பார்ப்போம்.",
              ["இதைப் பாருங்கள்! {topic} பற்றி புதிய செய்தி இருக்கிறது.", "அருமை, மிகவும் சுவாரஸ்யம்!"]),
    "recap": ("நாம் கற்றதை நினைவு கூர்வோம்.",
              ["அருமை! நாம் நிறைய கற்றுக்கொண்டோம்!", "ஒன்றாக மீண்டும் சொல்வோம்!"]),
    "outro": ("எங்களுடன் கற்றதற்கு நன்றி!",
              ["மீண்டும் சந்திப்போம், நண்பர்களே!", "பை பை!"]),
}
_TA_OBJECTIVE = "நினைவில் கொள்ளுங்கள்: {objective}."

_TEMPLATES = {"en": (_EN, _EN_OBJECTIVE), "ta": (_TA, _TA_OBJECTIVE)}
_WEIGHTS = {"intro": 1.0, "learn": 2.0, "recap": 1.2, "outro": 0.8}
_CUES = {
    "intro": ["cheerful opening jingle (background music)", "sparkle sound as the title appears"],
    "learn": ["gentle upbeat background music", "soft chime on each new discovery"],
    "recap": ["calm reflective background music", "applause sound effect"],
    "outro": ["warm closing background music", "short wave-goodbye sound effect"],
}


def _kinds(n: int) -> list[str]:
    if n <= 2:
        return ["intro", "outro"][:n]
    if n < 5:
        return ["intro"] + ["learn"] * (n - 2) + ["outro"]
    return ["intro"] + ["learn"] * (n - 3) + ["recap", "outro"]


def _topic(prompt: str) -> str:
    cleaned = " ".join(prompt.split())
    return cleaned if len(cleaned) <= 60 else cleaned[:57].rstrip() + "..."


_BEAT_MARKER = re.compile(
    r"(?P<start>\d{1,3})\s*(?:-|–|—|to)\s*\d{1,3}\s*(?:seconds?|secs?)\s*:\s*",
    re.IGNORECASE,
)
_CHARACTER_TERMS = (
    "watermelon", "banana", "orange", "pineapple", "rabbit", "bunny", "dinosaur",
    "unicorn", "dragon", "elephant", "monkey", "frog", "lion", "dolphin", "fish",
    "whale", "penguin", "butterfly", "bee", "robot", "fox", "cat", "bear", "dog",
    "bird", "turtle", "girl", "boy", "children",
)


def _prompt_beats(prompt: str) -> list[str]:
    markers = list(_BEAT_MARKER.finditer(prompt))
    beats = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(prompt)
        beat = " ".join(prompt[marker.end():end].strip(" \t\r\n-–—;").split())
        if beat:
            beats.append(beat)
    return beats


def _prompt_characters(prompt: str) -> list[str]:
    lowered = prompt.lower()
    found = [(lowered.find(term), term) for term in _CHARACTER_TERMS if lowered.find(term) >= 0]
    return list(dict.fromkeys(term for _, term in sorted(found)))


def _scene_direction(prompt: str, kind: str, index: int, beats: list[str]) -> str:
    # Keep visual prompts focused on the requested shot instead of finding any
    # character/action word anywhere in the full script.
    text = (beats[0] if kind == "intro" and beats else
            beats[min(index, len(beats) - 1)] if kind == "learn" and beats else
            beats[-2] if kind == "recap" and len(beats) > 1 else
            beats[-1] if kind == "outro" and beats else prompt)
    lowered = text.lower()
    actions = (
        ("share", ("share", "sharing", "take turns", "taking turns"), "share a toy with a friend"),
        ("plant", ("plant", "planting", "seed", "garden"), "plant a seed and care for it"),
        ("build", ("build", "building", "make", "making", "construct"), "build something together"),
        ("help", ("help", "helping", "kind", "kindness", "friend"), "help a friend"),
        ("run", ("run", "running", "race", "chase"), "run along the path"),
        ("fly", ("fly", "flying", "soar", "wing"), "fly through the scene"),
        ("swim", ("swim", "swimming", "ocean", "underwater"), "swim through the scene"),
        ("freeze", ("freeze", "freezes", "frozen", "stop", "stops the music"), "freeze in a funny pose"),
        ("dance", ("dance", "dancing", "song", "sing"), "dance together"),
        ("wave", ("wave", "goodbye"), "wave goodbye"),
        ("explore", ("explore", "exploring", "discover", "journey", "adventure"), "explore the setting"),
        ("learn", ("learn", "learning", "lesson", "discover"), "look closely at the topic"),
    )
    action = next((description for _, terms, description in actions if any(term in lowered for term in terms)),
                  "explore the topic")
    cast = _prompt_characters(prompt)
    cast_note = f" Story characters: {', '.join(cast)}." if cast else ""
    if kind == "intro":
        return f"Opening scene. {text}{cast_note}"
    if kind == "learn":
        return f"Scene {index}: the characters {action}. Show this requested moment: {text}{cast_note}"
    if kind == "recap":
        return f"Recap scene. The characters celebrate what happened: {text}{cast_note}"
    return f"Closing scene. The characters wave goodbye: {text}{cast_note}"


class MockStoryProvider(StoryProvider):
    name = "mock"
    is_mock = True
    supported_languages = ("en", "ta")

    def generate_story(self, request: dict, characters: list[dict], scene_count: int) -> dict:
        target = request["target_language"]
        langs = [target] + [l for l in request.get("subtitle_languages", []) if l != target]
        bad = [l for l in langs if l not in self.supported_languages]
        if bad:
            raise UnsupportedLanguageError(
                f"The mock story provider only supports {', '.join(self.supported_languages)}; got: {', '.join(bad)}.",
                hint="Use en/ta, or configure a real provider that supports the language.",
            )
        full_prompt = " ".join(request["prompt"].split())
        topic = _topic(full_prompt)
        beats = _prompt_beats(full_prompt)
        objectives = request.get("educational_objectives") or []
        cast = characters
        warnings = ["Mock provider output: templated text, not AI-written."]
        if not characters:
            warnings.append(
                "No saved characters selected. Recognized characters named in the prompt are drawn procedurally; "
                "they are not saved character profiles."
            )
        if "ta" in langs:
            warnings.append("Tamil lines are fixed template phrases; topic words are inserted untranslated.")

        scenes = []
        learn_i = 0
        for idx, kind in enumerate(_kinds(scene_count)):
            if kind == "learn":
                learn_i += 1
            speakers = [cast[(idx + k) % len(cast)]["id"] for k in range(2)] if len(cast) > 1 else (
                [cast[0]["id"]] * 2 if cast else [])
            by_language = {}
            for lang in langs:
                templates, obj_tpl = _TEMPLATES[lang]
                narration_tpl, lines = templates[kind]
                fmt = {"topic": topic, "i": learn_i}
                dialogue_lines = [l.format(**fmt) for l in lines]
                if kind == "learn" and objectives:
                    dialogue_lines.append(obj_tpl.format(objective=objectives[(learn_i - 1) % len(objectives)]))
                by_language[lang] = {
                    "narration": narration_tpl.format(**fmt),
                    "dialogue": [
                        {"character_id": speakers[j % 2], "text": text} for j, text in enumerate(dialogue_lines)
                    ] if speakers else [],
                }
            title = {"intro": "Welcome", "learn": f"Discovery {learn_i}", "recap": "Let's Remember", "outro": "Goodbye"}[kind]
            scenes.append({
                "kind": kind,
                "title": title,
                "description": f"{title}: {_scene_direction(full_prompt, kind, learn_i, beats)}",
                "visual_description": _scene_direction(full_prompt, kind, learn_i, beats),
                "weight": _WEIGHTS[kind],
                "character_ids": sorted({c["id"] for c in cast}),
                "audio_cues": list(_CUES[kind]),
                "by_language": by_language,
            })
        return {
            "title": f"Let's Learn: {topic}",
            "synopsis": f"A short educational story based on '{topic}' for ages {request.get('age_group', '')}.".strip(),
            "warnings": warnings,
            "scenes": scenes,
        }
