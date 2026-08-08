"""Middleware de observabilidad: métricas HTTP, trace_id y logging de errores.

Registra para cada request: contador por método/ruta/status, histograma de
duración, contador de errores (≥400) y de excepciones no controladas. Expone el
`trace_id` en el header de respuesta `X-Request-ID`. Nunca loggea body ni auth.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import logger, set_trace_id
from app.core.metrics import metrics

# Tamaño máximo del label de ruta para evitar cardinalidad por query/params.
_MAX_ROUTE_LABEL = 128


def route_label(request: Request) -> str:
    """Route template si la matchea una ruta conocida; si no, el path base.

    Evita cardinalidad alta (no se incluyen query params ni IDs de tickets).
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path[: _MAX_ROUTE_LABEL]
    path = request.url.path
    return path[: _MAX_ROUTE_LABEL]


class MetricsMiddleware(BaseHTTPMiddleware):
    """Mide latencia y publica métricas HTTP por request (spec §14.4)."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not getattr(request.state, "trace_id", None):
            request.state.trace_id = str(uuid.uuid4())
        trace_id = request.headers.get("X-Request-ID") or request.state.trace_id
        request.state.trace_id = trace_id
        set_trace_id(trace_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            metrics.inc(
                "http_exceptions_total",
                labels={"method": request.method, "route": route_label(request)},
            )
            logger.exception("Excepción no controlada durante el request", extra={"trace_id": trace_id})
            raise
        finally:
            duration = time.perf_counter() - start
            label = route_label(request)
            metrics.inc(
                "http_requests_total",
                labels={"method": request.method, "route": label, "status": str(status_code)},
            )
            metrics.observe(
                "http_request_duration_seconds",
                duration,
                labels={"method": request.method, "route": label},
            )
            if status_code >= 400:
                metrics.inc(
                    "http_errors_total",
                    labels={"status": str(status_code)},
                )
        response.headers["X-Request-ID"] = trace_id
        return response