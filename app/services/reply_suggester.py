"""Sugerencia de respuesta editable de tickets (spec §15.3, FR-03, FR-08, épica 4.4).

Mismo pipeline seguro que la clasificación (011) y el resumen (012): contexto
redactado de PII → orquestador LLM (tarea `reply`) → validación JSON →
persistencia como `AISuggestion` (type=reply, draft) → auditoría sin PII.
El grounding se limita al ticket y su historial (FR-08); no se inventan
políticas, precios ni plazos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics
from app.models.ai_suggestion import AISuggestion
from app.prompts.reply import REPLY_PROMPT_VERSION, build_reply_system, build_reply_user_prompt
from app.repositories.tickets import TicketRepository
from app.services.llm_orchestrator import LLMOrchestrator
from app.services.pii import PiiRedactor


class ReplyError(ValueError):
    """La salida del LLM no es un JSON de respuesta válido (fallback seguro)."""


@dataclass
class ReplyResult:
    suggested_reply: str
    confidence: float
    sources: list[str] = field(default_factory=list)
    policy_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class AuditPort(Protocol):
    def log(
        self,
        action: str,
        *,
        user_id: int | None = None,
        tenant_id: str | None = None,
        service: str | None = None,
        trace_id: str | None = None,
        result: str = "success",
        confidence: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> object: ...


class TicketReplySuggester:
    """Sugiere una respuesta editable para un ticket del tenant."""

    def __init__(
        self,
        db: Session,
        *,
        user_id: int | None,
        tenant_id: str | None,
        orchestrator: LLMOrchestrator | None = None,
        audit: AuditPort | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        self._db = db
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._orchestrator = orchestrator or LLMOrchestrator()
        self._audit = audit
        self._redactor = PiiRedactor()
        self._repo = TicketRepository(db, tenant_id) if tenant_id else None
        # Override de GlobalPolicy (018): None = usar settings.
        self._confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else settings.ai_confidence_threshold
        )

    def suggest_reply(
        self,
        ticket_id: int,
        *,
        tone: str | None = None,
        language: str | None = None,
        trace_id: str | None = None,
    ) -> tuple[ReplyResult, AISuggestion]:
        """Sugiere una respuesta y persiste la sugerencia. Otro tenant → PermissionError."""
        if self._repo is None:
            raise PermissionError("Tenant no definido")
        ticket = self._repo.get_or_none(ticket_id)
        if ticket is None:
            raise PermissionError("Ticket no encontrado")
        messages = self._repo.list_messages(ticket_id)

        history = "\n".join(f"- {m.body}" for m in messages[-5:])
        subject = self._redactor.redact(ticket.subject).text
        description = self._redactor.redact(ticket.description).text
        history = self._redactor.redact(history).text

        user_prompt = build_reply_user_prompt(
            subject=subject,
            description=description,
            history=history,
            locale=language or ticket.language,
            tone=tone or "profesional",
        )
        result_payload = self._orchestrator.complete(
            task="reply",
            system=build_reply_system(),
            user=user_prompt,
            tenant_id=self._tenant_id,
            user_id=self._user_id,
            trace_id=trace_id,
        )

        parsed = self._parse_output(result_payload["content"])

        suggestion = AISuggestion(
            tenant_id=self._tenant_id,
            ticket_id=ticket_id,
            type="reply",
            output={
                "suggested_reply": parsed.suggested_reply,
                "sources": parsed.sources,
                "policy_flags": parsed.policy_flags,
            },
            confidence=parsed.confidence,
            model=result_payload["model"],
            prompt_version=REPLY_PROMPT_VERSION,
            state="draft",
        )
        self._db.add(suggestion)
        self._db.commit()
        self._db.refresh(suggestion)

        metrics.inc("ai_replies_total", labels={"status": "ok"})
        if self._audit is not None:
            self._audit.log(
                "ai.replied",
                user_id=self._user_id,
                tenant_id=self._tenant_id,
                service="ai",
                trace_id=trace_id,
                result="success",
                confidence=parsed.confidence,
                detail={
                    "ticket_id": ticket_id,
                    "model": result_payload["model"],
                    "prompt_version": REPLY_PROMPT_VERSION,
                },
            )
        return parsed, suggestion

    def _parse_output(self, content: str) -> ReplyResult:
        """Valida y normaliza la salida JSON del LLM (fallback seguro si es inválida)."""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ReplyError("Salida de respuesta inválida") from exc
        if not isinstance(data, dict):
            raise ReplyError("Salida de respuesta inválida")

        suggested_reply = str(data.get("suggestedReply") or "").strip()
        if not suggested_reply:
            raise ReplyError("Campos de respuesta inválidos")

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        sources = [str(s) for s in data.get("sources", []) if isinstance(s, (str, int, float))]
        policy_flags = [str(p) for p in data.get("policyFlags", []) if isinstance(p, (str, int, float))]
        warnings = [str(w) for w in data.get("warnings", []) if isinstance(w, (str, int, float))]
        if confidence < self._confidence_threshold:
            warnings.append("revisión humana recomendada: confianza baja")

        return ReplyResult(
            suggested_reply=suggested_reply,
            confidence=confidence,
            sources=sources,
            policy_flags=policy_flags,
            warnings=warnings,
        )
