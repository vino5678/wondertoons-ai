from __future__ import annotations

import shutil
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.paths import safe_join
from app.models.orm import ProjectCharacterRow, ProjectRow, new_id
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.schemas.story import Scene, StoryPlan


def get_project_or_404(db: Session, pid: str) -> ProjectRow:
    row = db.get(ProjectRow, pid)
    if row is None:
        raise NotFoundError("Project", pid)
    return row


def create_project(db: Session, settings: Settings, data: ProjectCreate) -> ProjectRow:
    row = ProjectRow(id=new_id("prj"), title=data.title, prompt=data.prompt, provider_settings=data.provider_settings)
    db.add(row)
    db.commit()
    safe_join(settings.projects_dir, row.id).mkdir(parents=True, exist_ok=True)
    return row


def list_projects(db: Session, limit: int, offset: int) -> List[ProjectRow]:
    stmt = select(ProjectRow).order_by(ProjectRow.created_at.desc(), ProjectRow.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def update_project(db: Session, row: ProjectRow, data: ProjectUpdate) -> ProjectRow:
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, key, value)
    db.commit()
    return row


def delete_project(db: Session, settings: Settings, row: ProjectRow) -> None:
    pid = row.id
    db.delete(row)  # jobs and character links cascade
    db.commit()
    folder = safe_join(settings.projects_dir, pid)  # restricted to the projects directory
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


def selected_character_ids(db: Session, pid: str) -> List[str]:
    return list(db.scalars(select(ProjectCharacterRow.character_id).where(ProjectCharacterRow.project_id == pid)
                           .order_by(ProjectCharacterRow.selected_at, ProjectCharacterRow.character_id)))


def to_out(db: Session, row: ProjectRow) -> ProjectOut:
    return ProjectOut(
        id=row.id, title=row.title, prompt=row.prompt, provider_settings=row.provider_settings or {},
        has_story=row.story is not None, scene_count=len(row.scenes or []),
        selected_character_ids=selected_character_ids(db, row.id),
        created_at=row.created_at, updated_at=row.updated_at,
    )


def load_story_plan(row: ProjectRow) -> StoryPlan:
    if row.story is None:
        raise NotFoundError("Story for project", row.id)
    return StoryPlan(**row.story, scenes=[Scene(**s) for s in (row.scenes or [])])


def save_story_plan(row: ProjectRow, plan: StoryPlan) -> None:
    row.story = plan.model_dump(mode="json", exclude={"scenes"})
    row.scenes = [s.model_dump(mode="json") for s in plan.scenes]
