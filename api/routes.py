from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health", tags=["Service"])
def health_check():
    """Проверка, что сервер работает."""
    return {"status": "ok", "environment": settings.env}


@router.get("/settings", tags=["Debug"])
def get_settings():
    """Показывает текущие переменные настроек (только для отладки!)"""
    return settings.model_dump()
