#!/usr/bin/env python3
"""Migración: agrega `customers.user_id` (FK a users.id, unique, nullable).

El portal de personas (rol `customer`) vincula cada usuario a su fila en
`customers` para aislar "mis tickets". `Base.metadata.create_all` no altera
tablas existentes, por lo que este script aplica el ALTER idempotente.

Ejecutar:
    .venv/bin/python scripts/migrate_customers_user_id.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import SessionLocal


def migrate():
    """Agrega customers.user_id si no existe (idempotente)."""
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'customers' "
                "AND column_name = 'user_id'"
            )
        )
        if result.scalar() > 0:
            print("customers.user_id ya existe. Nada que hacer.")
            return

        print("Agregando customers.user_id ...")
        db.execute(
            text("ALTER TABLE customers ADD COLUMN user_id INTEGER REFERENCES users(id)")
        )
        db.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_user_id "
                "ON customers (user_id)"
            )
        )
        db.commit()
        print("Migración completada: customers.user_id agregado.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
