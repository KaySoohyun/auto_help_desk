from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KbArticle(Base):
    __tablename__ = "kb_articles"
    __table_args__ = (
        Index("ix_kb_articles_tenant_status", "tenant_id", "status"),
        Index("ix_kb_articles_tenant_category", "tenant_id", "category"),
        Index("ix_kb_articles_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    current_version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KbArticleVersion(Base):
    __tablename__ = "kb_article_versions"
    __table_args__ = (Index("ix_kb_versions_article_version", "article_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("kb_articles.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    change_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class KbArticleTag(Base):
    __tablename__ = "kb_article_tags"
    __table_args__ = (Index("ix_kb_tags_article_tag", "article_id", "tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("kb_articles.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(50), index=True)
