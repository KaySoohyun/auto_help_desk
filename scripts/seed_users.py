#!/usr/bin/env python3
"""Seed de usuarios de prueba, uno por cada rol.

Crea usuarios con credenciales conocidas para desarrollo y testing.
Las credenciales se documentan en .env.example.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User

USERS = [
    {
        "email": "agent@example.com",
        "password": "agent-pass-123",
        "role": "agent",
        "tenant_id": "test-tenant",
    },
    {
        "email": "supervisor@example.com",
        "password": "supervisor-pass-123",
        "role": "supervisor",
        "tenant_id": "test-tenant",
    },
    {
        "email": "tenant-admin@example.com",
        "password": "tenant-admin-pass-123",
        "role": "tenant_admin",
        "tenant_id": "test-tenant",
    },
    {
        "email": "platform-admin@example.com",
        "password": "platform-admin-pass-123",
        "role": "platform_admin",
        "tenant_id": None,
    },
]


def seed_users() -> None:
    db = SessionLocal()
    try:
        for user_data in USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"Usuario {user_data['email']} ya existe (id={existing.id})")
                continue

            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                tenant_id=user_data["tenant_id"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Usuario creado: {user.email} (id={user.id}, role={user.role})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
