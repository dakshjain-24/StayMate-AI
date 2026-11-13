from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.core.rate_limit import limiter

from app.db.base import Base
from app.db.session import engine

import app.models  # noqa: F401



# APP LIFESPAN

@asynccontextmanager
async def lifespan(_: FastAPI,):

    # Ensure pgvector extension exists.
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE EXTENSION "
                "IF NOT EXISTS vector"
            )
        )

    # Create any missing SQLAlchemy tables.
    Base.metadata.create_all(bind=engine)

    yield



# FASTAPI APP

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)



# RATE LIMITER

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.add_middleware(SlowAPIMiddleware)



# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



# ROUTES
app.include_router(router)



# ROOT

@app.get("/")
def root():

    return {
        "name": settings.app_name,
        "docs": "/docs",
    }