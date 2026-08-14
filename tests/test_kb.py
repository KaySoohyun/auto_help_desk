from fastapi.testclient import TestClient
from tests.conftest import register_login

from app.database import SessionLocal
from app.models.audit import AuditEvent


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_article(client: TestClient, tokens: dict, **overrides) -> dict:
    payload = {
        "title": "Cómo resetear contraseña",
        "body": "Pasos para resetear la contraseña del sistema...",
        "category": "account",
        "tags": ["password", "login"],
    }
    payload.update(overrides)
    response = client.post("/v1/kb/articles", json=payload, headers=_headers(tokens))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    article = _create_article(client, tokens)
    assert article["title"] == "Cómo resetear contraseña"
    assert article["body"] == "Pasos para resetear la contraseña del sistema..."
    assert article["category"] == "account"
    assert set(article["tags"]) == {"password", "login"}
    assert article["status"] == "draft"
    assert article["current_version"] == 1
    assert article["tenant_id"] == "ten-a"


def test_create_article_requires_auth(client: TestClient) -> None:
    assert client.post("/v1/kb/articles", json={}).status_code == 401


def test_create_article_requires_permission(client: TestClient) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten-a")
    response = client.post(
        "/v1/kb/articles",
        json={"title": "Test", "body": "Body"},
        headers=_headers(tokens),
    )
    assert response.status_code == 403


def test_list_articles(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    _create_article(client, tokens, title="Artículo 1")
    _create_article(client, tokens, title="Artículo 2", category="billing")
    response = client.get("/v1/kb/articles", headers=_headers(tokens))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2
    for item in body["items"]:
        assert "body" not in item


def test_list_articles_with_filters(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    _create_article(client, tokens, title="Login issue", category="account")
    _create_article(client, tokens, title="Billing issue", category="billing")
    response = client.get(
        "/v1/kb/articles",
        headers=_headers(tokens),
        params={"category": "account"},
    )
    assert response.status_code == 200
    body = response.json()
    assert all(item["category"] == "account" for item in body["items"])


def test_list_articles_with_search(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    _create_article(client, tokens, title="Problema de facturación", body="Factura pendiente")
    _create_article(client, tokens, title="Problema de acceso", body="No puede entrar")
    response = client.get(
        "/v1/kb/articles",
        headers=_headers(tokens),
        params={"search": "facturación"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert any("facturación" in item["title"].lower() for item in body["items"])


def test_list_articles_with_tag_filter(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    _create_article(client, tokens, title="Art 1", tags=["password", "login"])
    _create_article(client, tokens, title="Art 2", tags=["billing"])
    response = client.get(
        "/v1/kb/articles",
        headers=_headers(tokens),
        params={"tag": "password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert all("password" in item["tags"] for item in body["items"])


def test_get_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    response = client.get(f"/v1/kb/articles/{created['id']}", headers=_headers(tokens))
    assert response.status_code == 200
    article = response.json()
    assert article["id"] == created["id"]
    assert article["body"] == created["body"]


def test_get_article_from_other_tenant_is_404(client: TestClient) -> None:
    tokens_a = register_login(client, "sup-a@example.com", "supervisor", "ten-a")
    tokens_b = register_login(client, "sup-b@example.com", "supervisor", "ten-b")
    created = _create_article(client, tokens_a)
    response = client.get(f"/v1/kb/articles/{created['id']}", headers=_headers(tokens_b))
    assert response.status_code == 404


def test_update_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    response = client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "Título actualizado", "change_note": "Corrección ortográfica"},
        headers=_headers(tokens),
    )
    assert response.status_code == 200
    article = response.json()
    assert article["title"] == "Título actualizado"
    assert article["current_version"] == 2


def test_update_article_creates_version(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "V2"},
        headers=_headers(tokens),
    )
    client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "V3"},
        headers=_headers(tokens),
    )
    response = client.get(f"/v1/kb/articles/{created['id']}/versions", headers=_headers(tokens))
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 3
    assert versions[0]["version"] == 3
    assert versions[1]["version"] == 2
    assert versions[2]["version"] == 1


def test_update_article_from_other_tenant_is_404(client: TestClient) -> None:
    tokens_a = register_login(client, "sup-a@example.com", "supervisor", "ten-a")
    tokens_b = register_login(client, "sup-b@example.com", "supervisor", "ten-b")
    created = _create_article(client, tokens_a)
    response = client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "Hack"},
        headers=_headers(tokens_b),
    )
    assert response.status_code == 404


def test_publish_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    response = client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    assert response.status_code == 200
    article = response.json()
    assert article["status"] == "published"
    assert article["published_at"] is not None


def test_publish_article_requires_permission(client: TestClient) -> None:
    tokens_sup = register_login(client, "sup@example.com", "supervisor", "ten-a")
    tokens_agent = register_login(client, "agent@example.com", "agent", "ten-a")
    created = _create_article(client, tokens_sup)
    response = client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens_agent))
    assert response.status_code == 403


