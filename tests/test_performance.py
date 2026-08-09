"""Pruebas de patrón de consultas en listados de tickets (spec §16, épica 6.3).

Mide el PATRÓN de consultas (número de queries emitidas), no la latencia
absoluta (inestable en CI): el listado no debe cargar la columna diferida
`description`, no debe emitir N+1 por ticket, y la paginación y el `total` con
filtros deben ser correctos.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.conftest import register_login

from app.database import engine


@pytest.fixture
def query_counter():
    """Cuenta queries SQL emitidas a través del engine (patrón de consultas)."""
    state = {"count": 0}

    def _after(conn, cursor, statement, parameters, context, executemany):
        state["count"] += 1

    event.listen(engine, "after_cursor_execute", _after)
    yield lambda: state["count"]
    event.remove(engine, "after_cursor_execute", _after)


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_ticket(client: TestClient, tokens: dict, *, description: str, status: str = "open") -> dict:
    resp = client.post(
        "/v1/tickets",
        json={
            "subject": "Problema de facturación",
            "description": description,
            "category": "billing",
            "priority": "high",
            "language": "es",
        },
        headers=_headers(tokens),
    )
    assert resp.status_code == 201, resp.text
    ticket = resp.json()
    if status != "open":
        resp = client.patch(
            f"/v1/tickets/{ticket['id']}",
            json={"status": status},
            headers=_headers(tokens),
        )
        assert resp.status_code == 200, resp.text
    return ticket


def test_list_does_not_load_deferred_description(client: TestClient) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten")
    long_desc = "Descripción muy larga que no debe cargarse en el listado. " * 50
    _create_ticket(client, tokens, description=long_desc)

    resp = client.get("/v1/tickets", headers=_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    # TicketSummaryView no expone `description` (columna diferida, feature 008)
    assert "description" not in body["items"][0]


def test_list_emits_bounded_queries(client: TestClient, query_counter) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten")

    for i in range(5):
        _create_ticket(client, tokens, description=f"Ticket {i}")

    before = query_counter()
    client.get("/v1/tickets", headers=_headers(tokens))
    queries_small = query_counter() - before

    for i in range(25):
        _create_ticket(client, tokens, description=f"Ticket extra {i}")

    before = query_counter()
    client.get("/v1/tickets", headers=_headers(tokens))
    queries_large = query_counter() - before

    # Sin N+1: el listado de 30 tickets emite las mismas queries que el de 5
    assert queries_large == queries_small
    assert queries_large <= 8


def test_pagination_respects_limits(client: TestClient) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten")
    for i in range(10):
        _create_ticket(client, tokens, description=f"Ticket {i}")

    resp = client.get("/v1/tickets", params={"limit": 3, "offset": 2}, headers=_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 10
    assert len(body["items"]) == 3
    assert body["limit"] == 3
    assert body["offset"] == 2
    assert "description" not in body["items"][0]


def test_total_count_with_filters(client: TestClient) -> None:
    tokens = register_login(client, "agent@example.com", "agent", "ten")
    for i in range(4):
        _create_ticket(client, tokens, description=f"Abierto {i}", status="open")
    for i in range(3):
        _create_ticket(client, tokens, description=f"Cerrado {i}", status="closed")

    resp = client.get("/v1/tickets", params={"status": "open"}, headers=_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert all(t["status"] == "open" for t in body["items"])
