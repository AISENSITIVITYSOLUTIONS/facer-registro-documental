from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.routers.documents import router as documents_router
from app.routers.users import router as users_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(documents_router, prefix=settings.api_v1_prefix)