def test_publish_from_published_is_422(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    response = client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    assert response.status_code == 422


def test_archive_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    response = client.post(f"/v1/kb/articles/{created['id']}/archive", headers=_headers(tokens))
    assert response.status_code == 200
    article = response.json()
    assert article["status"] == "archived"


def test_archive_from_draft_is_422(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    response = client.post(f"/v1/kb/articles/{created['id']}/archive", headers=_headers(tokens))
    assert response.status_code == 422


def test_restore_article(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    client.post(f"/v1/kb/articles/{created['id']}/archive", headers=_headers(tokens))
    response = client.post(f"/v1/kb/articles/{created['id']}/restore", headers=_headers(tokens))
    assert response.status_code == 200
    article = response.json()
    assert article["status"] == "draft"
    assert article["published_at"] is None


def test_restore_from_draft_is_422(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    response = client.post(f"/v1/kb/articles/{created['id']}/restore", headers=_headers(tokens))
    assert response.status_code == 422


def test_list_versions(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "V2", "change_note": "Segunda versión"},
        headers=_headers(tokens),
    )
    response = client.get(f"/v1/kb/articles/{created['id']}/versions", headers=_headers(tokens))
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_note"] == "Segunda versión"
    assert versions[1]["version"] == 1


def test_kb_operations_are_audited(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-a")
    created = _create_article(client, tokens)
    client.patch(
        f"/v1/kb/articles/{created['id']}",
        json={"title": "Actualizado"},
        headers=_headers(tokens),
    )
    client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens))
    client.post(f"/v1/kb/articles/{created['id']}/archive", headers=_headers(tokens))
    client.post(f"/v1/kb/articles/{created['id']}/restore", headers=_headers(tokens))

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(AuditEvent.tenant_id == "ten-a").all()
    actions = {e.action for e in events}
    assert "kb.article_created" in actions
    assert "kb.article_updated" in actions
    assert "kb.article_published" in actions
    assert "kb.article_archived" in actions
    assert "kb.article_restored" in actions
    for e in events:
        if e.action.startswith("kb."):
            assert e.trace_id
            assert e.detail["article_id"] == created["id"]


def test_agent_can_read_published_articles(client: TestClient) -> None:
    tokens_sup = register_login(client, "sup@example.com", "supervisor", "ten-a")
    tokens_agent = register_login(client, "agent@example.com", "agent", "ten-a")
    created = _create_article(client, tokens_sup)
    client.post(f"/v1/kb/articles/{created['id']}/publish", headers=_headers(tokens_sup))
    response = client.get(f"/v1/kb/articles/{created['id']}", headers=_headers(tokens_agent))
    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_agent_cannot_create_articles(client: TestClient) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten-a")
    response = client.post(
        "/v1/kb/articles",
        json={"title": "Test", "body": "Body"},
        headers=_headers(tokens),
    )
    assert response.status_code == 403


# === Categorías de base de conocimiento ===


def test_list_categories_seeds_defaults(client: TestClient) -> None:
    tokens = register_login(client, "sup-cat@example.com", "supervisor", "ten-a")
    resp = client.get("/v1/kb/categories", headers=_headers(tokens))
    assert resp.status_code == 200
    data = resp.json()
    # Se sembraron las categorías por defecto del tenant
    assert len(data) >= 1
    assert all("id" in c and "name" in c for c in data)


def test_create_category(client: TestClient) -> None:
    tokens = register_login(client, "sup-cat2@example.com", "supervisor", "ten-a")
    resp = client.post(
        "/v1/kb/categories",
        json={"name": "Instalaciones"},
        headers=_headers(tokens),
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Instalaciones"

    # Duplicado → 409
    dup = client.post(
        "/v1/kb/categories",
        json={"name": "Instalaciones"},
        headers=_headers(tokens),
    )
    assert dup.status_code == 409


def test_delete_category(client: TestClient) -> None:
    tokens = register_login(client, "sup-cat3@example.com", "supervisor", "ten-a")
    created = client.post(
        "/v1/kb/categories",
        json={"name": "Temporal"},
        headers=_headers(tokens),
    ).json()
    resp = client.delete(f"/v1/kb/categories/{created['id']}", headers=_headers(tokens))
    assert resp.status_code == 204

    missing = client.delete("/v1/kb/categories/999999", headers=_headers(tokens))
    assert missing.status_code == 404


def test_category_requires_edit_permission(client: TestClient) -> None:
    # agent solo puede leer (kb:read), no crear
    tokens = register_login(client, "agent-cat@example.com", "agent", "ten-a")
    resp = client.post("/v1/kb/categories", json={"name": "X"}, headers=_headers(tokens))
    assert resp.status_code == 403
