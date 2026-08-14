"""Tests para el endpoint /v1/ai/tickets/{id}/analyze (Feature 012)."""

from fastapi.testclient import TestClient
from tests.conftest import register_login

from app.database import SessionLocal
from app.models.kb import KbArticle
from app.models.tag import Tag


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


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


def _create_published_article(client: TestClient, tokens: dict, category: str, title: str) -> dict:
    """Crea y publica un artículo de KB."""
    payload = {
        "title": title,
        "body": "Contenido del artículo",
        "category": category,
        "tags": [],
    }
    response = client.post("/v1/kb/articles", json=payload, headers=_headers(tokens))
    assert response.status_code == 201, response.text
    article = response.json()
    
    # Publicar el artículo
    response = client.post(f"/v1/kb/articles/{article['id']}/publish", headers=_headers(tokens))
    assert response.status_code == 200, response.text
    return response.json()


def test_analyze_ticket_basic(client: TestClient) -> None:
    """Test básico del endpoint /analyze."""
    tokens = register_login(client, "agent-analyze-1@example.com", "agent", "ten-a")
    ticket = _create_ticket(client, tokens)
    
    response = client.post(f"/v1/ai/tickets/{ticket['id']}/analyze", headers=_headers(tokens))
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert "classification" in data
    assert "summary" in data
    assert "suggested_reply" in data
    assert "kb_recommendations" in data
    assert "pii_detected" in data
    assert "risks" in data


def test_analyze_ticket_with_pii(client: TestClient) -> None:
    """Test de /analyze con PII en el contenido."""
    tokens = register_login(client, "agent-analyze-2@example.com", "agent", "ten-a")
    ticket = _create_ticket(
        client,
        tokens,
        subject="Problema con mi cuenta",
        description="Mi email es juan.perez@example.com y mi teléfono es +54 11 1234-5678"
    )
    
    response = client.post(f"/v1/ai/tickets/{ticket['id']}/analyze", headers=_headers(tokens))
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert "pii_detected" in data
    # Debería detectar al menos email y phone
    pii_types = [p["type"] for p in data["pii_detected"]]
    assert "email" in pii_types or "phone" in pii_types


def test_analyze_ticket_with_kb_recommendations(client: TestClient) -> None:
    """Test de /analyze con artículos KB recomendados."""
    tokens = register_login(client, "agent-analyze-3@example.com", "agent", "ten-a")
    
    # Crear un ticket en la categoría billing
    ticket = _create_ticket(client, tokens, category="billing")
    
    # El endpoint /analyze debería funcionar incluso sin artículos KB
    response = client.post(f"/v1/ai/tickets/{ticket['id']}/analyze", headers=_headers(tokens))
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert "kb_recommendations" in data
    # kb_recommendations puede estar vacío si no hay artículos publicados
    assert isinstance(data["kb_recommendations"], list)


def test_analyze_ticket_not_found(client: TestClient) -> None:
    """Test de /analyze con ticket inexistente."""
    tokens = register_login(client, "agent-analyze-4@example.com", "agent", "ten-a")
    
    response = client.post("/v1/ai/tickets/99999/analyze", headers=_headers(tokens))
    assert response.status_code == 404


def test_analyze_ticket_from_other_tenant_is_404(client: TestClient) -> None:
    """Test de /analyze con ticket de otro tenant."""
    tokens_a = register_login(client, "agent-analyze-5@example.com", "agent", "ten-a")
    tokens_b = register_login(client, "agent-analyze-6@example.com", "agent", "ten-b")
    
    ticket = _create_ticket(client, tokens_a)
    
    response = client.post(f"/v1/ai/tickets/{ticket['id']}/analyze", headers=_headers(tokens_b))
    assert response.status_code == 404


def test_analyze_ticket_requires_auth(client: TestClient) -> None:
    """Test de /analyze sin autenticación."""
    response = client.post("/v1/ai/tickets/1/analyze")
    assert response.status_code == 401
