from datetime import datetime

from pydantic import BaseModel, Field

from app.constants import ConsultationStatus
from app.extraction.schemas import ConsultationDocuments


class ConsultationAccepted(BaseModel):
    id: str = Field(
        ...,
        min_length=1,
        examples=["00000000-0000-4000-8000-000000000001"],
    )
    status: ConsultationStatus


class ConsultationRead(BaseModel):
    id: str = Field(
        ...,
        min_length=1,
        examples=["00000000-0000-4000-8000-000000000001"],
    )
    status: ConsultationStatus
    documents: ConsultationDocuments | None
    error: str | None


class ConsultationMeta(BaseModel):
    id: str = Field(..., min_length=1)
    status: ConsultationStatus
    pyannote_job_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
