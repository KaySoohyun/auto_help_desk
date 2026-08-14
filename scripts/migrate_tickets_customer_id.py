#!/usr/bin/env python3
"""Migración de esquema de `tickets` en bases existentes.

`Base.metadata.create_all` no altera tablas ya existentes, por lo que los cambios
al modelo `Ticket` (Feature 012) no se reflejan en entornos con la tabla ya creada
(p. ej. Supabase). Este script aplica los ALTER idempotentes:

1. Agrega `tickets.customer_id` (FK a customers.id) si no existe.
2. Da un default a `tickets.language` (columna NOT NULL sin default que el modelo
   ya no usa) para que los INSERT del modelo actual no fallen.

Ejecutar:
    .venv/bin/python scripts/migrate_tickets_customer_id.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import SessionLocal


def migrate():
    """Aplica los ALTER de tickets idempotentes."""
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'tickets' "
                "AND column_name = 'customer_id'"
            )
        )
        if result.scalar() == 0:
            print("Agregando tickets.customer_id ...")
            db.execute(
                text(
                    "ALTER TABLE tickets ADD COLUMN customer_id INTEGER "
                    "REFERENCES customers(id)"
                )
            )
            db.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_tickets_tenant_customer "
                    "ON tickets (tenant_id, customer_id)"
                )
            )
            db.commit()
        else:
            print("tickets.customer_id ya existe.")

        # language es NOT NULL sin default y el modelo actual no la escribe.
        lang_result = db.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'tickets' "
                "AND column_name = 'language'"
            )
        )
        lang_default = lang_result.scalar()
        if lang_default is None:
            print("Agregando default a tickets.language ...")
            db.execute(text("ALTER TABLE tickets ALTER COLUMN language SET DEFAULT 'es'"))
            db.commit()
        else:
            print("tickets.language ya tiene default.")

        print("Migración completada.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
