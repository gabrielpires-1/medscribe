from fastapi import APIRouter, Depends

from app.health.schemas import HealthRead
from app.health.service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
async def get_health(service: HealthService = Depends()) -> HealthRead:
    return service.check()
