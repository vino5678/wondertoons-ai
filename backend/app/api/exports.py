import json
from pathlib import PurePosixPath
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.core.errors import AppError, ConflictError, InvalidInputError, NotFoundError
from app.core.paths import safe_join
from app.schemas.common import ErrorResponse
from app.schemas.export import ExportOut, ExportRequest
from app.schemas.job import JobOut
from app.services import assembly, jobs, projects as svc
from app.workers.export_job import effective_languages, run_export_job

router = APIRouter(prefix="/projects/{project_id}/exports", tags=["export"])
_404 = {404: {"model": ErrorResponse, "description": "Not found"}}
_MEDIA = {".mp4": "video/mp4", ".srt": "application/x-subrip", ".vtt": "text/vtt", ".json": "application/json"}
_KIND = {".mp4": "video", ".srt": "subtitles_srt", ".vtt": "subtitles_vtt", ".json": "manifest"}


@router.post("", response_model=JobOut, status_code=202, responses={**_404, 409: {"model": ErrorResponse},
             503: {"model": ErrorResponse}}, summary="Render a local animated MP4 (background job)")
def start_export(project_id: str, body: ExportRequest, request: Request, db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings)):
    """Renders the saved scene plan into a verified H.264/AAC MP4 with captions.
    The default renderer is procedural 2D animation, not AI-generated video. Poll `GET /jobs/{id}`."""
    project = svc.get_project_or_404(db, project_id)
    if project.story is None:
        raise ConflictError("Generate a story before exporting.", hint="Use POST /projects/{id}/story first.")
    plan = svc.load_story_plan(project)
    available = {lang for s in plan.scenes for lang in s.caption_text}
    langs = effective_languages(body, [plan.target_language] + plan.subtitle_languages)
    missing = [l for l in langs if l not in available]
    if missing:
        raise InvalidInputError(f"No caption text in the scene plan for: {', '.join(missing)}.",
                                hint=f"Available caption languages: {', '.join(sorted(available))}.")
    if not (assembly.find_ffmpeg() and assembly.find_ffprobe()):
        raise AppError(503, "ffmpeg_not_found", "FFmpeg (ffmpeg and ffprobe) was not found on this computer.",
                       "Install FFmpeg, add it to PATH, or set WONDERTOONS_FFMPEG_PATH, then restart the backend.")
    job = jobs.create_job(db, project_id, "export")
    request.app.state.job_runner.submit(run_export_job, request.app.state.session_factory, settings, job.id,
                                        project_id, body.model_dump(mode="json"))
    db.expire_all()
    return jobs.get_job_or_404(db, job.id)


@router.get("", response_model=List[ExportOut], responses=_404, summary="Completed exports (newest first)")
def list_exports(project_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    svc.get_project_or_404(db, project_id)
    out: List[ExportOut] = []
    for job in jobs.list_project_jobs(db, project_id):
        if job.kind != "export" or job.status != "completed":
            continue
        files, manifest = [], None
        for rel in job.output_files or []:
            path = safe_join(settings.projects_dir, f"{project_id}/{rel}")
            if not path.is_file():
                continue
            name = PurePosixPath(rel).name
            suffix = PurePosixPath(rel).suffix.lower()
            files.append({"name": name, "kind": _KIND.get(suffix, "file"), "size_bytes": path.stat().st_size,
                          "url": f"/projects/{project_id}/exports/{job.id}/files/{name}"})
            if name == "manifest.json":
                manifest = json.loads(path.read_text(encoding="utf-8"))
        if any(f["kind"] == "video" for f in files):  # only list exports whose video still exists
            out.append(ExportOut(job_id=job.id, status=job.status, created_at=job.created_at,
                                 kind=manifest.get("kind", "unknown") if manifest else "unknown",
                                 files=files, manifest=manifest))
    return out


@router.get("/{job_id}/files/{filename}", responses=_404, summary="Download or stream an exported file")
def get_export_file(project_id: str, job_id: str, filename: str, download: bool = Query(False),
                    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Only files recorded by a COMPLETED export job can be fetched."""
    job = jobs.get_job_or_404(db, job_id)
    if job.project_id != project_id or job.kind != "export" or job.status != "completed":
        raise NotFoundError("Export", job_id)
    rel = next((r for r in (job.output_files or []) if PurePosixPath(r).name == filename), None)
    if rel is None:
        raise NotFoundError("Export file", filename)
    path = safe_join(settings.projects_dir, f"{project_id}/{rel}")
    if not path.is_file():
        raise NotFoundError("Export file", filename)
    media = _MEDIA.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media, filename=filename) if download else FileResponse(path, media_type=media)
