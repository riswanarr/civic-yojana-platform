from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.eligibility_service import (
    eligibility_service,
)

router = APIRouter()

security = HTTPBearer()


@router.get("/{scheme_id}/eligibility")
def get_scheme_eligibility(
    scheme_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
) -> dict[str, Any]:
    access_token = credentials.credentials

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )

    return eligibility_service.get_eligibility(
        access_token,
        scheme_id,
    )