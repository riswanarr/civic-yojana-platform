from app.services.update_service import update_service

from fastapi import APIRouter

router = APIRouter()


@router.post("")
def sync_sources() -> dict[str, int]:
    return update_service.run_sync()
