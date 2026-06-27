from fastapi import APIRouter

from app.api import (
    admin,
    applications,
    chatbot,
    eligibility,
    notifications,
    profiles,
    recommendations,
    saved_schemes,
    schemes,
    sync,
)
api_router = APIRouter()

api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(schemes.router, prefix="/schemes", tags=["schemes"])
api_router.include_router(eligibility.router,prefix="/schemes",tags=["eligibility"])
api_router.include_router(saved_schemes.router, prefix="/saved-schemes", tags=["saved-schemes"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
