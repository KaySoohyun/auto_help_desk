from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.hash import argon2

from app.core.config import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenError(Exception):
    """Base para errores de token (diferenciar 401 inválido vs expirado)."""


class TokenExpiredError(TokenError):
    """El token está vencido."""


class TokenInvalidError(TokenError):
    """El token no es válido (firma, claims, issuer o audiencia)."""


def hash_password(password: str) -> str:
    return argon2.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return argon2.verify(password, password_hash)


def _create_token(
    token_type: str,
    subject: str,
    tenant_id: str,
    roles: list[str],
    expires_delta: timedelta,
    jti: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": roles,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str,
    tenant_id: str,
    roles: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(TOKEN_TYPE_ACCESS, subject, tenant_id, roles, delta)


def create_refresh_token(
    subject: str,
    tenant_id: str,
    roles: list[str],
    jti: str,
    expires_delta: timedelta | None = None,
) -> str:
    delta = expires_delta or timedelta(days=settings.refresh_token_expire_days)
    return _create_token(TOKEN_TYPE_REFRESH, subject, tenant_id, roles, delta, jti=jti)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Token inválido") from exc
    return payload
