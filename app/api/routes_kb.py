import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_effective_tenant_ids
from app.core.permissions import KB_EDIT, KB_PUBLISH, KB_READ, require_permissions
from app.database import get_db
from app.models.user import User
from app.repositories.kb import KbRepository
from app.schemas.kb import (
    KbArticleCreate,
    KbArticleListOut,
    KbArticleOut,
    KbArticleSummaryOut,
    KbArticleUpdate,
    KbArticleVersionOut,
)
from app.services.audit import AuditService, get_audit_service

router = APIRouter(prefix="/v1/kb", tags=["kb"])


def _get_trace_id() -> str:
    return str(uuid.uuid4())


def _repo(db: Session, tenant_ids: list[str]) -> KbRepository:
    return KbRepository(db, tenant_ids=tenant_ids)


def _get_or_404(repo: KbRepository, article_id: int):
    try:
        article = repo.get_or_none(article_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado") from exc
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    return article


def _audit(
    audit: AuditService,
    user: User,
    tenant_id: str | None,
    action: str,
    article_id: int,
    trace_id: str,
    detail: dict | None = None,
) -> None:
    detail = dict(detail or {})
    detail["article_id"] = article_id
    audit.log(
        action,
        user_id=user.id,
        tenant_id=tenant_id,
        service="kb",
        model="KbArticle",
        trace_id=trace_id,
        detail=detail,
    )


def _audit_tenant(tenant_ids: list[str], user: User) -> str | None:
    return tenant_ids[0] if tenant_ids else user.tenant_id


@router.get("/articles", response_model=KbArticleListOut)
def list_articles(
    current_user: User = Depends(require_permissions(KB_READ)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|archived)$"),
    category: str | None = Query(default=None, max_length=100),
    tag: str | None = Query(default=None, max_length=50),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> KbArticleListOut:
    repo = _repo(db, tenant_ids)
    items, total = repo.list(
        status=status_filter,
        category=category,
        tag=tag,
        search=search,
        limit=limit,
        offset=offset,
    )
    return KbArticleListOut(
        items=[KbArticleSummaryOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/articles", response_model=KbArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: KbArticleCreate,
    current_user: User = Depends(require_permissions(KB_EDIT)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> KbArticleOut:
    repo = _repo(db, tenant_ids)
    article = repo.create(
        title=payload.title,
        body=payload.body,
        category=payload.category,
        tags=payload.tags,
        author_id=current_user.id,
    )
    _audit(audit, current_user, _audit_tenant(tenant_ids, current_user), "kb.article_created", article["id"], trace_id)
    return KbArticleOut(**article)


@router.get("/articles/{article_id}", response_model=KbArticleOut)
def get_article(
    article_id: int,
    current_user: User = Depends(require_permissions(KB_READ)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
) -> KbArticleOut:
    repo = _repo(db, tenant_ids)
    article = _get_or_404(repo, article_id)
    return KbArticleOut(**article)


@router.patch("/articles/{article_id}", response_model=KbArticleOut)
def update_article(
    article_id: int,
    payload: KbArticleUpdate,
    current_user: User = Depends(require_permissions(KB_EDIT)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> KbArticleOut:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sin cambios")
    repo = _repo(db, tenant_ids)
    _get_or_404(repo, article_id)
    article = repo.update(
        article_id,
        title=changes.get("title"),
        body=changes.get("body"),
        category=changes.get("category"),
        tags=changes.get("tags"),
        change_note=changes.get("change_note"),
        author_id=current_user.id,
    )
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    _audit(audit, current_user, _audit_tenant(tenant_ids, current_user), "kb.article_updated", article_id, trace_id, detail=changes)
    return KbArticleOut(**article)


@router.post("/articles/{article_id}/publish", response_model=KbArticleOut)
def publish_article(
    article_id: int,
    current_user: User = Depends(require_permissions(KB_PUBLISH)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> KbArticleOut:
    repo = _repo(db, tenant_ids)
    _get_or_404(repo, article_id)
    try:
        article = repo.publish(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    _audit(audit, current_user, _audit_tenant(tenant_ids, current_user), "kb.article_published", article_id, trace_id)
    return KbArticleOut(**article)


@router.post("/articles/{article_id}/archive", response_model=KbArticleOut)
def archive_article(
    article_id: int,
    current_user: User = Depends(require_permissions(KB_EDIT)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> KbArticleOut:
    repo = _repo(db, tenant_ids)
    _get_or_404(repo, article_id)
    try:
        article = repo.archive(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    _audit(audit, current_user, _audit_tenant(tenant_ids, current_user), "kb.article_archived", article_id, trace_id)
    return KbArticleOut(**article)


@router.post("/articles/{article_id}/restore", response_model=KbArticleOut)
def restore_article(
    article_id: int,
    current_user: User = Depends(require_permissions(KB_EDIT)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> KbArticleOut:
    repo = _repo(db, tenant_ids)
    _get_or_404(repo, article_id)
    try:
        article = repo.restore(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    _audit(audit, current_user, _audit_tenant(tenant_ids, current_user), "kb.article_restored", article_id, trace_id)
    return KbArticleOut(**article)


@router.get("/articles/{article_id}/versions", response_model=list[KbArticleVersionOut])
def list_versions(
    article_id: int,
    current_user: User = Depends(require_permissions(KB_READ)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
) -> list[KbArticleVersionOut]:
    repo = _repo(db, tenant_ids)
    _get_or_404(repo, article_id)
    try:
        versions = repo.list_versions(article_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado") from exc
    return [KbArticleVersionOut(**v) for v in versions]
