from app.constants import HealthStatus
from app.health.schemas import HealthRead
from app.health.service import HealthService


def test_check_returns_ok_status() -> None:
    result = HealthService().check()
    assert isinstance(result, HealthRead)
    assert result.status == HealthStatus.OK
