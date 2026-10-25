from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ErrorResponse
from app.schemas.job import JobOut
from app.services import jobs as svc
from app.services import projects as project_svc

router = APIRouter(tags=["jobs"])
_404 = {404: {"model": ErrorResponse, "description": "Not found"}}


@router.get("/jobs/{job_id}", response_model=JobOut, responses=_404, summary="Job status")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """`progress` is stage-based (see `progress_kind`), not measured work."""
    return svc.get_job_or_404(db, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, responses={**_404, 409: {"model": ErrorResponse}},
             summary="Cancel a queued or running job")
def cancel(job_id: str, db: Session = Depends(get_db)):
    """Cooperative: a running job stops at its next stage boundary and saves nothing. 409 if already finished."""
    return svc.cancel_job(db, svc.get_job_or_404(db, job_id))


@router.get("/projects/{project_id}/jobs", response_model=List[JobOut], responses=_404, summary="Jobs for a project")
def project_jobs(project_id: str, db: Session = Depends(get_db)):
    project_svc.get_project_or_404(db, project_id)
    return svc.list_project_jobs(db, project_id)
