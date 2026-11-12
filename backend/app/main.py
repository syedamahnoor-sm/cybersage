from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.retrieval.api import router as retrieval_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Health checks and startup do not require a database connection or model.
    app.state.retrieval_engine = None
    try:
        yield
    finally:
        engine = app.state.retrieval_engine
        if engine is not None:
            engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Evidence-grounded cybersecurity intelligence API",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(retrieval_router)


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "0.1.0",
    }
