from __future__ import annotations

from typing import List

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.orm import JobRow, new_id, utcnow

ACTIVE = ("queued", "running")


def create_job(db: Session, project_id: str, kind: str) -> JobRow:
    job = JobRow(id=new_id("job"), project_id=project_id, kind=kind, status="queued", stage="queued", progress=0)
    db.add(job)
    db.commit()
    return job


def get_job_or_404(db: Session, job_id: str) -> JobRow:
    job = db.get(JobRow, job_id)
    if job is None:
        raise NotFoundError("Job", job_id)
    return job


def list_project_jobs(db: Session, project_id: str) -> List[JobRow]:
    return list(db.scalars(select(JobRow).where(JobRow.project_id == project_id)
                           .order_by(JobRow.created_at.desc(), JobRow.id)))


def fail_interrupted_jobs(db: Session) -> int:
    """Mark in-process jobs from a previous server run as failed instead of leaving them stuck."""
    res = db.execute(update(JobRow).where(JobRow.status.in_(ACTIVE)).values(
        status="failed",
        stage="failed",
        error_message="Job was interrupted because the backend restarted. Start the job again.",
        updated_at=utcnow(),
    ))
    db.commit()
    return res.rowcount


def advance(db: Session, job_id: str, **values) -> bool:
    """Update an ACTIVE job. Returns False if the job is no longer active
    (cancelled/deleted), which tells the worker to stop."""
    res = db.execute(update(JobRow).where(JobRow.id == job_id, JobRow.status.in_(ACTIVE))
                     .values(updated_at=utcnow(), **values))
    db.commit()
    return res.rowcount == 1


def cancel_job(db: Session, job: JobRow) -> JobRow:
    ok = advance(db, job.id, status="cancelled", stage="cancelled")
    db.refresh(job)
    if not ok:
        raise ConflictError(f"Job is already {job.status} and cannot be cancelled.")
    return job
