from __future__ import annotations

import hashlib
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.orm import CharacterRow, ProjectCharacterRow, ProjectRow, new_id
from app.providers.similarity import SimilarityChecker, TextOverlapSimilarityChecker
from app.schemas.character import (CharacterCreate, CharacterDraft, CharacterUpdate, SimilarityMatchOut,
                                   SimilarityReport)
from app.schemas.common import OutputStatus

SIMILARITY_THRESHOLD = 0.5


def get_character_or_404(db: Session, cid: str) -> CharacterRow:
    row = db.get(CharacterRow, cid)
    if row is None:
        raise NotFoundError("Character", cid)
    return row


def create_character(db: Session, data: CharacterCreate) -> CharacterRow:
    row = CharacterRow(
        id=new_id("chr"), name=data.name, description=data.description, appearance=data.appearance,
        personality=data.personality, voice_preferences=data.voice_preferences.model_dump(),
        reference_image_paths=list(data.reference_image_paths),
    )
    db.add(row)
    db.commit()
    return row


def update_character(db: Session, row: CharacterRow, data: CharacterUpdate) -> CharacterRow:
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            if key in ("name", "appearance"):
                continue  # required fields cannot be cleared
            value = [] if key == "reference_image_paths" else ({} if key == "voice_preferences" else "")
        setattr(row, key, value)
    db.commit()
    return row


def delete_character(db: Session, row: CharacterRow, force: bool) -> None:
    in_use = db.scalar(select(ProjectCharacterRow.project_id).where(ProjectCharacterRow.character_id == row.id).limit(1))
    if in_use and not force:
        raise ConflictError("Character is selected in one or more projects.",
                            hint="Pass ?force=true to delete anyway (scene plans keep the old id).")
    db.delete(row)
    db.commit()


def as_prompt_dict(row: CharacterRow) -> dict:
    return {"id": row.id, "name": row.name, "appearance": row.appearance, "personality": row.personality}


def similarity_report(db: Session, name: str, appearance: str, exclude_id: Optional[str] = None,
                      checker: Optional[SimilarityChecker] = None) -> SimilarityReport:
    checker = checker or TextOverlapSimilarityChecker()
    existing = [as_prompt_dict(r) for r in db.scalars(select(CharacterRow).limit(1000)) if r.id != exclude_id]
    matches = checker.compare({"name": name, "appearance": appearance}, existing)[:5]
    flagged = any(m.score >= SIMILARITY_THRESHOLD for m in matches)
    return SimilarityReport(
        method=checker.method,
        guarantees_visual_uniqueness=checker.guarantees_visual_uniqueness,
        threshold=SIMILARITY_THRESHOLD,
        verdict="possible_duplicate" if flagged else "no_text_match",
        matches=[SimilarityMatchOut(character_id=m.character_id, name=m.name, score=m.score) for m in matches],
        note="Compares name and appearance TEXT only. A low score does not prove the character looks different; "
             "visual checks (e.g. image embeddings) are not implemented yet.",
    )


_SPECIES = ["fox", "owl", "turtle", "bunny", "panda", "robot", "dragon", "hedgehog"]
_COLORS = ["orange", "teal", "purple", "yellow", "green", "blue", "pink", "red"]
_TRAITS = ["curious", "gentle", "cheerful", "brave", "clever", "kind"]


def propose_character_mock(db: Session, brief: str) -> CharacterDraft:
    """Deterministic MOCK character proposal derived from the brief. Not AI-generated; not saved."""
    h = hashlib.sha256(brief.strip().lower().encode("utf-8")).digest()
    species, color, trait = _SPECIES[h[0] % 8], _COLORS[h[1] % 8], _TRAITS[h[2] % 6]
    name = f"{color.capitalize()} {species.capitalize()}"
    draft = CharacterCreate(
        name=name,
        description=f"Proposed from brief: {brief.strip()}",
        appearance=f"A friendly {color} cartoon {species} with big round eyes and a simple rounded design",
        personality=trait,
    )
    return CharacterDraft(
        output_status=OutputStatus.MOCK,
        draft=draft,
        similarity=similarity_report(db, draft.name, draft.appearance),
        note="Mock proposal chosen from small fixed lists; no image was generated and nothing was saved. "
             "POST the draft to /characters to save it.",
    )


def select_for_project(db: Session, project: ProjectRow, character: CharacterRow, role: str) -> ProjectCharacterRow:
    link = db.get(ProjectCharacterRow, (project.id, character.id))
    if link is None:
        link = ProjectCharacterRow(project_id=project.id, character_id=character.id, role=role)
        db.add(link)
    else:
        link.role = role
    db.commit()
    return link
