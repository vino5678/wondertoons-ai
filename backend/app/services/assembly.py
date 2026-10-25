"""Video assembly with FFmpeg (procedural 2D or storyboard-preview renderer).

The default renderer creates geometric scene art and moves a simple mascot; the
legacy renderer creates solid-colour title cards. Both can include burned-in
captions (ASS subtitles rendered by libass, which shapes Tamil correctly when a
Tamil-capable font is installed). Scene clips are concatenated and muxed with
optional local audio. The output is a playable H.264/AAC MP4, not AI-generated
video, and every report says so.

Safety: FFmpeg is always started with an argument LIST (never a shell string),
user text only ever goes into .ass files after escaping, and every file name
passed to FFmpeg is generated here.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.services import procedural_art

ASPECTS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1)}
RESOLUTIONS = {"480p": 480, "720p": 720, "1080p": 1080}
PALETTE = ["2D6CDF", "E0702F", "2A9D78", "8A52D1", "D0407A"]  # RGB hex, kid-friendly, dark enough for white text
FPS = 24
FADE_SECONDS = 0.3
FONT_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,60}$")


class AssemblyError(Exception):
    """A readable, user-facing assembly failure."""


class AssemblyCancelled(Exception):
    pass


@dataclass
class RenderOptions:
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    caption_languages: list = field(default_factory=list)
    burn_captions: bool = True
    silent_audio: bool = True
    renderer: str = "procedural_2d"
    video_title: str = ""
    visual_style: str = "colorful 2D cartoon"
    audio_description: str = "silent_placeholder"


# ---------- tools ----------
def find_ffmpeg() -> Optional[str]:
    configured = os.environ.get("WONDERTOONS_FFMPEG_PATH")
    if configured:
        return configured
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    return _find_winget_ffmpeg("ffmpeg.exe")


def find_ffprobe() -> Optional[str]:
    if os.environ.get("WONDERTOONS_FFPROBE_PATH"):
        return os.environ["WONDERTOONS_FFPROBE_PATH"]
    ff = os.environ.get("WONDERTOONS_FFMPEG_PATH")
    if ff:
        sibling = Path(ff).with_name("ffprobe.exe" if ff.lower().endswith(".exe") else "ffprobe")
        if sibling.exists():
            return str(sibling)
    on_path = shutil.which("ffprobe")
    if on_path:
        return on_path
    return _find_winget_ffmpeg("ffprobe.exe")


def _find_winget_ffmpeg(executable: str) -> Optional[str]:
    """Find the standard WinGet Gyan package when the current shell has a stale PATH."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    candidates = sorted(packages.glob(f"Gyan.FFmpeg.Shared_*/ffmpeg-*/bin/{executable}"))
    return str(candidates[-1]) if candidates else None


def default_font() -> str:
    configured = os.environ.get("WONDERTOONS_CAPTION_FONT", "").strip()
    if configured and FONT_RE.match(configured):
        return configured
    return "Nirmala UI" if os.name == "nt" else "FreeSans"  # both cover Tamil and Latin


# ---------- pure helpers ----------
def _even(x: float) -> int:
    return int(round(x / 2)) * 2


def output_size(aspect_ratio: str, resolution: str) -> tuple[int, int]:
    if aspect_ratio not in ASPECTS or resolution not in RESOLUTIONS:
        raise AssemblyError(f"Unsupported aspect ratio / resolution: {aspect_ratio} / {resolution}.")
    short = RESOLUTIONS[resolution]
    aw, ah = ASPECTS[aspect_ratio]
    return (_even(short * aw / ah), short) if aw >= ah else (short, _even(short * ah / aw))


