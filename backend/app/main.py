from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.services.sync_scheduler import sync_scheduler


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    async def start_sync_scheduler() -> None:
        if settings.auto_sync_enabled:
            sync_scheduler.start(settings.auto_sync_interval_seconds)

    @app.on_event("shutdown")
    async def stop_sync_scheduler() -> None:
        await sync_scheduler.stop()

    return app


app = create_app()
