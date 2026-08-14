#!/usr/bin/env python3
"""Migración de `kb_article_tags`: `tag` (string) → `tag_id` (FK a tags.id).

La Feature 019 normalizó los tags de artículos a la tabla `tags` con FK. En
bases existentes la tabla `kb_article_tags` quedó con la columna legacy `tag`
(string) y sin `tag_id`, rompiendo todas las operaciones KB.

Este script:
1. Agrega `tag_id` (nullable).
2. Para cada fila, crea (si falta) el `Tag` por nombre en el tenant del artículo
   y setea `tag_id`.
3. Elimina la columna `tag` y deja `tag_id` NOT NULL.

Ejecutar:
    .venv/bin/python scripts/migrate_kb_article_tags.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import SessionLocal
from app.models.tag import Tag


def migrate():
    db = SessionLocal()
    try:
        has_tag_id = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'kb_article_tags' "
                "AND column_name = 'tag_id'"
            )
        ).scalar()

        if has_tag_id == 0:
            print("Agregando kb_article_tags.tag_id ...")
            db.execute(text("ALTER TABLE kb_article_tags ADD COLUMN tag_id INTEGER"))
            db.commit()

            rows = db.execute(text("SELECT id, article_id, tag FROM kb_article_tags")).fetchall()
            for row_id, article_id, tag_name in rows:
                tenant_id = db.execute(
                    text("SELECT tenant_id FROM kb_articles WHERE id = :a"), {"a": article_id}
                ).scalar()
                if tenant_id is None:
                    continue
                tag = (
                    db.query(Tag)
                    .filter(Tag.tenant_id == tenant_id, Tag.name == tag_name)
                    .first()
                )
                if tag is None:
                    tag = Tag(tenant_id=tenant_id, name=tag_name)
                    db.add(tag)
                    db.flush()
                db.execute(
                    text("UPDATE kb_article_tags SET tag_id = :t WHERE id = :r"),
                    {"t": tag.id, "r": row_id},
                )
            db.commit()

            db.execute(text("ALTER TABLE kb_article_tags DROP COLUMN tag"))
            db.execute(text("ALTER TABLE kb_article_tags ALTER COLUMN tag_id SET NOT NULL"))
            db.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_kb_tags_article_tag "
                    "ON kb_article_tags (article_id, tag_id)"
                )
            )
            db.commit()
            print(f"Migración completada: {len(rows)} filas migradas a tag_id.")
        else:
            print("kb_article_tags.tag_id ya existe. Nada que hacer.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
