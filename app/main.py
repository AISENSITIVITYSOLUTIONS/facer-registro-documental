from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.middleware.auth import api_key_auth
from app.routers.documents import router as documents_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_db_schema and settings.sqlalchemy_database_uri.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Public routes (no authentication required)
@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


# Protected routes (require API key via Authorization: Bearer <key>)
app.include_router(
    users_router,
    prefix=settings.api_v1_prefix,
    dependencies=[Depends(api_key_auth)],
)
app.include_router(
    documents_router,
    prefix=settings.api_v1_prefix,
    dependencies=[Depends(api_key_auth)],
)
