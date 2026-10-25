from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.core.config import Settings
from app.core.errors import AppError
from app.models.orm import CharacterRow, JobRow, ProjectRow, utcnow
from app.providers.registry import get_story_provider
from app.schemas.story import StoryRequest
from app.services import characters as char_service
from app.services import jobs, projects, story_engine

log = logging.getLogger("wondertoons.jobs")

# Progress values are FIXED PER STAGE, not measured. JobOut.progress_kind says "stage_based".
STAGES = {
    "validating_request": 5,
    "loading_characters": 15,
    "generating_story": 30,
    "planning_scenes": 65,
    "saving": 90,
}


def run_story_job(session_factory, settings: Settings, job_id: str, project_id: str,
                  request_dict: dict, provider_name: str) -> None:
    db = session_factory()
    try:
        if not jobs.advance(db, job_id, status="running", stage="validating_request", progress=STAGES["validating_request"]):
            return  # cancelled before start
        request = StoryRequest.model_validate(request_dict)

        if not jobs.advance(db, job_id, stage="loading_characters", progress=STAGES["loading_characters"]):
            return
        project = db.get(ProjectRow, project_id)
        if project is None:
            return
        wanted = request.character_ids or projects.selected_character_ids(db, project_id)
        rows = list(db.scalars(select(CharacterRow).where(CharacterRow.id.in_(wanted)))) if wanted else []
        missing = sorted(set(wanted) - {r.id for r in rows})
        if missing:
            raise AppError(422, "unknown_character", f"Unknown character id(s): {', '.join(missing)}.")
        order = {cid: i for i, cid in enumerate(wanted)}
        characters = [char_service.as_prompt_dict(r) for r in sorted(rows, key=lambda r: order[r.id])]

        if not jobs.advance(db, job_id, stage="generating_story", progress=STAGES["generating_story"]):
            return
        provider = get_story_provider(provider_name, settings)
        raw = story_engine.generate_raw(request, characters, provider, settings)

        if not jobs.advance(db, job_id, stage="planning_scenes", progress=STAGES["planning_scenes"]):
            return
        plan = story_engine.build_plan(request, raw, characters, provider)

        if not jobs.advance(db, job_id, stage="saving", progress=STAGES["saving"]):
            return
        project = db.get(ProjectRow, project_id)
        if project is None:
            return
        projects.save_story_plan(project, plan)
        project.story_request = request.model_dump(mode="json")
        res = db.execute(update(JobRow).where(JobRow.id == job_id, JobRow.status.in_(jobs.ACTIVE))
                         .values(status="completed", stage="completed", progress=100, updated_at=utcnow()))
        if res.rowcount != 1:  # cancelled while saving: discard the result
            db.rollback()
            return
        db.commit()
    except AppError as exc:
        db.rollback()
        jobs.advance(db, job_id, status="failed", stage="failed", error_message=exc.message
                     + (f" Hint: {exc.hint}" if exc.hint else ""))
    except Exception as exc:  # noqa: BLE001 - never leak internals/secrets to the API
        db.rollback()
        log.exception("Story job %s crashed", job_id)
        jobs.advance(db, job_id, status="failed", stage="failed",
                     error_message=f"Unexpected internal error ({type(exc).__name__}); see the server log.")
    finally:
        db.close()
