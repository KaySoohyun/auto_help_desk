#!/usr/bin/env python3
"""Seed de tenants, customers y tags de prueba.

Crea datos de prueba para desarrollo y testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.tag import Tag

TENANTS = [
    {"id": "test-tenant", "name": "Test Tenant", "slug": "test-tenant"},
    {"id": "acme-corp", "name": "Acme Corporation", "slug": "acme-corp"},
]

CUSTOMERS = [
    # test-tenant
    {"tenant_id": "test-tenant", "name": "Juan Pérez", "email": "juan.perez@example.com", "company": "Empresa A", "plan": "basic"},
    {"tenant_id": "test-tenant", "name": "María García", "email": "maria.garcia@example.com", "company": "Empresa B", "plan": "premium"},
    {"tenant_id": "test-tenant", "name": "Carlos López", "email": "carlos.lopez@example.com", "company": "Empresa C", "plan": "basic"},
    # acme-corp
    {"tenant_id": "acme-corp", "name": "Ana Rodríguez", "email": "ana.rodriguez@example.com", "company": "Acme Inc", "plan": "enterprise"},
    {"tenant_id": "acme-corp", "name": "Pedro Martínez", "email": "pedro.martinez@example.com", "company": "Acme Inc", "plan": "premium"},
    {"tenant_id": "acme-corp", "name": "Laura Fernández", "email": "laura.fernandez@example.com", "company": "Acme Inc", "plan": "basic"},
]

TAGS = [
    # test-tenant
    {"tenant_id": "test-tenant", "name": "urgente"},
    {"tenant_id": "test-tenant", "name": "facturacion"},
    {"tenant_id": "test-tenant", "name": "tecnico"},
    {"tenant_id": "test-tenant", "name": "consulta"},
    # acme-corp
    {"tenant_id": "acme-corp", "name": "prioridad-alta"},
    {"tenant_id": "acme-corp", "name": "reembolso"},
    {"tenant_id": "acme-corp", "name": "soporte"},
]


def seed_tenants() -> None:
    db = SessionLocal()
    try:
        for tenant_data in TENANTS:
            existing = db.query(Tenant).filter(Tenant.id == tenant_data["id"]).first()
            if existing:
                print(f"Tenant {tenant_data['id']} ya existe")
                continue

            tenant = Tenant(**tenant_data)
            db.add(tenant)
            db.commit()
            print(f"Tenant creado: {tenant.name} (id={tenant.id})")
    finally:
        db.close()


def seed_customers() -> None:
    db = SessionLocal()
    try:
        for customer_data in CUSTOMERS:
            existing = db.query(Customer).filter(
                Customer.tenant_id == customer_data["tenant_id"],
                Customer.email == customer_data["email"]
            ).first()
            if existing:
                print(f"Customer {customer_data['email']} ya existe en {customer_data['tenant_id']}")
                continue

            customer = Customer(**customer_data)
            db.add(customer)
            db.commit()
            print(f"Customer creado: {customer.name} (tenant={customer.tenant_id})")
    finally:
        db.close()


def seed_tags() -> None:
    db = SessionLocal()
    try:
        for tag_data in TAGS:
            existing = db.query(Tag).filter(
                Tag.tenant_id == tag_data["tenant_id"],
                Tag.name == tag_data["name"]
            ).first()
            if existing:
                print(f"Tag {tag_data['name']} ya existe en {tag_data['tenant_id']}")
                continue

            tag = Tag(**tag_data)
            db.add(tag)
            db.commit()
            print(f"Tag creado: {tag.name} (tenant={tag.tenant_id})")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding tenants...")
    seed_tenants()
    print("\nSeeding customers...")
    seed_customers()
    print("\nSeeding tags...")
    seed_tags()
    print("\n✓ Seed completado")
