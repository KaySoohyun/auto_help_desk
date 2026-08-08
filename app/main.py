from fastapi import FastAPI

from app.api.routes_admin import router as admin_router
from app.api.routes_ai import router as ai_router
from app.api.routes_audit import router as audit_router
from app.api.routes_auth import router as auth_router
from app.api.routes_metrics import router as metrics_router
from app.api.routes_pii import router as pii_router
from app.api.routes_tickets import router as tickets_router
from app.core.config import settings
from app.core.observability import MetricsMiddleware
from app.database import Base, engine

app = FastAPI(title=settings.app_name)

app.add_middleware(MetricsMiddleware)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(tickets_router)
app.include_router(pii_router)
app.include_router(metrics_router)
app.include_router(ai_router)


@app.on_event("startup")
def on_startup() -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
