"""Rate limiting en memoria (spec §14.2, sin Redis en el stack).

Ventana deslizante por clave (ej: `tenant_id:user_id`) con recuento de llamadas
dentro de la ventana. Adviértase: para multi-instancia/despliegue real se debe
mover a Redis (se documenta en feature 018).
"""

from __future__ import annotations

import threading
import time


class RateLimitStore:
    """Registra llamadas por clave y permite/página según una ventana."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timestamps: dict[str, list[float]] = {}

    def reset(self) -> None:
        """Limpia el registro (útil en tests)."""
        with self._lock:
            self._timestamps.clear()

    def record(self, key: str, now: float | None = None) -> None:
        with self._lock:
            self._timestamps.setdefault(key, []).append(now or time.monotonic())

    def count_in_window(self, key: str, window_seconds: float, now: float | None = None) -> int:
        """Devuelve cuántas llamadas hay dentro de la ventana anterior a `now`."""
        now = now or time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            stamps = self._timestamps.get(key, [])
            keep = [t for t in stamps if t >= cutoff]
            self._timestamps[key] = keep
            return len(keep)

    def is_allowed(self, key: str, max_calls: int, window_seconds: float) -> bool:
        return self.count_in_window(key, window_seconds) < max_calls

    def allow_and_record(self, key: str, max_calls: int, window_seconds: float) -> bool:
        """¿Permitido? Si sí, registra la llamada; si no, no."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - window_seconds
            stamps = [t for t in self._timestamps.get(key, []) if t >= cutoff]
            self._timestamps[key] = stamps
            if len(stamps) >= max_calls:
                return False
            self._timestamps[key].append(now)
            return True


rate_limit_store = RateLimitStore()