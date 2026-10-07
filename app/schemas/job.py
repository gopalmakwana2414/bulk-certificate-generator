from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import MAX_RECIPIENTS


class RecipientIn(BaseModel):
    # strip spaces first, so "   " is treated as empty
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., max_length=100, examples=["Rahul Sharma"])
    certificate_id: str = Field(..., max_length=50, examples=["CERT-001"])

    @field_validator("name", "certificate_id")
    @classmethod
    def must_not_be_empty(cls, value, info):
        if not value:
            raise ValueError(f"{info.field_name} cannot be empty")
        return value


class JobCreate(BaseModel):
    recipients: list[RecipientIn] = Field(..., min_length=1, max_length=MAX_RECIPIENTS)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recipients": [
                    {"name": "Rahul Sharma", "certificate_id": "CERT-001"},
                    {"name": "Priya Patel", "certificate_id": "CERT-002"},
                ]
            }
        }
    )

    @model_validator(mode="after")
    def no_duplicate_certificate_ids(self):
        seen = set()
        duplicates = []
        for recipient in self.recipients:
            if recipient.certificate_id in seen and recipient.certificate_id not in duplicates:
                duplicates.append(recipient.certificate_id)
            seen.add(recipient.certificate_id)

        if duplicates:
            raise ValueError("Duplicate certificate IDs in request: " + ", ".join(duplicates))
        return self


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_count: int
    success_count: int
    failure_count: int
    progress: int
    created_at: datetime
    completed_at: Optional[datetime] = None
