import os
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateStatus
from app.services import job_service

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}/download",
    summary="Download a generated certificate (PDF)",
    responses={
        404: {"description": "Certificate or its file not found"},
        409: {"description": "Certificate was not generated (failed or still pending)"},
    },
)
def download_certificate(certificate_id: int, db: Session = Depends(get_db)):
    """`certificate_id` here is the `id` returned by the job's certificate list
    (the database id), not the CERT-001 style value."""
    certificate = job_service.get_certificate(db, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail=f"Certificate {certificate_id} not found")

    if certificate.status != CertificateStatus.GENERATED:
        raise HTTPException(
            status_code=409,
            detail=f"Certificate is not available, its status is '{certificate.status}'",
        )

    if not certificate.file_path or not os.path.exists(certificate.file_path):
        raise HTTPException(status_code=404, detail="Certificate file is missing on the server")

    # certificate_id is user input, keep only safe characters for the download name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", certificate.certificate_id)
    return FileResponse(
        certificate.file_path,
        media_type="application/pdf",
        filename=f"{safe_name}.pdf",
    )
