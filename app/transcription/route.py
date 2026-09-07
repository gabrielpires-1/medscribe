from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.exceptions import (
    EmptyAudioError,
    PyannoteClientError,
    PyannoteJobTimeoutError,
)
from app.transcription.schemas import TranscribeAccepted
from app.transcription.service import TranscriptionService

router = APIRouter(tags=["transcription"])


def get_transcription_service() -> TranscriptionService:
    return TranscriptionService()


@router.post("/transcribe", response_model=TranscribeAccepted, status_code=202)
async def transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscribeAccepted:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="audio file is empty")
    try:
        accepted = await service.start_transcription(content)
    except EmptyAudioError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except PyannoteJobTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message) from exc
    except PyannoteClientError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    background_tasks.add_task(service.persist_job_result, accepted.job_id)
    return accepted
