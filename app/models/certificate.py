import os

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class CertificateStatus:
    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"


class Certificate(Base):
    __tablename__ = "certificates"
    # safety net, the schema already rejects duplicates inside one request
    __table_args__ = (UniqueConstraint("job_id", "certificate_id"),)

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("generation_jobs.id"), nullable=False, index=True)
    recipient_name = Column(String(100), nullable=False)
    certificate_id = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default=CertificateStatus.PENDING)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    job = relationship("GenerationJob", back_populates="certificates")

    @property
    def file_name(self):
        # the API only shows the file name, not the path on the server
        if self.file_path is None:
            return None
        return os.path.basename(self.file_path)