def ass_escape(text: str) -> str:
    """Neutralise ASS override syntax in user text and flatten to one line."""
    return " ".join(str(text).replace("\\", "/").replace("{", "(").replace("}", ")").split())


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def build_scene_ass(width: int, height: int, duration: float, title: str, caption_lines: list[str],
                    label: str, font: str, video_title: str = "") -> str:
    short = min(width, height)
    margin = int(short * 0.06)
    title_size, cap_size, label_size = int(short * 0.075), int(short * 0.052), int(short * 0.03)
    outline = max(2, int(short * 0.004))
    end = ass_time(duration + 1)
    cap = r"\N".join(ass_escape(l) for l in caption_lines if l.strip())
    fmt = ("Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
           "MarginL, MarginR, MarginV, Encoding")
    style = lambda n, size, bold, align, mv: (  # noqa: E731
        f"Style: {n},{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,{bold},0,0,0,100,100,0,0,1,"
        f"{outline},1,{align},{margin},{margin},{mv},1")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", f"Format: {fmt}",
        style("Title", title_size, 1, 5, 0),
        style("Caption", cap_size, 1, 2, int(short * 0.07)),
        style("Label", label_size, 0, 7, int(margin * 0.6)),
        style("VideoTitle", label_size, 1, 8, int(margin * 0.6)),
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,0:00:00.00,{end},Label,,0,0,0,,{ass_escape(label)}",
        f"Dialogue: 1,0:00:00.00,{end},VideoTitle,,0,0,0,,{ass_escape(video_title)}" if video_title else "",
        f"Dialogue: 0,0:00:00.00,{end},Title,,0,0,0,,{{\\fad(250,250)}}{ass_escape(title)}",
    ]
    if cap:
        lines.append(f"Dialogue: 0,0:00:00.20,{end},Caption,,0,0,0,,{{\\fad(250,250)}}{cap}")
    return "\n".join(lines) + "\n"


def scene_clip_args(ffmpeg: str, width: int, height: int, duration: float, bg_hex: str,
                    ass_name: str, out_name: str) -> list[str]:
    """Argument LIST for one video-only scene clip. Run with cwd = the work dir."""
    fade_out_at = max(duration - FADE_SECONDS, 0.0)
    vf = f"ass={ass_name},fade=t=in:st=0:d={FADE_SECONDS},fade=t=out:st={fade_out_at:.3f}:d={FADE_SECONDS}"
    return [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=0x{bg_hex}:s={width}x{height}:r={FPS}:d={duration:.3f}",
        "-vf", vf, "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-g", str(FPS * 2), "-an", out_name,
    ]


def procedural_clip_args(ffmpeg: str, width: int, height: int, duration: float, background_name: str,
                         mascot_name: str, ass_name: str, out_name: str, motion: str = "walk") -> list[str]:
    """Render a procedural scene with prompt-selected character movement."""
    fade_out_at = max(duration - FADE_SECONDS, 0.0)
    mascot_height = max(80, int(height * 0.43))
    movements = {
        "walk": ("(W-w)/2+sin(2*PI*t/7)*W*0.18", "H*0.47+sin(2*PI*t/1.25)*H*0.025"),
        "fly": ("(W-w)/2+sin(2*PI*t/5)*W*0.3", "H*0.36+sin(2*PI*t/2)*H*0.1"),
        "swim": ("(W-w)/2+sin(2*PI*t/6)*W*0.25", "H*0.49+sin(2*PI*t/0.8)*H*0.035"),
        "dance": ("(W-w)/2+sin(2*PI*t/2)*W*0.08", "H*0.47+abs(sin(2*PI*t/1.1))*H*0.08"),
        "jump": ("(W-w)/2+sin(2*PI*t/3)*W*0.14", "H*0.44-abs(sin(2*PI*t/1.7))*H*0.15"),
        "freeze": ("(W-w)/2", "H*0.47"),
        "rest": ("(W-w)/2", "H*0.49+sin(2*PI*t/3)*H*0.008"),
    }
    x_motion, y_motion = movements.get(motion, movements["walk"])
    filters = (
        f"[0:v]scale={width}:{height}:flags=lanczos,setsar=1[bg];"
        f"[1:v]colorkey=0x00FF00:0.18:0.08,scale=-1:{mascot_height}[mascot];"
        f"[bg][mascot]overlay=x='{x_motion}':y='{y_motion}':shortest=1,"
        f"ass={ass_name},fade=t=in:st=0:d={FADE_SECONDS},"
        f"fade=t=out:st={fade_out_at:.3f}:d={FADE_SECONDS},format=yuv420p[v]"
    )
    return [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-f", "image2", "-loop", "1", "-framerate", str(FPS), "-i", background_name,
        "-f", "image2", "-loop", "1", "-framerate", str(FPS), "-i", mascot_name,
        "-filter_complex", filters, "-map", "[v]", "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", out_name,
    ]


