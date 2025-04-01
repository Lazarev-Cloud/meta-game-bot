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
