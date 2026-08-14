from typing import TypeAlias

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User

# Permisos del spec §10.3
READ_TICKETS = "tickets:read"
REQUEST_AI_SUGGESTION = "ai:suggest"
EDIT_RESPONSE = "responses:edit"
SEND_RESPONSE = "responses:send"
CONFIGURE_TENANT = "tenant:configure"
VIEW_AUDIT = "audit:view"
MANAGE_AI_POLICIES = "ai_policies:manage"
KB_READ = "kb:read"
KB_EDIT = "kb:edit"
KB_PUBLISH = "kb:publish"
PERSONA_TICKETS = "persona:tickets"  # Portal de personas (usuario final)

Permission: TypeAlias = str

ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "agent": {READ_TICKETS, REQUEST_AI_SUGGESTION, EDIT_RESPONSE, SEND_RESPONSE, KB_READ},
    "supervisor": {
        READ_TICKETS,
        REQUEST_AI_SUGGESTION,
        EDIT_RESPONSE,
        SEND_RESPONSE,
        VIEW_AUDIT,
        KB_READ,
        KB_EDIT,
        KB_PUBLISH,
    },
    "tenant_admin": {
        READ_TICKETS,
        REQUEST_AI_SUGGESTION,
        EDIT_RESPONSE,
        SEND_RESPONSE,
        VIEW_AUDIT,
        CONFIGURE_TENANT,
        KB_READ,
        KB_EDIT,
        KB_PUBLISH,
    },
    "platform_admin": {
        READ_TICKETS,
        REQUEST_AI_SUGGESTION,
        EDIT_RESPONSE,
        SEND_RESPONSE,
        VIEW_AUDIT,
        CONFIGURE_TENANT,
        MANAGE_AI_POLICIES,
        KB_READ,
        KB_EDIT,
        KB_PUBLISH,
    },
    "customer": {PERSONA_TICKETS},
}

ROLE_NAMES: set[str] = set(ROLE_PERMISSIONS.keys())


def require_permissions(*required: Permission):
    def checker(user: User = Depends(get_current_user)) -> User:
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        if not required or any(perm in user_permissions for perm in required):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permiso insuficiente",
        )

    return checker


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role in roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol sin autorización",
        )

    return checker
