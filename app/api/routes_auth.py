import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.tenant import Tenant
from app.models.token import RefreshToken
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.repositories.user_tenant import UserTenantRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SwitchTenantRequest,
    TenantInfo,
    TokenResponse,
    UserOut,
)
from app.services.audit import AuditService, get_audit_service

router = APIRouter(prefix="/auth", tags=["auth"])

PUBLIC_REGISTRATION_ROLES = {"agent", "supervisor"}


def _get_user_tenants(user: User, db: Session) -> list[TenantInfo]:
    """Obtiene la lista de tenants a los que pertenece un usuario."""
    repo = UserTenantRepository(db)
    memberships = repo.get_user_tenants(user.id)
    
    tenants = []
    for membership in memberships:
        tenant = db.get(Tenant, membership.tenant_id)
        if tenant:
            tenants.append(TenantInfo(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=membership.role
            ))
    
    return tenants


def _user_to_user_out(user: User, db: Session) -> UserOut:
    """Convierte un User a UserOut incluyendo la lista de tenants."""
    tenants = _get_user_tenants(user, db)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        created_at=user.created_at,
        tenants=tenants
    )


def _issue_tokens(user: User, db: Session, tenant_id: str | None = None) -> TokenResponse:
    """Emite tokens para un usuario, opcionalmente para un tenant específico."""
    jti = str(uuid.uuid4())
    access_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_expires = timedelta(days=settings.refresh_token_expire_days)

    # Si no se especifica tenant_id, usar el tenant principal del usuario
    effective_tenant_id = tenant_id or user.tenant_id or ""
    
    # Obtener el rol del usuario en el tenant específico
    role = user.role
    if tenant_id:
        repo = UserTenantRepository(db)
        tenant_role = repo.get_user_role_in_tenant(user.id, tenant_id)
        if tenant_role:
            role = tenant_role

    access_token = create_access_token(
        subject=str(user.id),
        tenant_id=effective_tenant_id,
        roles=[role],
        expires_delta=access_expires,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        tenant_id=effective_tenant_id,
        roles=[role],
        jti=jti,
        expires_delta=refresh_expires,
    )

    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=datetime.now(UTC) + refresh_expires,
            revoked=False,
        )
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> UserOut:
    if payload.role not in PUBLIC_REGISTRATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol no permitido en el registro público",
        )
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        tenant_id=payload.tenant_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Si se especificó un tenant_id, crear la membresía en user_tenants
    if payload.tenant_id:
        repo = UserTenantRepository(db)
        repo.create(user.id, payload.tenant_id, payload.role)
    
    audit.log(
        "auth.user_registered",
        user_id=user.id,
        tenant_id=user.tenant_id,
        service="auth",
        result="success",
        detail={"role": user.role},
    )
    return _user_to_user_out(user, db)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        audit.log(
            "auth.login_failed",
            service="auth",
            detail={"email": payload.email},
            result="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    # Si se especificó un tenant_id, verificar que el usuario pertenezca a ese tenant
    if payload.tenant_id:
        repo = UserTenantRepository(db)
        if not repo.user_has_tenant(user.id, payload.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este tenant",
            )
    
    audit.log(
        "auth.login_success",
        user_id=user.id,
        tenant_id=payload.tenant_id or user.tenant_id,
        service="auth",
        result="success",
    )
    return _issue_tokens(user, db, payload.tenant_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except TokenExpiredError as exc:
        audit.log("auth.refresh_failed", service="auth", result="failure", detail={"reason": "expired"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco expirado") from exc
    except TokenInvalidError as exc:
        audit.log("auth.refresh_failed", service="auth", result="failure", detail={"reason": "invalid"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco inválido") from exc

    if claims.get("type") != TOKEN_TYPE_REFRESH:
        audit.log("auth.refresh_failed", service="auth", result="failure", detail={"reason": "wrong_type"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco inválido")

    stored = db.get(RefreshToken, claims.get("jti"))
    if stored is None or stored.revoked:
        audit.log("auth.refresh_failed", service="auth", result="failure", detail={"reason": "revoked"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco revocado")

    if datetime.now(UTC).replace(tzinfo=None) > stored.expires_at.replace(tzinfo=None):
        stored.revoked = True
        db.commit()
        audit.log("auth.refresh_failed", service="auth", result="failure", detail={"reason": "expired"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco expirado")

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")

    stored.revoked = True
    stored.revoked_at = datetime.now(UTC)
    db.commit()

    # Usar el tenant_id del token anterior
    tenant_id = claims.get("tenant_id")
    
    audit.log(
        "auth.refresh",
        user_id=user.id,
        tenant_id=tenant_id,
        service="auth",
        result="success",
    )
    return _issue_tokens(user, db, tenant_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    try:
        claims = decode_token(payload.refresh_token)
    except TokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco inválido")

    stored = db.get(RefreshToken, claims.get("jti"))
    if stored is not None and not stored.revoked:
        stored.revoked = True
        stored.revoked_at = datetime.now(UTC)
        db.commit()

    audit.log(
        "auth.logout",
        user_id=int(claims["sub"]) if claims.get("sub") else None,
        tenant_id=claims.get("tenant_id") or None,
        service="auth",
        result="success",
    )


@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> UserOut:
    audit.log(
        "auth.access_me",
        user_id=user.id,
        tenant_id=user.tenant_id,
        service="auth",
        result="success",
    )
    return _user_to_user_out(user, db)


@router.post("/switch-tenant", response_model=TokenResponse)
def switch_tenant(
    payload: SwitchTenantRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    """Cambia al tenant especificado. El usuario debe pertenecer a ese tenant."""
    repo = UserTenantRepository(db)
    
    # Verificar que el usuario pertenezca al tenant
    if not repo.user_has_tenant(user.id, payload.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tenant",
        )
    
    # Verificar que el tenant existe
    tenant = db.get(Tenant, payload.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    
    audit.log(
        "auth.switch_tenant",
        user_id=user.id,
        tenant_id=payload.tenant_id,
        service="auth",
        result="success",
    )
    
    # Emitir nuevos tokens para el tenant seleccionado
    return _issue_tokens(user, db, payload.tenant_id)


@router.get("/tenants", response_model=list[TenantInfo])
def list_user_tenants(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TenantInfo]:
    """Lista todos los tenants a los que pertenece el usuario autenticado."""
    return _get_user_tenants(user, db)
