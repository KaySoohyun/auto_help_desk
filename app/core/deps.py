from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TOKEN_TYPE_ACCESS, TokenError, TokenExpiredError, decode_token
from app.database import get_db
from app.models.user import User
from app.repositories.user_tenant import UserTenantRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_trace_id() -> str:
    """Identificador de correlación único por request (spec §11.2)."""
    import uuid

    return str(uuid.uuid4())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")
    return user


def get_tenant_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Devuelve el tenant_id del token validado.

    El tenant_id siempre proviene de los claims del JWT, nunca de inputs del cliente
    (spec §10.2, ADR-001).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant no definido",
        )
    return tenant_id


def get_token_tenant_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """Devuelve el tenant_id activo del JWT o None si no se seleccionó ninguno.

    A diferencia de `get_tenant_id`, no falla cuando el token no tiene tenant:
    es el caso de un usuario que salteó la selección y opera sobre todos sus tenants.
    """
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except TokenError:
        return None
    tenant_id = payload.get("tenant_id")
    return tenant_id or None


def get_effective_tenant_ids(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    """Resuelve el alcance de tenants del usuario para la sesión actual.

    - Si el JWT trae `tenant_id` (el usuario seleccionó o cambió a un tenant activo),
      se usa ese único tenant (validando que el usuario pertenezca a él).
    - Si no trae `tenant_id` (el usuario salteó la selección), se usan **todos** los
      tenants del usuario (`user_tenants`; fallback a `users.tenant_id` legacy para
      usuarios migrados sin membresías).

    Devuelve 403 si el usuario no tiene ningún tenant asignado.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
        )

    try:
        payload = decode_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token_tenant = payload.get("tenant_id")

    if token_tenant:
        repo = UserTenantRepository(db)
        # El tenant del token fue emitido por el backend. Se acepta si el usuario
        # tiene membresía o si es su tenant legacy (usuarios previos a user_tenants).
        if not repo.user_has_tenant(user.id, token_tenant) and user.tenant_id != token_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este tenant",
            )
        return [token_tenant]

    repo = UserTenantRepository(db)
    memberships = repo.get_user_tenants(user.id)
    tenant_ids = [m.tenant_id for m in memberships]
    if not tenant_ids and user.tenant_id:
        tenant_ids = [user.tenant_id]
    if not tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol sin tenant asignado",
        )
    return tenant_ids


def get_effective_tenant_ids_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[str]:
    """Igual que `get_effective_tenant_ids` pero sin fallar si el usuario no tiene tenants.

    Devuelve `[]` cuando no hay alcance. Útil en rutas de administración donde el
    `platform_admin` (sin tenant) opera a nivel plataforma y la lógica de negocio
    decide el tenant destino.
    """
    token_tenant = None
    if credentials is not None:
        try:
            payload = decode_token(credentials.credentials)
        except TokenError:
            token_tenant = None
        else:
            token_tenant = payload.get("tenant_id") or None

    if token_tenant:
        return [token_tenant]

    repo = UserTenantRepository(db)
    memberships = repo.get_user_tenants(user.id)
    tenant_ids = [m.tenant_id for m in memberships]
    if not tenant_ids and user.tenant_id:
        tenant_ids = [user.tenant_id]
    return tenant_ids
