from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status

from app.services.recommendation_service import recommendation_service

router = APIRouter()


@router.get("")
def get_recommendations(authorization: Annotated[str | None, Header()] = None) -> dict[str, list[dict[str, Any]]]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    access_token = authorization.split(" ", 1)[1].strip()
    return recommendation_service.get_recommendations(access_token)
