from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CertificateResponse, JobCreate, JobResponse
from app.services import job_service

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_job_or_404(db, job_id):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/", response_model=JobResponse, status_code=201, summary="Create a bulk generation job")
def create_generation_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Saves the job and returns right away. The certificates are generated in
    the background, use `GET /api/jobs/{job_id}` to follow the progress."""
    job = job_service.create_job(db, payload.recipients)
    background_tasks.add_task(job_service.process_job, job.id)
    return job


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status and progress",
    responses={404: {"description": "Job not found"}},
)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    return get_job_or_404(db, job_id)


@router.get(
    "/{job_id}/certificates",
    response_model=list[CertificateResponse],
    summary="List the certificates of a job",
    responses={404: {"description": "Job not found"}},
)
def list_job_certificates(job_id: int, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    return job.certificates
