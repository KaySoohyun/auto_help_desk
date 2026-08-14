#!/usr/bin/env python3
"""Crea la tabla `kb_categories` en bases existentes (idempotente).

`Base.metadata.create_all` la crea si no existe; este script la crea para
bases ya existentes donde no se pueda correr `create_all` sobre esa tabla.

Ejecutar:
    .venv/bin/python scripts/migrate_kb_categories.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine
from app.models.kb import KbCategory


def migrate():
    KbCategory.__table__.create(bind=engine, checkfirst=True)
    print("Tabla kb_categories verificada/creada.")


if __name__ == "__main__":
    migrate()
