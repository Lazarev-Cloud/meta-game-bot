"""
Main entry point for the FastAPI application.

This module initializes the FastAPI app, configures logging, and includes the API routes.

Modules:
    - FastAPI: Web framework for building APIs.
    - configure_logging: Custom logging configuration from the app package.
    - api_router: Main API router with all endpoints.

Usage:
    Run this module with a WSGI/ASGI server (e.g., Uvicorn) to start the application.

Example:
    uvicorn api.main:app --reload
"""

from fastapi import FastAPI
from app.logger import configure_logging
from api.routes import router as api_router

app = FastAPI(
    title="Not That Bot Template API",
    description="API documentation with Swagger UI",
    version="1.0.0"
)

configure_logging()
app.include_router(api_router)
