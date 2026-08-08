"""Logging de aplicación con `trace_id` por request (spec §14.4).

Sin PII: solo se loggean eventos, conteos y errores técnicos; nunca el body,
token ni credenciales.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

# ContextVar del trace_id: lo setea el middleware y lo lee el filtro de logging.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def set_trace_id(trace_id: str) -> None:
    trace_id_var.set(trace_id)


def get_current_trace_id() -> str:
    return trace_id_var.get()


LOG_FORMAT = "%(asctime)s | %(levelname)-7s | trace=%(trace_id)s | %(message)s"


class TraceIdFilter(logging.Filter):
    """Inyecta `trace_id` en el record (vacío si no hay request activa)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = getattr(record, "trace_id", None) or get_current_trace_id()
        return True


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura y devuelve el logger global de la aplicación (idempotente)."""
    logger = logging.getLogger("app")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(TraceIdFilter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


logger = configure_logging()