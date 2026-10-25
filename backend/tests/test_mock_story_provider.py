from app.core.errors import UnsupportedLanguageError
from app.providers.mock_story import MockStoryProvider
from app.providers.registry import get_story_provider
from app.core.config import Settings
from app.core.errors import ProviderCredentialsMissingError, ProviderUnavailableError
from pathlib import Path
import tempfile

REQ = {"prompt": "Why is the sky blue?", "target_language": "en", "subtitle_languages": ["ta"],
       "age_group": "3-5", "educational_objectives": ["Light bends"]}


def test_deterministic():
    p = MockStoryProvider()
    assert p.generate_story(REQ, [], 5) == p.generate_story(REQ, [], 5)


def test_scene_structure():
    r = MockStoryProvider().generate_story(REQ, [{"id": "c1", "name": "A"}, {"id": "c2", "name": "B"}], 6)
    kinds = [s["kind"] for s in r["scenes"]]
    assert kinds[0] == "intro" and kinds[-1] == "outro" and "recap" in kinds and len(kinds) == 6
    assert all(set(s["by_language"]) == {"en", "ta"} for s in r["scenes"])


def test_prompt_details_reach_each_scene_visual_direction():
    prompt = (
        "Create a story about a rabbit learning to share a red ball with a friend "
        "in a magical forest, then celebrate together."
    )
    result = MockStoryProvider().generate_story({**REQ, "prompt": prompt}, [], 4)
    visuals = [scene["visual_description"] for scene in result["scenes"]]
    assert all(prompt in description for description in visuals)
    assert "share a toy with a friend" in visuals[1]
    assert visuals[0] != visuals[1] != visuals[-1]


def test_timestamped_prompt_beats_and_character_roster_reach_their_scenes():
    prompt = (
        "CHARACTERS: watermelon, banana, orange, rabbit and girl. STORY: "
        "0-10 seconds: A watermelon rolls into a magical garden and starts dancing. "
        "10-25 seconds: A banana slides in and an orange jumps from behind a flower. "
        "25-40 seconds: All the characters dance together and the girl claps. "
        "40-52 seconds: Everyone freezes in funny poses. "
        "52-60 seconds: They perform a final dance and wave goodbye."
    )
    result = MockStoryProvider().generate_story({**REQ, "prompt": prompt}, [], 5)
    visuals = [scene["visual_description"] for scene in result["scenes"]]
    lowered = [visual.lower() for visual in visuals]
    assert "watermelon rolls" in lowered[0]
    assert "banana slides" in lowered[1]
    assert "orange jumps" in lowered[1]
    assert "all the characters dance" in lowered[2]
    assert "everyone freezes" in lowered[3]
    assert "wave goodbye" in lowered[4]
    assert all("Story characters: watermelon, banana, orange, rabbit, girl." in visual for visual in visuals)
    assert all(not scene["character_ids"] for scene in result["scenes"])
    assert all(not scene["by_language"]["en"]["dialogue"] for scene in result["scenes"])
    assert any("No saved characters selected" in warning for warning in result["warnings"])
    assert "placeholder_host" not in str(result)


def test_tamil_text_present():
    r = MockStoryProvider().generate_story({**REQ, "target_language": "ta", "subtitle_languages": []}, [], 3)
    text = r["scenes"][0]["by_language"]["ta"]["narration"]
    assert any("\u0b80" <= ch <= "\u0bff" for ch in text)


def test_unsupported_language():
    try:
        MockStoryProvider().generate_story({**REQ, "target_language": "fr"}, [], 3)
    except UnsupportedLanguageError:
        return
    raise AssertionError("accepted fr")


def test_missing_credentials_and_unknown_provider():
    s = Settings.for_testing(Path(tempfile.mkdtemp()), network_features_enabled=True)
    for name, exc in (("external_llm", ProviderCredentialsMissingError), ("nope", ProviderUnavailableError)):
        try:
            get_story_provider(name, s)
        except exc:
            continue
        raise AssertionError(name)
