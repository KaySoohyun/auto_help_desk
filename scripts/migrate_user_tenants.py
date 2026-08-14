#!/usr/bin/env python3
"""Migración de users.tenant_id a user_tenants.

Este script migra los datos existentes de la columna tenant_id en la tabla users
a la nueva tabla user_tenants para soportar multi-tenant real.

Ejecutar DESPUÉS de crear la tabla user_tenants y ANTES de eliminar users.tenant_id.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database import SessionLocal, engine, Base


def migrate_user_tenants():
    """Migra users.tenant_id a user_tenants."""
    # Crear la tabla user_tenants si no existe
    from app.models.user_tenant import UserTenant
    UserTenant.__table__.create(bind=engine, checkfirst=True)
    print("Tabla user_tenants verificada/creada.")
    
    db = SessionLocal()
    try:
        # Verificar si la columna tenant_id existe en users
        result = db.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'tenant_id'
        """))
        has_tenant_id = result.scalar() > 0
        
        if not has_tenant_id:
            print("La columna users.tenant_id no existe. Migración ya completada o no necesaria.")
            return
        
        # Primero, crear los tenants que faltan en la tabla tenants
        print("Verificando tenants faltantes...")
        db.execute(text("""
            INSERT INTO tenants (id, name, slug, created_at)
            SELECT DISTINCT tenant_id, tenant_id, tenant_id, NOW()
            FROM users
            WHERE tenant_id IS NOT NULL
            AND tenant_id NOT IN (SELECT id FROM tenants)
        """))
        db.commit()
        print("Tenants faltantes creados.")
        
        # Contar usuarios con tenant_id
        result = db.execute(text("""
            SELECT COUNT(*) FROM users WHERE tenant_id IS NOT NULL
        """))
        count = result.scalar()
        print(f"Encontrados {count} usuarios con tenant_id para migrar.")
        
        if count == 0:
            print("No hay usuarios para migrar.")
            return
        
        # Migrar datos a user_tenants
        # Usamos el role de users como role en user_tenants
        db.execute(text("""
            INSERT INTO user_tenants (user_id, tenant_id, role, created_at)
            SELECT id, tenant_id, role, created_at
            FROM users
            WHERE tenant_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM user_tenants 
                WHERE user_tenants.user_id = users.id 
                AND user_tenants.tenant_id = users.tenant_id
            )
        """))
        
        db.commit()
        
        # Verificar migración
        result = db.execute(text("""
            SELECT COUNT(*) FROM user_tenants
        """))
        migrated_count = result.scalar()
        print(f"Migración completada. {migrated_count} registros en user_tenants.")
        
        # Verificar que todos los usuarios con tenant_id fueron migrados
        result = db.execute(text("""
            SELECT COUNT(*) FROM users u
            WHERE u.tenant_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM user_tenants ut
                WHERE ut.user_id = u.id AND ut.tenant_id = u.tenant_id
            )
        """))
        missing = result.scalar()
        
        if missing > 0:
            print(f"ADVERTENCIA: {missing} usuarios no fueron migrados correctamente.")
        else:
            print("Todos los usuarios fueron migrados correctamente.")
        
    except Exception as e:
        db.rollback()
        print(f"Error durante la migración: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Iniciando migración de users.tenant_id a user_tenants...")
    migrate_user_tenants()
    print("Migración completada.")
