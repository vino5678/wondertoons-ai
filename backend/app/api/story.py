from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.core.errors import ConflictError, InvalidInputError
from app.providers.registry import get_story_provider
from app.schemas.common import ErrorResponse
from app.schemas.job import JobOut
from app.schemas.story import Scene, ScenePlanRescale, ScenePlanUpdate, StoryPlan, StoryRequest
from app.services import jobs, projects as svc, scene_planner, story_engine
from app.workers.story_job import run_story_job

router = APIRouter(prefix="/projects/{project_id}", tags=["story and scenes"])
_404 = {404: {"model": ErrorResponse, "description": "Project (or its story) not found"}}


@router.post("/story", response_model=JobOut, status_code=202, responses=_404,
             summary="Start story + scene-plan generation (background job)")
def start_story(project_id: str, body: StoryRequest, request: Request, db: Session = Depends(get_db),
                settings: Settings = Depends(get_settings)):
    """Returns 202 with a job. Poll `GET /jobs/{id}`; when `completed`, read `GET /projects/{id}/story`.
    Language support is checked immediately (422); provider errors (e.g. missing credentials)
    appear as a `failed` job with an actionable `error_message`."""
    project = svc.get_project_or_404(db, project_id)
    provider_name = (project.provider_settings or {}).get("story_provider", settings.story_provider)
    if not isinstance(provider_name, str):
        raise InvalidInputError("provider_settings.story_provider must be a string.")
    story_engine.check_languages(body, settings)
    job = jobs.create_job(db, project_id, "story_generation")
    request.app.state.job_runner.submit(
        run_story_job, request.app.state.session_factory, settings, job.id, project_id,
        body.model_dump(mode="json"), provider_name)
    db.expire_all()
    return jobs.get_job_or_404(db, job.id)


@router.get("/story", response_model=StoryPlan, responses=_404, summary="Get the saved story and scene plan")
def get_story(project_id: str, db: Session = Depends(get_db)):
    return svc.load_story_plan(svc.get_project_or_404(db, project_id))


@router.get("/scenes", response_model=List[Scene], responses=_404, summary="List scenes in order")
def get_scenes(project_id: str, db: Session = Depends(get_db)):
    return svc.load_story_plan(svc.get_project_or_404(db, project_id)).scenes


@router.put("/scenes", response_model=List[Scene], responses={**_404, 422: {"model": ErrorResponse}},
            summary="Save an edited scene plan")
def save_scenes(project_id: str, body: ScenePlanUpdate, db: Session = Depends(get_db)):
    """Replaces scenes. Durations must sum to the story's planned total within
    max(2s, 2%) (422 otherwise). Order and previous/next links are recomputed."""
    project = svc.get_project_or_404(db, project_id)
    plan = svc.load_story_plan(project)
    scenes = scene_planner.relink_scenes(list(body.scenes))
    scene_planner.validate_total(scenes, plan.total_duration_seconds)
    project.scenes = [s.model_dump(mode="json") for s in scenes]
    db.commit()
    return scenes


@router.post("/scenes/plan", response_model=List[Scene], responses={**_404, 409: {"model": ErrorResponse}},
             summary="Rescale scene durations to a new total")
def rescale(project_id: str, body: ScenePlanRescale, db: Session = Depends(get_db)):
    """Proportionally rescales existing scene durations (sum becomes exactly the new total).
    It does not rewrite scene text; re-run `POST /story` for that."""
    project = svc.get_project_or_404(db, project_id)
    plan = svc.load_story_plan(project)
    if body.total_duration_seconds < len(plan.scenes):
        raise InvalidInputError(f"Total must be at least {len(plan.scenes)}s (one second per scene).")
    scenes = scene_planner.rescale_scenes(plan.scenes, body.total_duration_seconds)
    plan.total_duration_seconds = body.total_duration_seconds
    plan.duration_tolerance_seconds = scene_planner.tolerance_seconds(body.total_duration_seconds)
    svc.save_story_plan(project, plan)
    db.commit()
    return scenes
