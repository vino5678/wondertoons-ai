from app.services.captions import (Cue, build_cues, reading_speed_warnings, to_srt, to_vtt, validate_cues)

SCENES = [
    {"estimated_duration_seconds": 4, "caption_text": {"en": "Hello <friends> & all", "ta": "வணக்கம்!"}},
    {"estimated_duration_seconds": 5, "caption_text": {"en": "Second"}},
    {"estimated_duration_seconds": 3, "caption_text": {"ta": "மீண்டும் சந்திப்போம்"}},
]


def test_cues_follow_scene_timeline():
    cues = build_cues(SCENES, "en")
    assert [(c.start, c.end) for c in cues] == [(0.0, 3.9), (4.0, 8.9)]
    ta = build_cues(SCENES, "ta")
    assert [(c.start, c.end) for c in ta] == [(0.0, 3.9), (9.0, 11.9)]  # scene 3 starts at 9s even though scene 2 has no Tamil


def test_validation_passes_for_built_cues_and_catches_problems():
    assert validate_cues(build_cues(SCENES, "ta")) == []
    bad = [Cue(1, 0, 5, "a"), Cue(2, 4, 6, "b"), Cue(3, 7, 7, "c"), Cue(4, 8, 9, " ")]
    problems = " ".join(validate_cues(bad))
    assert "overlaps" in problems and "invalid timing" in problems and "no text" in problems


def test_srt_format():
    srt = to_srt(build_cues(SCENES, "en"))
    assert srt.startswith("1\n00:00:00,000 --> 00:00:03,900\nHello <friends> & all\n\n2\n00:00:04,000 --> 00:00:08,900\nSecond")


def test_vtt_format_escapes_markup_and_keeps_tamil():
    vtt = to_vtt(build_cues(SCENES, "en"))
    assert vtt.startswith("WEBVTT\n\n00:00:00.000 --> 00:00:03.900\nHello &lt;friends&gt; &amp; all")
    assert "வணக்கம்!" in to_vtt(build_cues(SCENES, "ta"))


def test_hour_timestamps_and_reading_speed():
    long = [{"estimated_duration_seconds": 3700, "caption_text": {"en": "x"}},
            {"estimated_duration_seconds": 2, "caption_text": {"en": "y" * 100}}]
    cues = build_cues(long, "en")
    assert "01:01:40,000" in to_srt(cues)
    assert len(reading_speed_warnings(cues)) == 1
