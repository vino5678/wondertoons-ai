import shutil
import tempfile
import unittest
from pathlib import Path

from app.services import assembly as A


def test_output_sizes_are_even_and_match_aspect():
    assert A.output_size("16:9", "720p") == (1280, 720)
    assert A.output_size("16:9", "480p") == (854, 480)
    assert A.output_size("9:16", "1080p") == (1080, 1920)
    assert A.output_size("1:1", "720p") == (720, 720)


def test_unsupported_size_rejected():
    for args in (("4:3", "720p"), ("16:9", "4k")):
        try:
            A.output_size(*args)
        except A.AssemblyError:
            continue
        raise AssertionError(args)


def test_ass_escape_neutralises_override_tags():
    assert "{" not in A.ass_escape("a {\\fs500} b") and "\\" not in A.ass_escape("a\\Nb")
    assert A.ass_escape("line1\nline2\r\n  line3") == "line1 line2 line3"


def test_scene_ass_contains_label_title_and_caption_lines():
    ass = A.build_scene_ass(1280, 720, 5, "Title {x}", ["English", "தமிழ்"], "LABEL", "FreeSans")
    assert "PlayResX: 1280" in ass and "LABEL" in ass and "Title (x)" in ass and r"English\Nதமிழ்" in ass
    assert "{x}" not in ass


def test_ffmpeg_args_are_a_list_without_shell_text():
    args = A.scene_clip_args("ffmpeg", 854, 480, 5.0, "2D6CDF", "scene_0001.ass", "scene_0001.mp4")
    assert isinstance(args, list) and all(isinstance(a, str) for a in args)
    assert "-an" in args and "scene_0001.mp4" == args[-1]
    final = A.final_mux_args("ffmpeg", "concat.txt", "out.mp4", True)
    assert "aac" in final and "-shortest" in final
    with_audio = A.final_mux_args("ffmpeg", "concat.txt", "out.mp4", False, "audio.wav", 12)
    assert "-map" in with_audio and "apad" in with_audio and "12.000" in with_audio


def test_ffmpeg_tools_are_found_in_winget_when_path_is_stale(tmp_path, monkeypatch):
    binary_dir = (tmp_path / "Microsoft" / "WinGet" / "Packages" /
                  "Gyan.FFmpeg.Shared_Source" / "ffmpeg-9.0.2" / "bin")
    binary_dir.mkdir(parents=True)
    ffmpeg = binary_dir / "ffmpeg.exe"
    ffprobe = binary_dir / "ffprobe.exe"
    ffmpeg.touch()
    ffprobe.touch()

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("WONDERTOONS_FFMPEG_PATH", raising=False)
    monkeypatch.delenv("WONDERTOONS_FFPROBE_PATH", raising=False)
    monkeypatch.setattr(A.shutil, "which", lambda _name: None)

    assert A.find_ffmpeg() == str(ffmpeg)
    assert A.find_ffprobe() == str(ffprobe)


