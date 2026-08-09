"""Resumen automático de tickets (spec §15.2, FR-02, épica 4.3).

Mismo pipeline seguro que la clasificación (011): contexto redactado de PII →
orquestador LLM (tarea `summary`) → validación JSON → persistencia como
`AISuggestion` (type=summary, draft) → auditoría sin PII.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics
from app.models.ai_suggestion import AISuggestion
from app.prompts.summary import SUMMARY_PROMPT_VERSION, build_summary_system, build_summary_user_prompt
from app.repositories.tickets import TicketRepository
from app.services.llm_orchestrator import LLMOrchestrator
from app.services.pii import PiiRedactor


class SummaryError(ValueError):
    """La salida del LLM no es un JSON de resumen válido (fallback seguro)."""


@dataclass
class SummaryResult:
    summary: str
    missing_information: str | None
    confidence: float
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


class TicketSummarizer:
    """Resume un ticket del tenant usando el orquestador LLM."""

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

    def summarize(
        self,
        ticket_id: int,
        *,
        trace_id: str | None = None,
    ) -> tuple[SummaryResult, AISuggestion]:
        """Resume el ticket y persiste la sugerencia. Otro tenant → PermissionError."""
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

        user_prompt = build_summary_user_prompt(
            subject=subject,
            description=description,
            history=history,
            locale=ticket.language,
        )
        result_payload = self._orchestrator.complete(
            task="summary",
            system=build_summary_system(),
            user=user_prompt,
            tenant_id=self._tenant_id,
            user_id=self._user_id,
            trace_id=trace_id,
        )

        parsed = self._parse_output(result_payload["content"])

        suggestion = AISuggestion(
            tenant_id=self._tenant_id,
            ticket_id=ticket_id,
            type="summary",
            output={
                "summary": parsed.summary,
                "missing_information": parsed.missing_information,
            },
            confidence=parsed.confidence,
            model=result_payload["model"],
            prompt_version=SUMMARY_PROMPT_VERSION,
            state="draft",
        )
        self._db.add(suggestion)
        self._db.commit()
        self._db.refresh(suggestion)

        metrics.inc("ai_summaries_total", labels={"status": "ok"})
        if self._audit is not None:
            self._audit.log(
                "ai.summarized",
                user_id=self._user_id,
                tenant_id=self._tenant_id,
                service="ai",
                trace_id=trace_id,
                result="success",
                confidence=parsed.confidence,
                detail={
                    "ticket_id": ticket_id,
                    "model": result_payload["model"],
                    "prompt_version": SUMMARY_PROMPT_VERSION,
                },
            )
        return parsed, suggestion

    def _parse_output(self, content: str) -> SummaryResult:
        """Valida y normaliza la salida JSON del LLM (fallback seguro si es inválida)."""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise SummaryError("Salida de resumen inválida") from exc
        if not isinstance(data, dict):
            raise SummaryError("Salida de resumen inválida")

        summary = str(data.get("summary") or "").strip()
        if not summary:
            raise SummaryError("Campos de resumen inválidos")

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        warnings = [str(w) for w in data.get("warnings", []) if isinstance(w, (str, int, float))]
        if confidence < self._confidence_threshold:
            warnings.append("revisión humana recomendada: confianza baja")

        return SummaryResult(
            summary=summary,
            missing_information=str(data.get("missingInformation") or "") or None,
            confidence=confidence,
            warnings=warnings,
        )