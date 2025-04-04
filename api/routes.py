"""
API routes for basic service operations.

Includes endpoints for:
- Health check to verify if the server is running.
- Debug route to inspect current application settings.

Routes:
    GET /health: Returns a status message and current environment.
    GET /settings: Returns the application settings (for debugging only).
"""

from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health", tags=["Service"])
def health_check():
    """
    Perform a basic health check.

    Returns:
        dict: A status dictionary containing service availability and current environment.
    """
    return {"status": "ok", "environment": settings.env}


@router.get("/settings", tags=["Debug"])
def get_settings():
    """
    Retrieve current application settings.

    Warning:
        This endpoint is intended for debugging purposes only and should not be exposed in production.

    Returns:
        dict: A dictionary of the current configuration settings.
    """
    return settings.model_dump()