def test_procedural_art_and_filter_are_local_and_deterministic():
    from app.services import procedural_art

    tmp = Path(tempfile.mkdtemp())
    try:
        background, mascot = tmp / "scene.ppm", tmp / "mascot.ppm"
        procedural_art.make_background("magic forest", "storybook illustration", 1, background)
        kind = procedural_art.make_mascot("a rabbit learns to share", mascot)
        assert background.read_bytes().startswith(b"P6\n640 360\n255\n")
        assert mascot.read_bytes().startswith(b"P6\n180 220\n255\n")
        assert kind == "rabbit"
        args = A.procedural_clip_args("ffmpeg", 854, 480, 5, "scene.ppm", "mascot.ppm", "scene.ass", "out.mp4")
        assert args[0] == "ffmpeg" and "overlay=x=" in args[args.index("-filter_complex") + 1]
        assert "sin(2*PI*t/7)" in args[args.index("-filter_complex") + 1]
        assert args[-1] == "out.mp4"
        assert procedural_art.mascot_kind("a friendly robot explores the city") == "robot"
        assert procedural_art.mascot_kind("a dolphin swims under the sea") == "fish"
        assert procedural_art.mascot_kind(
            "A watermelon dances. Story characters: watermelon, banana, orange, rabbit, girl."
        ) == "watermelon"
        assert procedural_art.mascot_kind(
            "A banana slides into the scene. Story characters: watermelon, banana, orange, rabbit, girl."
        ) == "banana"
        assert procedural_art._prompt_color(
            "Characters: Fifi Fox (a bright blue fox with a red scarf)", "fox", (1, 2, 3)
        ) == (100, 143, 190)
        assert procedural_art._prompt_clothing_color(
            "Characters: Nia (a child wearing a sunny yellow shirt and denim overalls)"
        ) == (221, 180, 73)
        assert procedural_art.motion_kind("the rabbit jumps over a stream") == "jump"
        assert procedural_art.motion_kind("the fish swims in the ocean") == "swim"
        assert procedural_art.motion_kind("everyone freezes in a funny pose") == "freeze"
        dance_args = A.procedural_clip_args(
            "ffmpeg", 854, 480, 5, "scene.ppm", "mascot.ppm", "scene.ass", "out.mp4", "dance")
        assert "abs(sin(2*PI*t/1.1))" in dance_args[dance_args.index("-filter_complex") + 1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_prompt_settings_render_distinct_backgrounds():
    from app.services import procedural_art

    tmp = Path(tempfile.mkdtemp())
    try:
        scenes = (
            ("a rabbit shares a ball in a magical forest", "forest"),
            ("a robot flies through a city at night", "city"),
            ("a dolphin explores an underwater coral reef", "underwater"),
            ("an astronaut visits a moon base in space", "space"),
        )
        rendered = []
        for index, (prompt, expected_setting) in enumerate(scenes, start=1):
            path = tmp / f"scene-{index}.ppm"
            procedural_art.make_background(prompt, "colorful 2D cartoon", index, path)
            rendered.append(path.read_bytes())
            assert procedural_art._match(prompt, procedural_art._SETTINGS, "meadow") == expected_setting
        assert len(set(rendered)) == len(scenes)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_prompt_subjects_produce_individual_mascot_assets():
    from app.services import procedural_art

    tmp = Path(tempfile.mkdtemp())
    try:
        prompts = (
            ("a dinosaur", "dinosaur"), ("a unicorn", "unicorn"), ("a dragon", "dragon"),
            ("an elephant", "elephant"), ("a monkey", "monkey"), ("a frog", "frog"),
            ("a lion", "lion"), ("a dolphin", "fish"), ("a whale", "whale"),
            ("a penguin", "penguin"), ("a butterfly", "butterfly"), ("a bee", "bee"),
            ("a robot", "robot"), ("a rabbit", "rabbit"), ("a person", "person"),
        )
        for index, (prompt, expected) in enumerate(prompts):
            path = tmp / f"mascot-{index}.ppm"
            assert procedural_art.make_mascot(prompt, path) == expected
            assert path.stat().st_size > 180 * 220 * 3
        for index, fruit in enumerate(("watermelon", "banana", "orange"), start=len(prompts)):
            path = tmp / f"fruit-{index}.ppm"
            assert procedural_art.make_mascot(f"a dancing {fruit}", path) == fruit
            assert path.stat().st_size > 180 * 220 * 3
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_font_name_is_validated():
    import os
    os.environ["WONDERTOONS_CAPTION_FONT"] = "Bad;Font`name"
    try:
        assert A.default_font() in ("FreeSans", "Nirmala UI")
    finally:
        del os.environ["WONDERTOONS_CAPTION_FONT"]


def _need_ffmpeg():
    if not (A.find_ffmpeg() and A.find_ffprobe()):
        raise unittest.SkipTest("ffmpeg/ffprobe not installed")


SCENES = [
    {"title": "Welcome", "visual_prompt": "a rabbit walks through a forest",
     "estimated_duration_seconds": 2, "caption_text": {"ta": "வணக்கம்!", "en": "Hello!"}},
    {"title": "Bye {\\evil}", "visual_prompt": "a dolphin swims underwater",
     "estimated_duration_seconds": 3, "caption_text": {"ta": "மீண்டும் சந்திப்போம்", "en": "Bye!"}},
]


def test_real_render_is_verified_playable_mp4():
    _need_ffmpeg()
    tmp = Path(tempfile.mkdtemp())
    try:
        events = []
        report = A.assemble(scenes=SCENES, work_dir=tmp / "w", out_path=tmp / "o" / "video.mp4",
                            options=A.RenderOptions("9:16", "480p", ["ta", "en"]),
                            ffmpeg=A.find_ffmpeg(), ffprobe=A.find_ffprobe(),
                            on_progress=lambda s, d, t: events.append((s, d, t)) or True)
        assert (tmp / "o" / "video.mp4").stat().st_size > 0
        assert (report["width"], report["height"]) == (480, 854)
        assert report["video_codec"] == "h264" and report["audio_codec"] == "aac"
        assert abs(report["measured_duration_seconds"] - 5) <= 1
        assert report["is_ai_generated_video"] is False and report["audio"] == "silent_placeholder"
        assert report["kind"] == "procedural_2d_animation"
        assert "prompt-keyword-selected" in report["renderer"]
        assert events[:2] == [("rendering_scenes", 1, 2), ("rendering_scenes", 2, 2)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_render_with_local_narration_and_synthesized_music():
    import os
    from app.services import local_audio

    _need_ffmpeg()
    if os.name != "nt":
        raise unittest.SkipTest("This narration test uses the installed Windows Speech voice.")
    tmp = Path(tempfile.mkdtemp())
    try:
        speech, music, mixed = tmp / "voice.wav", tmp / "music.wav", tmp / "mixed.wav"
        try:
            local_audio.synthesize_windows_speech("A rabbit learns to share.", "en", speech)
        except local_audio.AudioGenerationError as exc:
            if "No installed Windows speech voice" in str(exc):
                raise unittest.SkipTest(str(exc)) from exc
            raise
        local_audio.generate_music_bed(A.find_ffmpeg(), music, 5)
        local_audio.mix_audio(A.find_ffmpeg(), speech, music, mixed, 5)
        report = A.assemble(
            scenes=SCENES,
            work_dir=tmp / "work",
            out_path=tmp / "out" / "video.mp4",
            options=A.RenderOptions(
                resolution="480p",
                caption_languages=["en"],
                silent_audio=False,
                audio_description="narration_and_procedural_music",
            ),
            ffmpeg=A.find_ffmpeg(),
            ffprobe=A.find_ffprobe(),
            audio_file=mixed,
        )
        assert report["audio_codec"] == "aac"
        assert report["audio"] == "narration_and_procedural_music"
        assert abs(report["measured_duration_seconds"] - 5) <= 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cancellation_leaves_no_output_file():
    _need_ffmpeg()
    tmp = Path(tempfile.mkdtemp())
    try:
        try:
            A.assemble(scenes=SCENES, work_dir=tmp / "w", out_path=tmp / "o" / "video.mp4",
                       options=A.RenderOptions(), ffmpeg=A.find_ffmpeg(), ffprobe=A.find_ffprobe(),
                       on_progress=lambda *_: False)
        except A.AssemblyCancelled:
            assert not (tmp / "o" / "video.mp4").exists()
            return
        raise AssertionError("not cancelled")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_ffmpeg_binary_gives_clear_error():
    tmp = Path(tempfile.mkdtemp())
    try:
        try:
            A.assemble(scenes=SCENES, work_dir=tmp / "w", out_path=tmp / "o.mp4", options=A.RenderOptions(),
                       ffmpeg=str(tmp / "no-such-ffmpeg"), ffprobe="x")
        except A.AssemblyError as exc:
            assert "FFmpeg could not be started" in str(exc)
            return
        raise AssertionError("no error")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_installed_windows_voice_can_create_narration(tmp_path):
    import os
    from app.services.local_audio import AudioGenerationError, synthesize_windows_speech

    if os.name != "nt":
        raise unittest.SkipTest("Windows Speech is only available on Windows.")
    try:
        synthesize_windows_speech("This is a local narration check.", "en", tmp_path / "voice.wav")
    except AudioGenerationError as exc:
        if "No installed Windows speech voice" in str(exc):
            raise unittest.SkipTest(str(exc)) from exc
        raise
    assert (tmp_path / "voice.wav").stat().st_size > 1000


def test_verify_rejects_missing_and_empty_files():
    tmp = Path(tempfile.mkdtemp())
    try:
        for make in (lambda p: None, lambda p: p.write_bytes(b"")):
            p = tmp / "x.mp4"
            make(p)
            try:
                A.verify_output("ffprobe", p, 5, 480, 854, True)
            except A.AssemblyError as exc:
                assert "missing or empty" in str(exc)
                continue
            raise AssertionError("accepted bad file")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
