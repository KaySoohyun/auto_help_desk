"""Registro de métricas en memoria compatible con el formato de texto de Prometheus.

Sin dependencias externas (el venv no incluye prometheus-client). Se usa stdlib
`dict` + `threading.Lock` para coherencia básica y se serializa a mano.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

# Buckets por defecto para histogramas de latencia (segundos), estilo Prometheus.
DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

_COUNTER = "counter"
_GAUGE = "gauge"
_HISTOGRAM = "histogram"

_LABELS_ESCAPE = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n"})


def _escape_label(value: str) -> str:
    return value.translate(_LABELS_ESCAPE)


class MetricsRegistry:
    """Contadores, gauges e histogramas identificados por nombre + etiquetas."""

    def __init__(self, buckets: tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        self._buckets = buckets
        self._lock = threading.Lock()
        self._types: dict[str, str] = {}
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        # Historia por (nombre, labels): (sum, count, buckets_counts)
        self._histograms: dict[
            tuple[str, tuple[tuple[str, str], ...]],
            tuple[float, float, list[float]],
        ] = {}

    def reset(self) -> None:
        """Limpia todos los registros (útil en tests)."""
        with self._lock:
            self._types.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    @staticmethod
    def _labels(labels: dict[str, Any] | None) -> tuple[tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted((k, str(v)) for k, v in labels.items()))

    def inc(
        self,
        name: str,
        value: float = 1,
        labels: dict[str, Any] | None = None,
    ) -> None:
        """Incrementa un contador (crea el tipo si no existe)."""
        key = (name, self._labels(labels))
        with self._lock:
            self._types.setdefault(name, _COUNTER)
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
        """Fija un gauge (crea el tipo si no existe)."""
        key = (name, self._labels(labels))
        with self._lock:
            self._types.setdefault(name, _GAUGE)
            self._gauges[key] = float(value)

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, Any] | None = None,
    ) -> None:
        """Registra una observación en un histograma (crea el tipo si no existe)."""
        key = (name, self._labels(labels))
        with self._lock:
            self._types.setdefault(name, _HISTOGRAM)
            sample = self._histograms.get(key)
            if sample is None:
                sample = (0.0, 0, [0.0] * (len(self._buckets) + 1))  # incluye +Inf
                self._histograms[key] = sample
            hist_sum, count, bucket_counts = sample
            self._histograms[key] = (hist_sum + float(value), count + 1, bucket_counts)
            for idx, le in enumerate(self._buckets):
                if float(value) <= le:
                    bucket_counts[idx] += 1
            bucket_counts[-1] += 1  # bucket +Inf

    def render_prometheus(self) -> str:
        """Serializa las métricas en formato de texto de Prometheus (text/plain)."""
        with self._lock:
            names = list(self._types.items())
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = dict(self._histograms)

        lines: list[str] = []
        for name, kind in names:
            lines.append(f"# TYPE {name} {kind}")
            for key in sorted(k for k in counters if k[0] == name):
                lines.append(self._render_line(name, counters[key], key[1]))
            for key in sorted(k for k in gauges if k[0] == name):
                lines.append(self._render_line(name, gauges[key], key[1]))
            for key in sorted(k for k in histograms if k[0] == name):
                hist_sum, count, bucket_counts = histograms[key]
                lines.extend(self._render_histogram(name, hist_sum, count, bucket_counts, key[1]))
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _render_line(name: str, value: float, label_tuple: tuple[tuple[str, str], ...]) -> str:
        labels = ",".join(f'{k}="{_escape_label(v)}"' for k, v in label_tuple)
        suffix = "{" + labels + "}" if labels else ""
        return f"{name}{suffix} {value}"

    def _render_histogram(
        self,
        name: str,
        hist_sum: float,
        count: int,
        bucket_counts: list[float],
        label_tuple: tuple[tuple[str, str], ...],
    ) -> list[str]:
        base_labels = ",".join(f'{k}="{_escape_label(v)}"' for k, v in label_tuple)
        prefix = f"{name}_bucket"
        lines: list[str] = []
        for idx, le in enumerate(self._buckets):
            labels = f'{base_labels},le="{le}"' if base_labels else f'le="{le}"'
            lines.append(f"{prefix}{{{labels}}} {bucket_counts[idx]:.0f}")
        inf_labels = f'{base_labels},le="+Inf"' if base_labels else 'le="+Inf"'
        lines.append(f"{prefix}{{{inf_labels}}} {bucket_counts[-1]:.0f}")
        if base_labels:
            lines.append(f"{name}_sum{{{base_labels}}} {hist_sum}")
            lines.append(f"{name}_count{{{base_labels}}} {count}")
        else:
            lines.append(f"{name}_sum {hist_sum}")
            lines.append(f"{name}_count {count}")
        return lines


metrics = MetricsRegistry()