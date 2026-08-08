from fastapi import FastAPI

from app.api.routes_admin import router as admin_router
from app.api.routes_audit import router as audit_router
from app.api.routes_auth import router as auth_router
from app.core.config import settings
from app.database import Base, engine

app = FastAPI(title=settings.app_name)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(audit_router)


@app.on_event("startup")
def on_startup() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
