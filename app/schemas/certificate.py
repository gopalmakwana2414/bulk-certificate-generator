from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # "id" is the database id, it is the one used in the download URL.
    # "certificate_id" is the value the client sent, e.g. CERT-001.
    id: int
    job_id: int
    certificate_id: str
    recipient_name: str
    status: str
    file_name: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