def final_mux_args(ffmpeg: str, list_name: str, out_name: str, silent_audio: bool,
                   audio_file: Optional[str] = None, duration: Optional[float] = None) -> list[str]:
    args = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", list_name]
    if audio_file:
        if duration is None:
            raise AssemblyError("A target duration is required when adding audio.")
        args += ["-i", audio_file, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                 "-b:a", "128k", "-af", "apad", "-t", f"{duration:.3f}"]
    elif silent_audio:
        args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        args += ["-c", "copy"]
    return args + ["-movflags", "+faststart", out_name]


# ---------- running ffmpeg / ffprobe ----------
def _run(args: list[str], cwd: Path, timeout: int) -> None:
    try:
        proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, shell=False)
    except FileNotFoundError as exc:
        raise AssemblyError("FFmpeg could not be started. Install FFmpeg and add it to PATH "
                            "(or set WONDERTOONS_FFMPEG_PATH).") from exc
    except subprocess.TimeoutExpired as exc:
        raise AssemblyError(f"FFmpeg did not finish within {timeout} seconds and was stopped.") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-600:]
        raise AssemblyError(f"FFmpeg failed (exit code {proc.returncode}): {tail}")


def probe_media(ffprobe: str, path: Path) -> dict:
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
             "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, shell=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise AssemblyError("ffprobe could not be run, so the output file could not be verified.") from exc
    if proc.returncode != 0:
        raise AssemblyError(f"ffprobe could not read the output file: {(proc.stderr or '').strip()[-300:]}")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0) or 0), "size": int(fmt.get("size", 0) or 0),
        "video_codec": video.get("codec_name") if video else None,
        "width": video.get("width") if video else None, "height": video.get("height") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
    }


def verify_output(ffprobe: str, path: Path, expected_seconds: float, width: int, height: int,
                  expect_audio: bool) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssemblyError("The exported file is missing or empty.")
    info = probe_media(ffprobe, path)
    if info["video_codec"] != "h264":
        raise AssemblyError(f"Output video codec is {info['video_codec']}, expected h264.")
    if (info["width"], info["height"]) != (width, height):
        raise AssemblyError(f"Output size is {info['width']}x{info['height']}, expected {width}x{height}.")
    if expect_audio and info["audio_codec"] != "aac":
        raise AssemblyError("The exported file has no AAC audio track.")
    tolerance = max(1.0, 0.01 * expected_seconds)
    if abs(info["duration"] - expected_seconds) > tolerance:
        raise AssemblyError(f"Output is {info['duration']:.1f}s long but {expected_seconds:.1f}s was planned "
                            f"(tolerance {tolerance:.1f}s).")
    return info


# ---------- orchestration ----------
ProgressFn = Callable[[str, int, int], bool]  # (stage, done, total) -> keep_going


