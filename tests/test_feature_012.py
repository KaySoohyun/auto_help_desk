"""Tests para los endpoints de tags, customers y tenants (Feature 012)."""

from fastapi.testclient import TestClient
from tests.conftest import register_login

from app.database import SessionLocal
from app.models.tag import Tag
from app.models.customer import Customer
from app.models.tenant import Tenant


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_tenant(tenant_id: str, name: str, slug: str) -> None:
    """Crea un tenant en la base de datos."""
    db = SessionLocal()
    try:
        tenant = Tenant(id=tenant_id, name=name, slug=slug)
        db.add(tenant)
        db.commit()
    finally:
        db.close()


def _create_ticket(client: TestClient, tokens: dict, **overrides) -> dict:
    payload = {
        "subject": "Problema de facturación",
        "description": "El sistema no genera la factura del mes",
        "category": "billing",
        "priority": "high",
    }
    payload.update(overrides)
    response = client.post("/v1/tickets", json=payload, headers=_headers(tokens))
    assert response.status_code == 201, response.text
    return response.json()


# === Tests de Tags ===

def test_list_ticket_tags_empty(client: TestClient) -> None:
    """Test de listar tags de un ticket sin tags."""
    tokens = register_login(client, "agent-tags-1@example.com", "agent", "ten-a")
    ticket = _create_ticket(client, tokens)
    
    response = client.get(f"/v1/tickets/{ticket['id']}/tags", headers=_headers(tokens))
    assert response.status_code == 200
    assert response.json() == []


def test_add_and_list_ticket_tags(client: TestClient) -> None:
    """Test de agregar y listar tags de un ticket."""
    tokens = register_login(client, "agent-tags-2@example.com", "agent", "ten-a")
    ticket = _create_ticket(client, tokens)
    
    # Crear un tag manualmente
    db = SessionLocal()
    try:
        tag = Tag(tenant_id="ten-a", name="urgente")
        db.add(tag)
        db.commit()
        db.refresh(tag)
        tag_id = tag.id
    finally:
        db.close()
    
    # Agregar el tag al ticket
    response = client.post(
        f"/v1/tickets/{ticket['id']}/tags",
        json={"tag_id": tag_id},
        headers=_headers(tokens)
    )
    assert response.status_code == 201, response.text
    
    # Listar los tags
    response = client.get(f"/v1/tickets/{ticket['id']}/tags", headers=_headers(tokens))
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 1
    assert tags[0]["name"] == "urgente"


def test_remove_ticket_tag(client: TestClient) -> None:
    """Test de quitar un tag de un ticket."""
    tokens = register_login(client, "agent-tags-3@example.com", "agent", "ten-a")
    ticket = _create_ticket(client, tokens)
    
    # Crear un tag manualmente
    db = SessionLocal()
    try:
        tag = Tag(tenant_id="ten-a", name="facturacion")
        db.add(tag)
        db.commit()
        db.refresh(tag)
        tag_id = tag.id
    finally:
        db.close()
    
    # Agregar el tag al ticket
    response = client.post(
        f"/v1/tickets/{ticket['id']}/tags",
        json={"tag_id": tag_id},
        headers=_headers(tokens)
    )
    assert response.status_code == 201
    
    # Quitar el tag
    response = client.delete(
        f"/v1/tickets/{ticket['id']}/tags/{tag_id}",
        headers=_headers(tokens)
    )
    assert response.status_code == 204
    
    # Verificar que se quitó
    response = client.get(f"/v1/tickets/{ticket['id']}/tags", headers=_headers(tokens))
    assert response.status_code == 200
    assert response.json() == []


