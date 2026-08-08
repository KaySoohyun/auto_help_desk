from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_trace_id
from app.core.permissions import REQUEST_AI_SUGGESTION, VIEW_AUDIT, require_permissions
from app.database import get_db
from app.models.user import User
from app.schemas.ai import ClassificationOut
from app.schemas.llm import LLMPingInfo
from app.services.audit import AuditService, get_audit_service
from app.services.classifier import ClassificationError, TicketClassifier
from app.services.llm import LLMRateLimitExceeded, LLMUnavailableError
from app.services.llm_orchestrator import LLMOrchestrator

router = APIRouter(prefix="/v1/ai", tags=["ai"])


def _orchestrator(audit: AuditService) -> LLMOrchestrator:
    return LLMOrchestrator(audit=audit)


def _trace() -> str:
    return get_trace_id()


@router.post("/ping", response_model=LLMPingInfo)
def ai_ping(
    current_user: User = Depends(require_permissions(REQUEST_AI_SUGGESTION)),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_trace),
) -> LLMPingInfo:
    """Prueba de conectividad del orquestador LLM (sin PII, sin red en dev)."""
    orchestrator = _orchestrator(audit)
    try:
        result = orchestrator.complete(
            task="ping",
            system="Responde solo: pong.",
            user="ping",
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            trace_id=trace_id,
        )
    except LLMRateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM no disponible"
        ) from exc
    return LLMPingInfo(ok=True, model=result["model"], trace_id=trace_id)


@router.get("/info")
def ai_info(
    current_user: User = Depends(require_permissions(VIEW_AUDIT)),
) -> dict[str, object]:
    """Config del orquestador sin secretos (spec §14.4)."""
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "rate_max_calls": settings.llm_rate_max_calls,
        "rate_window_seconds": settings.llm_rate_window_seconds,
        "max_retries": settings.llm_max_retries,
    }


@router.post("/tickets/{ticket_id}/classify", response_model=ClassificationOut)
def classify_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permissions(REQUEST_AI_SUGGESTION)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_trace),
) -> ClassificationOut:
    """Clasifica un ticket con IA (spec §15.1). El contexto va redactado de PII."""
    classifier = TicketClassifier(
        db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        orchestrator=_orchestrator(audit),
        audit=audit,
    )
    try:
        result, suggestion = classifier.classify(ticket_id, trace_id=trace_id)
    except LLMRateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM no disponible"
        ) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado") from exc
    except ClassificationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ClassificationOut(
        category=result.category,
        subcategory=result.subcategory,
        intent=result.intent,
        suggested_priority=result.suggested_priority,
        confidence=result.confidence,
        rationale=result.rationale,
        warnings=result.warnings,
        suggestion_id=suggestion.id,
        trace_id=trace_id,
    )