from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.kb import KbArticle, KbArticleTag, KbArticleVersion
from app.models.tag import Tag
from app.repositories.base import TenantScopedRepository


class KbRepository(TenantScopedRepository[KbArticle]):
    def __init__(self, db: Session, tenant_id: str) -> None:
        super().__init__(db, KbArticle, tenant_id)

    def _get_or_create_tag(self, tag_name: str) -> Tag:
        """Obtiene o crea un tag por nombre para el tenant actual."""
        tag = self.db.query(Tag).filter(
            Tag.tenant_id == self.tenant_id,
            Tag.name == tag_name
        ).first()
        if not tag:
            tag = Tag(tenant_id=self.tenant_id, name=tag_name)
            self.db.add(tag)
            self.db.flush()
        return tag

    def get_tags(self, article_id: int) -> list[str]:
        stmt = (
            select(Tag.name)
            .join(KbArticleTag, KbArticleTag.tag_id == Tag.id)
            .where(KbArticleTag.article_id == article_id)
        )
        return list(self.db.scalars(stmt).all())

    def set_tags(self, article_id: int, tags: list[str]) -> None:
        self.db.execute(delete(KbArticleTag).where(KbArticleTag.article_id == article_id))
        for tag_name in tags:
            tag = self._get_or_create_tag(tag_name)
            self.db.add(KbArticleTag(article_id=article_id, tag_id=tag.id))
        self.db.flush()

    def _with_tags(self, article: KbArticle) -> dict:
        tags = self.get_tags(article.id)
        return {
            "id": article.id,
            "tenant_id": article.tenant_id,
            "title": article.title,
            "body": article.body,
            "category": article.category,
            "tags": tags,
            "status": article.status,
            "author_id": article.author_id,
            "current_version": article.current_version,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
            "published_at": article.published_at,
        }

    def _summary(self, article: KbArticle) -> dict:
        data = self._with_tags(article)
        del data["body"]
        return data

    def list(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        filters = [KbArticle.tenant_id == self.tenant_id]
        if status:
            filters.append(KbArticle.status == status)
        if category:
            filters.append(KbArticle.category == category)
        if tag:
            # Buscar artículos que tengan el tag por nombre
            tag_subq = (
                select(KbArticleTag.article_id)
                .join(Tag, KbArticleTag.tag_id == Tag.id)
                .where(Tag.name == tag, Tag.tenant_id == self.tenant_id)
            )
            filters.append(KbArticle.id.in_(tag_subq))
        if search:
            pattern = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(KbArticle.title).like(pattern),
                    func.lower(KbArticle.body).like(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(KbArticle).where(*filters)
        total = self.db.scalar(count_stmt) or 0

        stmt = (
            select(KbArticle)
            .where(*filters)
            .order_by(KbArticle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        articles = list(self.db.scalars(stmt).all())
        return [self._summary(a) for a in articles], total

    def get_or_none(self, pk) -> dict | None:
        article = super().get_or_none(pk)
        if article is None:
            return None
        return self._with_tags(article)

    def create(
        self,
        *,
        title: str,
        body: str,
        category: str | None,
        tags: list[str],
        author_id: int,
    ) -> dict:
        article = KbArticle(
            tenant_id=self.tenant_id,
            title=title,
            body=body,
            category=category,
            status="draft",
            author_id=author_id,
            current_version=1,
        )
        self.db.add(article)
        self.db.flush()
        self.set_tags(article.id, tags)
        version = KbArticleVersion(
            article_id=article.id,
            version=1,
            title=title,
            body=body,
            category=category,
            author_id=author_id,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(article)
        return self._with_tags(article)

    def update(
        self,
        pk,
        *,
        title: str | None = None,
        body: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        change_note: str | None = None,
        author_id: int,
    ) -> dict | None:
        article = super().get_or_none(pk)
        if article is None:
            return None
        if title is not None:
            article.title = title
        if body is not None:
            article.body = body
        if category is not None:
            article.category = category
        article.current_version += 1
        article.updated_at = datetime.now(UTC)
        if tags is not None:
            self.set_tags(article.id, tags)
        version = KbArticleVersion(
            article_id=article.id,
            version=article.current_version,
            title=article.title,
            body=article.body,
            category=article.category,
            author_id=author_id,
            change_note=change_note,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(article)
        return self._with_tags(article)

    def publish(self, pk) -> dict | None:
        article = super().get_or_none(pk)
        if article is None:
            return None
        if article.status != "draft":
            raise ValueError("Solo se puede publicar desde borrador")
        article.status = "published"
        article.published_at = datetime.now(UTC)
        article.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(article)
        return self._with_tags(article)

    def archive(self, pk) -> dict | None:
        article = super().get_or_none(pk)
        if article is None:
            return None
        if article.status != "published":
            raise ValueError("Solo se puede archivar desde publicado")
        article.status = "archived"
        article.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(article)
        return self._with_tags(article)

    def restore(self, pk) -> dict | None:
        article = super().get_or_none(pk)
        if article is None:
            return None
        if article.status != "archived":
            raise ValueError("Solo se puede restaurar desde archivado")
        article.status = "draft"
        article.published_at = None
        article.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(article)
        return self._with_tags(article)

    def list_versions(self, article_id: int) -> list[dict]:
        article = super().get_or_none(article_id)
        if article is None:
            raise PermissionError("Artículo no encontrado")
        stmt = (
            select(KbArticleVersion)
            .where(KbArticleVersion.article_id == article_id)
            .order_by(KbArticleVersion.version.desc())
        )
        versions = list(self.db.scalars(stmt).all())
        result = []
        for v in versions:
            result.append({
                "id": v.id,
                "article_id": v.article_id,
                "version": v.version,
                "title": v.title,
                "body": v.body,
                "category": v.category,
                "tags": self.get_tags(article_id) if v.version == article.current_version else [],
                "author_id": v.author_id,
                "change_note": v.change_note,
                "created_at": v.created_at,
            })
        return result
