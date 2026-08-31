from app.constants import HealthStatus
from app.health.schemas import HealthRead


class HealthService:
    def check(self) -> HealthRead:
        return HealthRead(status=HealthStatus.OK)
