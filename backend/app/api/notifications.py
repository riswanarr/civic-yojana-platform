from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status

from app.services.notification_service import notification_service

router = APIRouter()


def get_access_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    return authorization.split(" ", 1)[1].strip()


@router.get("")
def list_notifications(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return notification_service.list_notifications(get_access_token(authorization))


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return notification_service.mark_as_read(get_access_token(authorization), notification_id)
