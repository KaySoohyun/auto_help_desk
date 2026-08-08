"""Orquestador LLM: punto único de llamadas a modelos (ADR-002, spec §14.2).

Aplica rate limit, reintentos con backoff, métricas y auditoría sobre las llamadas
al proveedor. Recibe contexto ya redactado (nunca PII cruda); no guarda el
contenido del prompt ni la respuesta (solo métricas y metadata).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.metrics import metrics
from app.services.guardrails import Guardrails, OutputBlockedError
from app.services.llm import BaseLLMProvider, LLMRateLimitExceeded, LLMUnavailableError

from app.core.rate_limit import RateLimitStore, rate_limit_store

logger = logging.getLogger("app")


class AuditPort(Protocol):
    """Mínimo necesario de un servicio de auditoría para el orquestador."""

    def log(
        self,
        action: str,
        *,
        user_id: int | None = None,
        tenant_id: str | None = None,
        service: str | None = None,
        trace_id: str | None = None,
        result: str = "success",
        detail: dict[str, Any] | None = None,
    ) -> object: ...


class LLMOrchestrator:
    """Orquesta llamadas LLM con límites, reintentos, métricas y auditoría."""

    def __init__(
        self,
        *,
        provider: BaseLLMProvider | None = None,
        rate_limit: RateLimitStore | None = None,
        audit: AuditPort | None = None,
        guardrails: Guardrails | None = None,
    ) -> None:
        self._provider = provider
        self._rate_limit = rate_limit or rate_limit_store
        self._audit = audit
        self._guardrails = guardrails or Guardrails()

    @property
    def provider(self) -> BaseLLMProvider | None:
        return self._provider

    def _effective_provider(self) -> BaseLLMProvider:
        if self._provider is None:
            from app.services.llm import get_llm_provider

            return get_llm_provider(settings)
        return self._provider

    def complete(
        self,
        *,
        task: str,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0,
        tenant_id: str | None = None,
        user_id: int | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una llamada LLM orquestada y devuelve `{content, model}`.

        - Límite excedido → `LLMRateLimitExceeded`.
        - Proveedor caído tras reintentos → `LLMUnavailableError`.
        """
        key = f"{tenant_id or '-'}:{user_id or '-'}"
        if not self._rate_limit.allow_and_record(
            key, settings.llm_rate_max_calls, settings.llm_rate_window_seconds
        ):
            self._audit_call(
                task=task,
                model=model,
                status="rate_limited",
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
            )
            raise LLMRateLimitExceeded("Se excedió el límite de llamadas LLM")

        input_report = self._guardrails.check_input(user)
        if input_report.reasons:
            self._audit_call(
                task=task,
                model=model,
                status="alert",
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
                detail={"reasons": input_report.reasons},
            )
            logger.warning("Posible prompt injection en entrada", extra={"task": task, "reasons": input_report.reasons})

        provider = self._effective_provider()
        try:
            response = self._complete_with_retries(provider, task, system, user, model, temperature)
        except LLMUnavailableError:
            metrics.inc("llm_calls_total", labels={"task": task, "status": "unavailable"})
            self._audit_call(
                task=task,
                model=model,
                status="failure",
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
            )
            raise
        except Exception as exc:
            logger.exception("Fallo inesperado en llamada LLM", extra={"task": task})
            metrics.inc("llm_calls_total", labels={"task": task, "status": "error"})
            self._audit_call(
                task=task,
                model=model,
                status="failure",
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
            )
            raise LLMUnavailableError("LLM no disponible") from exc

        output_report = self._guardrails.check_output(response.content)
        if output_report.blocked:
            for reason in output_report.reasons:
                metrics.inc("ai_guardrail_blocks_total", labels={"reason": reason, "task": task})
            self._audit_call(
                task=task,
                model=response.model,
                status="blocked",
                tenant_id=tenant_id,
                user_id=user_id,
                trace_id=trace_id,
                detail={"reasons": output_report.reasons},
            )
            logger.warning("Salida LLM bloqueada por guardrails", extra={"task": task, "reasons": output_report.reasons})
            raise OutputBlockedError("Contenido bloqueado por política de seguridad")

        metrics.inc("llm_calls_total", labels={"task": task, "status": "ok"})
        metrics.observe("llm_latency_seconds", response.duration_seconds, labels={"task": task})
        metrics.inc("llm_tokens_total", value=response.usage.total_tokens, labels={"task": task})
        self._audit_call(
            task=task,
            model=response.model,
            status="success",
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id,
            detail={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "latency_s": round(response.duration_seconds, 4),
            },
        )
        return {"content": response.content, "model": response.model}

    def _complete_with_retries(
        self,
        provider: BaseLLMProvider,
        task: str,
        system: str,
        user: str,
        model: str | None,
        temperature: float,
    ):
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        retries = 0
        while True:
            try:
                return provider.complete(
                    messages=messages,
                    model=model or settings.llm_model,
                    max_tokens=settings.llm_max_tokens,
                    temperature=temperature,
                )
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
                retries += 1
                if retries > settings.llm_max_retries:
                    logger.error("LLM agotó reintentos", extra={"task": task})
                    raise LLMUnavailableError("LLM no disponible tras reintentos") from exc
                logger.warning("Reintentando LLM (intento %d)", retries)
                time.sleep(settings.llm_retry_backoff)

    def _audit_call(
        self,
        *,
        task: str,
        status: str,
        tenant_id: str | None,
        user_id: int | None,
        trace_id: str | None,
        model: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        if self._audit is None:
            return
        self._audit.log(
            "llm.call",
            user_id=user_id,
            tenant_id=tenant_id,
            service="llm",
            trace_id=trace_id,
            result=status,
            detail=dict(detail or {}) | {"task": task, "status": status, "model": model},
        )


llm_orchestrator = LLMOrchestrator()