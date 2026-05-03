from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.middleware.auth import api_key_auth
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.users import router as users_router


def _seed_default_data() -> None:
    """Seed a default institution and test user for SQLite dev/test environments."""
    from app.models import Institution, User

    db = SessionLocal()
    try:
        existing_inst = db.query(Institution).first()
        if existing_inst is None:
            inst = Institution(name="FaceR Demo", code="FACER_DEMO")
            db.add(inst)
            db.commit()
            db.refresh(inst)
        else:
            inst = existing_inst

        existing_user = db.query(User).first()
        if existing_user is None:
            user = User(
                first_name="Usuario",
                last_name="Prueba",
                institutional_id="TEST001",
                institution_id=inst.id,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_db_schema:
        # Import all models to ensure they are registered with Base
        from app.models import DocumentoINEMexico  # noqa: F401
        Base.metadata.create_all(bind=engine)
        if settings.sqlalchemy_database_uri.startswith("sqlite"):
            _seed_default_data()
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


# Auth routes (public - no API key required)
app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)


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
