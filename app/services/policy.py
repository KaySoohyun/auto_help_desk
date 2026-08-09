"""Resolución de políticas efectivas de IA en runtime (018, épica 6.5).

Conecta las políticas que la 016 expone por API (`TenantPolicy`, `GlobalPolicy`)
con el runtime: el orquestador y los servicios de IA usan estos valores efectivos
en lugar de leer `settings` directamente. Sin `GlobalPolicy` (fila 1) los valores
efectivos son los defaults de `.env`, por lo que el comportamiento no cambia.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.policy import GlobalPolicy
from app.services.admin import effective_global_policy


class PolicyResolver:
    """Devuelve los valores efectivos de la política global de IA para un request."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def effective_global(self) -> dict[str, Any]:
        """Valores efectivos de `GlobalPolicy`; sin fila, usa los defaults de `.env`."""
        policy = self._db.get(GlobalPolicy, 1)
        if policy is None:
            policy = GlobalPolicy(id=1)
        return effective_global_policy(policy)
