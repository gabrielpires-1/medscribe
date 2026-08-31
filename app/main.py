from fastapi import FastAPI

from app.config import get_settings
from app.health.route import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version)
    application.include_router(health_router)
    return application


app = create_app()
