from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.services.scheme_service import scheme_service

router = APIRouter()


PageQuery = Annotated[int, Query(ge=1)]
PageSizeQuery = Annotated[int, Query(ge=1, le=50)]


@router.get("")
def list_schemes(
    state: str | None = None,
    category: str | None = None,
    ministry: str | None = None,
    search: str | None = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 12,
) -> dict[str, Any]:
    return scheme_service.list_schemes(
        state=state,
        category=category,
        ministry=ministry,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/search")
def search_schemes(
    q: str | None = Query(default=None, alias="q"),
    state: str | None = None,
    category: str | None = None,
    ministry: str | None = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 12,
) -> dict[str, Any]:
    return scheme_service.list_schemes(
        state=state,
        category=category,
        ministry=ministry,
        search=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{scheme_id}")
def get_scheme(scheme_id: str) -> dict[str, Any]:
    return scheme_service.get_scheme(scheme_id)
