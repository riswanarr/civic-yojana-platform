from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.services.saved_scheme_service import saved_scheme_service

router = APIRouter()


class SavedSchemeRequest(BaseModel):
    scheme_id: str = Field(min_length=1)


def get_access_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    return authorization.split(" ", 1)[1].strip()


@router.get("")
def list_saved_schemes(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return saved_scheme_service.list_saved_schemes(get_access_token(authorization))


@router.post("")
def save_scheme(
    payload: SavedSchemeRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return saved_scheme_service.save_scheme(get_access_token(authorization), payload.scheme_id)


@router.delete("/{scheme_id}")
def unsave_scheme(
    scheme_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return saved_scheme_service.unsave_scheme(get_access_token(authorization), scheme_id)
