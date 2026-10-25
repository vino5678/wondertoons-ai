from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone

from sqlalchemy import update

from app.core.config import Settings
from app.core.errors import AppError
from app.core.paths import safe_join
from app.models.orm import JobRow, ProjectRow, utcnow
from app.schemas.export import ExportRequest
from app.services import assembly, captions, jobs, local_audio, projects

log = logging.getLogger("wondertoons.export")

# Stage values; rendering_scenes progress is MEASURED (scenes finished / scenes total).
FIXED = {"preparing": 2, "writing_captions": 4, "preparing_audio": 8,
         "assembling_video": 92, "verifying_output": 96}


def effective_languages(request: ExportRequest, plan_langs: list[str]) -> list[str]:
    return request.caption_languages or plan_langs


def run_export_job(session_factory, settings: Settings, job_id: str, project_id: str, request_dict: dict) -> None:
    db = session_factory()
    work_dir = settings.temp_dir / "export" / job_id
    export_dir = None
    try:
        if not jobs.advance(db, job_id, status="running", stage="preparing", progress=FIXED["preparing"],
                            progress_kind="stage_based"):
            return
        request = ExportRequest.model_validate(request_dict)
        project = db.get(ProjectRow, project_id)
        if project is None:
            return
        plan = projects.load_story_plan(project)
        scenes = [s.model_dump(mode="json") for s in plan.scenes]
        langs = effective_languages(request, [plan.target_language] + [l for l in plan.subtitle_languages
                                                                      if l != plan.target_language])
        ffmpeg, ffprobe = assembly.find_ffmpeg(), assembly.find_ffprobe()
        if not ffmpeg or not ffprobe:
            raise AppError(503, "ffmpeg_not_found", "FFmpeg (ffmpeg and ffprobe) was not found.",
                           "Install FFmpeg, add it to PATH, or set WONDERTOONS_FFMPEG_PATH.")

        export_dir = safe_join(settings.projects_dir, f"{project_id}/exports/{job_id}")
        export_dir.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        if not jobs.advance(db, job_id, stage="writing_captions", progress=FIXED["writing_captions"]):
            return
        warnings = ["Caption timing is estimated from scene durations; it is not aligned to speech."]
        written = []
        for lang in langs:
            cues = captions.build_cues(scenes, lang)
            if not cues:
                raise AppError(422, "no_captions", f"No caption text exists for language '{lang}'.")
            problems = captions.validate_cues(cues)
            if problems:
                raise AppError(422, "invalid_captions", "Caption timing is invalid: " + " ".join(problems[:3]))
            warnings += captions.reading_speed_warnings(cues)
            for ext, render in (("srt", captions.to_srt), ("vtt", captions.to_vtt)):
                name = f"captions_{lang}.{ext}"
                (export_dir / name).write_text(render(cues), encoding="utf-8")
                written.append(name)

        audio_path = None
        speech_path = None
        music_path = None
        audio_description = "silent_placeholder"
        if request.narration or request.background_music:
            if not jobs.advance(db, job_id, stage="preparing_audio", progress=FIXED["preparing_audio"],
                                progress_kind="stage_based"):
                return
            duration = float(sum(scene["estimated_duration_seconds"] for scene in scenes))
            if request.narration:
                speech_text = "\n\n".join(
                    "\n".join(filter(None, [scene.get("narration", "")] +
                                     [line.get("text", "") for line in scene.get("dialogue", [])]))
                    for scene in scenes
                )
                try:
                    speech_path = work_dir / "narration.wav"
                    local_audio.synthesize_windows_speech(speech_text, plan.target_language, speech_path)
                except local_audio.AudioGenerationError as exc:
                    warnings.append(f"Narration was requested but is unavailable: {exc} Video rendering continues.")
                    speech_path = None
            if request.background_music:
                try:
                    music_path = work_dir / "music_bed.wav"
                    local_audio.generate_music_bed(ffmpeg, music_path, duration)
                except local_audio.AudioGenerationError as exc:
                    warnings.append(f"Background music was requested but is unavailable: {exc} Video rendering continues.")
                    music_path = None

            if speech_path and music_path:
                try:
                    audio_path = work_dir / "mixed_audio.wav"
                    local_audio.mix_audio(ffmpeg, speech_path, music_path, audio_path, duration)
                except local_audio.AudioGenerationError as exc:
                    warnings.append(f"Audio mixing failed: {exc} Narration is kept without music.")
                    audio_path = speech_path
            else:
                audio_path = speech_path or music_path
            if audio_path:
                audio_description = "narration_and_procedural_music" if speech_path and music_path else (
                    "local_windows_narration" if speech_path else "procedural_synthesized_music")

        def on_progress(stage: str, done: int, total: int) -> bool:
            if stage == "rendering_scenes":
                return jobs.advance(db, job_id, stage=stage, progress=5 + int(85 * done / total),
                                    progress_kind="scene_count")
            return jobs.advance(db, job_id, stage=stage, progress=FIXED[stage], progress_kind="stage_based")

        story_request = project.story_request or {}
        options = assembly.RenderOptions(
            aspect_ratio=request.aspect_ratio.value,
            resolution=request.resolution.value,
            caption_languages=langs,
            burn_captions=request.burn_captions,
            silent_audio=request.include_silent_audio and audio_path is None,
            renderer=request.renderer.value,
            video_title=request.title or plan.title,
            visual_style=story_request.get("animation_style", "colorful 2D cartoon"),
            audio_description=audio_description,
        )
        report = assembly.assemble(scenes=scenes, work_dir=work_dir, out_path=export_dir / "video.mp4",
                                   options=options, ffmpeg=ffmpeg, ffprobe=ffprobe, on_progress=on_progress,
                                   audio_file=audio_path)
        report["subtitle_files"] = written
        report["warnings"] = warnings
        report["created_at"] = datetime.now(timezone.utc).isoformat()
        (export_dir / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        rels = [f"exports/{job_id}/{n}" for n in ["video.mp4", *written, "manifest.json"]]
        res = db.execute(update(JobRow).where(JobRow.id == job_id, JobRow.status.in_(jobs.ACTIVE)).values(
            status="completed", stage="completed", progress=100, output_files=rels, updated_at=utcnow()))
        db.commit()
        if res.rowcount != 1:  # cancelled at the last moment: discard
            shutil.rmtree(export_dir, ignore_errors=True)
    except assembly.AssemblyCancelled:
        if export_dir:
            shutil.rmtree(export_dir, ignore_errors=True)
    except (AppError, assembly.AssemblyError) as exc:
        db.rollback()
        message = exc.message + (f" Hint: {exc.hint}" if getattr(exc, "hint", None) else "") \
            if isinstance(exc, AppError) else str(exc)
        jobs.advance(db, job_id, status="failed", stage="failed", error_message=message)
        if export_dir:
            shutil.rmtree(export_dir, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("Export job %s crashed", job_id)
        jobs.advance(db, job_id, status="failed", stage="failed",
                     error_message=f"Unexpected internal error ({type(exc).__name__}); see the server log.")
        if export_dir:
            shutil.rmtree(export_dir, ignore_errors=True)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        db.close()
