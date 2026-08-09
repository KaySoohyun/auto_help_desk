"""Guardrails de entrada y salida para llamadas LLM (spec §12, ADR-002).

Centraliza en el orquestador los controles que faltan tras 010-013:
- `check_output`: filtra la salida del LLM antes de devolverla (PII CRÍTICA no
  tokenizada = eco de PII, amenaza T3; y contenido prohibido como jailbreak,
  cambio de rol o exfiltración, §12.3). Si detecta → `blocked=True`.
- `check_input`: detecta patrones de prompt injection en el contexto del ticket
  (ya delimitado como `DATOS_NO_CONFIABLES`) y devuelve un reporte informativo
  (no bloquea: la delimitación del prompt ya protege, §12.1).

Filtros deterministas (regex + `PiiRedactor.detect`); sin segundo LLM. La
evaluación formal con dataset de control llega en la feature 017.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.pii import PiiRedactor


class OutputBlockedError(ValueError):
    """La salida del LLM fue bloqueada por los guardrails (fallback seguro)."""


@dataclass
class GuardrailReport:
    blocked: bool = False
    reasons: list[str] = field(default_factory=list)


class Guardrails:
    """Filtros deterministas de entrada y salida para las llamadas LLM.

    `enabled` permite aplicar un override de `GlobalPolicy` (018). Si es `None`
    se usa `settings.guardrails_enabled` (comportamiento por defecto).
    """

    def __init__(self, enabled: bool | None = None) -> None:
        self._redactor = PiiRedactor()
        self._enabled = enabled

    def _is_enabled(self) -> bool:
        return settings.guardrails_enabled if self._enabled is None else self._enabled

    def _compile(self, patterns: list[str]) -> list[re.Pattern[str]]:
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def check_output(self, content: str) -> GuardrailReport:
        """Filtra la salida del LLM. Bloquea si hay PII cruda o contenido prohibido."""
        if not self._is_enabled() or not content:
            return GuardrailReport()

        report = GuardrailReport()
        pii = self._redactor.redact(content, mode="detect")
        if pii.report.total > 0:
            report.blocked = True
            report.reasons.append("pii_leak")

        for pattern in self._compile(settings.guardrail_prohibited_patterns):
            if pattern.search(content):
                report.blocked = True
                report.reasons.append("prohibited_content")
                break

        return report

    def check_input(self, content: str) -> GuardrailReport:
        """Detecta patrones de prompt injection en la entrada (informativo, no bloquea)."""
        if not self._is_enabled() or not content:
            return GuardrailReport()

        report = GuardrailReport()
        for pattern in self._compile(settings.guardrail_injection_patterns):
            if pattern.search(content):
                report.reasons.append("prompt_injection")
                break
        return report