def test_add_duplicate_tag_is_409(client: TestClient) -> None:
    """Test de agregar un tag duplicado a un ticket."""
    tokens = register_login(client, "agent-tags-4@example.com", "agent", "ten-a")
    ticket = _create_ticket(client, tokens)
    
    # Crear un tag manualmente
    db = SessionLocal()
    try:
        tag = Tag(tenant_id="ten-a", name="duplicado")
        db.add(tag)
        db.commit()
        db.refresh(tag)
        tag_id = tag.id
    finally:
        db.close()
    
    # Agregar el tag al ticket
    response = client.post(
        f"/v1/tickets/{ticket['id']}/tags",
        json={"tag_id": tag_id},
        headers=_headers(tokens)
    )
    assert response.status_code == 201
    
    # Intentar agregarlo de nuevo
    response = client.post(
        f"/v1/tickets/{ticket['id']}/tags",
        json={"tag_id": tag_id},
        headers=_headers(tokens)
    )
    assert response.status_code == 409


# === Tests de Customers ===

def test_list_customers(client: TestClient) -> None:
    """Test de listar customers del tenant."""
    tokens = register_login(client, "agent-cust-1@example.com", "agent", "ten-a")
    
    response = client.get("/v1/customers", headers=_headers(tokens))
    assert response.status_code == 200
    # Los customers del seed deberían estar disponibles
    customers = response.json()
    assert isinstance(customers, list)


def test_get_customer_by_id(client: TestClient) -> None:
    """Test de obtener un customer por ID."""
    tokens = register_login(client, "agent-cust-2@example.com", "agent", "ten-a")
    
    # Crear un customer manualmente
    db = SessionLocal()
    try:
        customer = Customer(
            tenant_id="ten-a",
            name="Test Customer",
            email="test@example.com",
            company="Test Company",
            plan="basic"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        customer_id = customer.id
    finally:
        db.close()
    
    response = client.get(f"/v1/customers/{customer_id}", headers=_headers(tokens))
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Customer"
    assert data["email"] == "test@example.com"


def test_get_customer_from_other_tenant_is_404(client: TestClient) -> None:
    """Test de obtener un customer de otro tenant."""
    tokens_a = register_login(client, "agent-cust-3@example.com", "agent", "ten-a")
    tokens_b = register_login(client, "agent-cust-4@example.com", "agent", "ten-b")
    
    # Crear un customer en ten-a
    db = SessionLocal()
    try:
        customer = Customer(
            tenant_id="ten-a",
            name="Customer A",
            email="a@example.com"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        customer_id = customer.id
    finally:
        db.close()
    
    # Intentar obtenerlo desde ten-b
    response = client.get(f"/v1/customers/{customer_id}", headers=_headers(tokens_b))
    assert response.status_code == 404


# === Tests de Tenants ===

def test_list_tenants(client: TestClient) -> None:
    """Test de listar tenants."""
    # Crear tenants para el test
    _create_tenant("test-tenant-1", "Test Tenant 1", "test-tenant-1")
    _create_tenant("test-tenant-2", "Test Tenant 2", "test-tenant-2")
    
    # Usar un usuario con permisos de auditoría
    tokens = register_login(client, "supervisor-tenants@example.com", "supervisor", "ten-a")
    
    response = client.get("/v1/tenants", headers=_headers(tokens))
    assert response.status_code == 200
    tenants = response.json()
    assert isinstance(tenants, list)
    # Debería haber al menos los 2 tenants creados
    assert len(tenants) >= 2


def test_get_tenant_by_id(client: TestClient) -> None:
    """Test de obtener un tenant por ID."""
    # Crear el tenant para el test
    _create_tenant("ten-a", "Tenant A", "ten-a")
    
    tokens = register_login(client, "supervisor-tenant@example.com", "supervisor", "ten-a")
    
    response = client.get("/v1/tenants/ten-a", headers=_headers(tokens))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ten-a"


def test_get_tenant_not_found(client: TestClient) -> None:
    """Test de obtener un tenant inexistente."""
    tokens = register_login(client, "supervisor-tenant2@example.com", "supervisor", "ten-a")
    
    response = client.get("/v1/tenants/non-existent", headers=_headers(tokens))
    assert response.status_code == 404
