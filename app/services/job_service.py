import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, GenerationJob, JobStatus
from app.services import certificate_service

logger = logging.getLogger(__name__)


def create_job(db, recipients):
    """Saves the job and one 'pending' certificate row per recipient."""
    job = GenerationJob(status=JobStatus.PENDING, total_count=len(recipients))
    for recipient in recipients:
        job.certificates.append(
            Certificate(
                recipient_name=recipient.name,
                certificate_id=recipient.certificate_id,
                status=CertificateStatus.PENDING,
            )
        )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db, job_id):
    return db.get(GenerationJob, job_id)


def get_certificate(db, certificate_id):
    return db.get(Certificate, certificate_id)


def process_job(job_id):
    # This runs as a background task, after the response was already sent.
    # The request's db session is closed by then, so we open our own.
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        for certificate in list(job.certificates):
            process_certificate(db, job, certificate)

        job.status = get_final_status(job)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        # Something outside a single certificate broke (e.g. the database).
        logger.exception("Job %s crashed", job_id)
        db.rollback()
        mark_job_failed(db, job_id)
    finally:
        db.close()


def process_certificate(db, job, certificate):
    # The try/except is around ONE certificate. If it fails we save the error
    # and go on, so the for loop in process_job keeps running.
    try:
        certificate.file_path = certificate_service.generate_certificate_pdf(
            certificate.id, certificate.recipient_name, certificate.certificate_id
        )
        certificate.status = CertificateStatus.GENERATED
        job.success_count += 1
    except Exception as error:
        logger.warning("Certificate %s failed: %s", certificate.certificate_id, error)
        certificate.status = CertificateStatus.FAILED
        certificate.error_message = f"{type(error).__name__}: {error}"[:500]
        job.failure_count += 1

    # commit after every certificate so the status endpoint shows live progress
    db.commit()


def get_final_status(job):
    if job.failure_count == 0:
        return JobStatus.COMPLETED
    if job.success_count == 0:
        return JobStatus.FAILED
    return JobStatus.COMPLETED_WITH_ERRORS


def mark_job_failed(db, job_id):
    job = db.get(GenerationJob, job_id)
    if job is not None:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
