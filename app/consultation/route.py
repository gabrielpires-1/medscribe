from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.constants import EMPTY_AUDIO_MESSAGE
from app.consultation.schemas import ConsultationAccepted, ConsultationRead
from app.consultation.service import ConsultationService
from app.exceptions import (
    AnthropicClientError,
    ConsultationNotFoundError,
    EmptyAudioError,
    ExtractNotReadyError,
    PyannoteClientError,
    PyannoteJobTimeoutError,
)

router = APIRouter(tags=["consultation"])


def get_consultation_service() -> ConsultationService:
    return ConsultationService()


@router.post("/consultations", response_model=ConsultationAccepted, status_code=202)
async def create_consultation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: ConsultationService = Depends(get_consultation_service),
) -> ConsultationAccepted:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail=EMPTY_AUDIO_MESSAGE)
    try:
        accepted = await service.start(content)
    except EmptyAudioError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except PyannoteJobTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message) from exc
    except (PyannoteClientError, AnthropicClientError) as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    background_tasks.add_task(service.run_pipeline, accepted.id)
    return accepted


@router.get("/consultations/{consultation_id}", response_model=ConsultationRead)
async def get_consultation(
    consultation_id: str,
    service: ConsultationService = Depends(get_consultation_service),
) -> ConsultationRead:
    try:
        return service.get(consultation_id)
    except ConsultationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


@router.post(
    "/consultations/{consultation_id}/extract",
    response_model=ConsultationAccepted,
    status_code=202,
)
async def extract_consultation(
    consultation_id: str,
    background_tasks: BackgroundTasks,
    service: ConsultationService = Depends(get_consultation_service),
) -> ConsultationAccepted:
    try:
        accepted = await service.start_extract(consultation_id)
    except ConsultationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ExtractNotReadyError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except PyannoteJobTimeoutError as exc:
        raise HTTPException(status_code=504, detail=exc.message) from exc
    except (PyannoteClientError, AnthropicClientError) as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    background_tasks.add_task(service.run_extract, accepted.id)
    return accepted