def assemble(*, scenes: list[dict], work_dir: Path, out_path: Path, options: RenderOptions,
             ffmpeg: str, ffprobe: str, font: Optional[str] = None,
             on_progress: Optional[ProgressFn] = None, audio_file: Optional[Path] = None) -> dict:
    """Render the scene plan to out_path and return a verification report."""
    if not scenes:
        raise AssemblyError("The scene plan is empty; there is nothing to render.")
    width, height = output_size(options.aspect_ratio, options.resolution)
    font = font or default_font()
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(scenes)
    notify = on_progress or (lambda *_: True)

    if options.renderer not in {"procedural_2d", "storyboard_preview"}:
        raise AssemblyError(f"Unsupported video renderer: {options.renderer}.")

    clip_names = []
    for i, scene in enumerate(scenes, start=1):
        duration = float(scene["estimated_duration_seconds"])
        captions = []
        if options.burn_captions:
            for lang in options.caption_languages:
                text = (scene.get("caption_text") or {}).get(lang, "")
                if text:
                    captions.append(text)
        ass_name, clip_name = f"scene_{i:04d}.ass", f"scene_{i:04d}.mp4"
        if options.renderer == "procedural_2d":
            scene_text = f"{scene.get('visual_prompt', '')} {scene.get('description', '')}"
            background_name = f"background_{i:04d}.ppm"
            procedural_art.make_background(
                scene_text, options.visual_style, i, work_dir / background_name,
            )
            mascot_name = f"character_{i:04d}.ppm"
            procedural_art.make_mascot(scene_text, work_dir / mascot_name)
            label = f"PROCEDURAL 2D ANIMATION | Scene {i} of {total} | not AI-generated video"
        else:
            background_name = ""
            label = f"STORYBOARD PREVIEW | Scene {i} of {total} | not AI-generated video"
        (work_dir / ass_name).write_text(
            build_scene_ass(width, height, duration, str(scene.get("title", "")), captions, label, font,
                            options.video_title),
            encoding="utf-8")
        if options.renderer == "procedural_2d":
            motion = procedural_art.motion_kind(scene_text)
            args = procedural_clip_args(ffmpeg, width, height, duration, background_name, mascot_name, ass_name,
                                        clip_name, motion)
        else:
            args = scene_clip_args(ffmpeg, width, height, duration, PALETTE[(i - 1) % len(PALETTE)],
                                   ass_name, clip_name)
        _run(args, work_dir, timeout=600)
        clip_names.append(clip_name)
        if not notify("rendering_scenes", i, total):
            raise AssemblyCancelled()

    if not notify("assembling_video", 0, 1):
        raise AssemblyCancelled()
    (work_dir / "concat.txt").write_text("".join(f"file '{n}'\n" for n in clip_names), encoding="utf-8")
    tmp_out = "final_tmp.mp4"
    expected = float(sum(s["estimated_duration_seconds"] for s in scenes))
    audio_name = str(audio_file.resolve()) if audio_file else None
    _run(final_mux_args(ffmpeg, "concat.txt", tmp_out, options.silent_audio, audio_name, expected),
         work_dir, timeout=3600)

    if not notify("verifying_output", 0, 1):
        raise AssemblyCancelled()
    info = verify_output(ffprobe, work_dir / tmp_out, expected, width, height,
                         options.silent_audio or audio_file is not None)
    shutil.move(str(work_dir / tmp_out), str(out_path))  # only a verified file reaches the exports folder

    return {
        "kind": "procedural_2d_animation" if options.renderer == "procedural_2d" else "storyboard_preview",
        "is_ai_generated_video": False,
        "renderer": ("prompt-keyword-selected procedural settings, props, creatures and movement with FFmpeg scene transitions"
                     if options.renderer == "procedural_2d" else "ffmpeg title cards with burned-in captions"),
        "visual_generation": "procedural; no AI model or generated images",
        "video_title": options.video_title,
        "width": width, "height": height, "fps": FPS,
        "aspect_ratio": options.aspect_ratio, "resolution": options.resolution,
        "scene_count": total,
        "expected_duration_seconds": expected, "measured_duration_seconds": round(info["duration"], 2),
        "video_codec": info["video_codec"], "audio_codec": info["audio_codec"],
        "audio": options.audio_description if audio_file else (
            "silent_placeholder" if options.silent_audio else "none"),
        "burned_caption_languages": list(options.caption_languages) if options.burn_captions else [],
        "size_bytes": out_path.stat().st_size,
    }
