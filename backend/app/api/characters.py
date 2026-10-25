from typing import List

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.orm import CharacterRow, ProjectCharacterRow
from app.schemas.character import (AppearanceOut, CharacterCreate, CharacterDraft, CharacterGenerationRequest,
                                   CharacterOut, CharacterUpdate, SimilarityCheckRequest, SimilarityReport)
from app.schemas.common import ErrorResponse
from app.services import characters as svc
from app.services import projects as project_svc

router = APIRouter(tags=["characters"])
_404 = {404: {"model": ErrorResponse, "description": "Not found"}}


@router.post("/characters", response_model=CharacterOut, status_code=201, summary="Create a character")
def create_character(body: CharacterCreate, db: Session = Depends(get_db)):
    """`reference_image_paths` are relative to data/characters; absolute paths and '..' are rejected (422)."""
    return svc.create_character(db, body)


@router.get("/characters", response_model=List[CharacterOut], summary="List characters")
def list_characters(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(CharacterRow).order_by(CharacterRow.created_at, CharacterRow.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.post("/characters/similarity-check", response_model=SimilarityReport, summary="Text similarity check")
def similarity_check(body: SimilarityCheckRequest, db: Session = Depends(get_db)):
    """TEXT overlap only. The report states `guarantees_visual_uniqueness: false`."""
    return svc.similarity_report(db, body.name, body.appearance, body.exclude_character_id)


@router.post("/characters/generation-requests", response_model=CharacterDraft,
             summary="Request a new character proposal (mock)")
def generation_request(body: CharacterGenerationRequest, db: Session = Depends(get_db)):
    """Returns an unsaved draft labelled `output_status: mock`. No image is generated."""
    return svc.propose_character_mock(db, body.brief)


@router.get("/characters/{character_id}", response_model=CharacterOut, responses=_404, summary="Get a character")
def get_character(character_id: str, db: Session = Depends(get_db)):
    return svc.get_character_or_404(db, character_id)


@router.patch("/characters/{character_id}", response_model=CharacterOut, responses=_404, summary="Update a character")
def update_character(character_id: str, body: CharacterUpdate, db: Session = Depends(get_db)):
    return svc.update_character(db, svc.get_character_or_404(db, character_id), body)


@router.delete("/characters/{character_id}", status_code=204, responses={**_404, 409: {"model": ErrorResponse}},
               summary="Delete a character")
def delete_character(character_id: str, force: bool = False, db: Session = Depends(get_db)):
    svc.delete_character(db, svc.get_character_or_404(db, character_id), force)
    return Response(status_code=204)


@router.get("/characters/{character_id}/appearances", response_model=List[AppearanceOut], responses=_404,
            summary="Projects this character has been selected in")
def appearances(character_id: str, db: Session = Depends(get_db)):
    svc.get_character_or_404(db, character_id)
    links = db.scalars(select(ProjectCharacterRow).where(ProjectCharacterRow.character_id == character_id)
                       .order_by(ProjectCharacterRow.selected_at))
    return [AppearanceOut(project_id=l.project_id, project_title=l.project.title, role=l.role,
                          selected_at=l.selected_at) for l in links]


@router.get("/projects/{project_id}/characters", response_model=List[CharacterOut], responses=_404,
            summary="Characters selected for a project")
def project_characters(project_id: str, db: Session = Depends(get_db)):
    project_svc.get_project_or_404(db, project_id)
    ids = project_svc.selected_character_ids(db, project_id)
    rows = {r.id: r for r in db.scalars(select(CharacterRow).where(CharacterRow.id.in_(ids)))} if ids else {}
    return [rows[i] for i in ids if i in rows]


@router.put("/projects/{project_id}/characters/{character_id}", status_code=204, responses=_404,
            summary="Select a character for a project (idempotent)")
def select_character(project_id: str, character_id: str, role: str = Query("", max_length=80),
                     db: Session = Depends(get_db)):
    project = project_svc.get_project_or_404(db, project_id)
    svc.select_for_project(db, project, svc.get_character_or_404(db, character_id), role)
    return Response(status_code=204)


@router.delete("/projects/{project_id}/characters/{character_id}", status_code=204, responses=_404,
               summary="Deselect a character from a project")
def deselect_character(project_id: str, character_id: str, db: Session = Depends(get_db)):
    project_svc.get_project_or_404(db, project_id)
    link = db.get(ProjectCharacterRow, (project_id, character_id))
    if link is not None:
        db.delete(link)
        db.commit()
    return Response(status_code=204)
