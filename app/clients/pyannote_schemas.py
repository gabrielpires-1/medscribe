from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.constants import DiarizationModel, JobStatus


class MediaInputRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., min_length=1)


class MediaUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., min_length=1)


class DiarizeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., min_length=1)
    transcription: bool = True
    model: DiarizationModel = DiarizationModel.PRECISION_2


class JobCreated(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., min_length=1, alias="jobId")
    status: JobStatus
    warning: str | None = None


class TranscriptionSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start: float
    end: float
    text: str
    speaker: str


class DiarizationSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    speaker: str
    start: float
    end: float
    confidence: dict[str, float] | None = None


class DiarizationJobOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    diarization: list[DiarizationSegment] = Field(default_factory=list)
    word_level_transcription: list[TranscriptionSegment] | None = Field(
        default=None,
        alias="wordLevelTranscription",
    )
    turn_level_transcription: list[TranscriptionSegment] | None = Field(
        default=None,
        alias="turnLevelTranscription",
    )
    error: str | None = None
    warning: str | None = None


class DiarizationJob(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., min_length=1, alias="jobId")
    status: JobStatus
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    output: DiarizationJobOutput | None = None
