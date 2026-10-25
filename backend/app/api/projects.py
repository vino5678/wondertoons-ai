from typing import List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings
from app.core.config import Settings
from app.schemas.common import ErrorResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import projects as svc

router = APIRouter(prefix="/projects", tags=["projects"])
_404 = {404: {"model": ErrorResponse, "description": "Project not found"}}


@router.post("", response_model=ProjectOut, status_code=201, summary="Create a project")
def create_project(body: ProjectCreate, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Creates the project and its folder under data/projects. `provider_settings` must not contain secrets (422)."""
    return svc.to_out(db, svc.create_project(db, settings, body))


@router.get("", response_model=List[ProjectOut], summary="List projects (newest first)")
def list_projects(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return [svc.to_out(db, r) for r in svc.list_projects(db, limit, offset)]


@router.get("/{project_id}", response_model=ProjectOut, responses=_404, summary="Get a project")
def get_project(project_id: str, db: Session = Depends(get_db)):
    return svc.to_out(db, svc.get_project_or_404(db, project_id))


@router.patch("/{project_id}", response_model=ProjectOut, responses=_404, summary="Update a project")
def update_project(project_id: str, body: ProjectUpdate, db: Session = Depends(get_db)):
    row = svc.get_project_or_404(db, project_id)
    return svc.to_out(db, svc.update_project(db, row, body))


@router.delete("/{project_id}", status_code=204, responses=_404, summary="Delete a project and its files")
def delete_project(project_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    svc.delete_project(db, settings, svc.get_project_or_404(db, project_id))
    return Response(status_code=204)
