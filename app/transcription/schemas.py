from pydantic import BaseModel, Field

from app.constants import JobStatus


class TranscribeAccepted(BaseModel):
    job_id: str = Field(..., min_length=1, examples=["job-0001"])
    status: JobStatus
