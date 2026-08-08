from fastapi.testclient import TestClient
from sqlalchemy import inspect
from tests.conftest import register_login

from app.database import engine
from app.models.audit import AuditEvent
from app.models.ticket import Ticket, TicketMessage


def _index_names(table_name: str) -> set[str]:
    inspector = inspect(engine)
    return {ix["name"] for ix in inspector.get_indexes(table_name)}


def test_metadata_declares_composite_indexes() -> None:
    """Los índices compuestos se declaran en la metadata SQLAlchemy."""
    from app.database import Base

    indices: set[str] = set()
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            indices.add(index.name)
    assert "ix_tickets_tenant_status" in indices
    assert "ix_tickets_tenant_created" in indices
    assert "ix_tickets_tenant_priority" in indices
    assert "ix_messages_ticket_created" in indices
    assert "ix_audit_tenant_created" in indices


def test_indexes_exist_in_recreated_schema() -> None:
    indexes = _index_names("tickets")
    assert {"ix_tickets_tenant_status", "ix_tickets_tenant_created", "ix_tickets_tenant_priority"} <= indexes
    assert "ix_messages_ticket_created" in _index_names("ticket_messages")
    assert "ix_audit_tenant_created" in _index_names("audit_events")


def test_description_is_deferred() -> None:
    assert Ticket.__mapper__.column_attrs["description"].deferred is True


def test_message_body_is_deferred() -> None:
    assert TicketMessage.__mapper__.column_attrs["body"].deferred is True


def test_audit_detail_is_not_deferred() -> None:
    assert AuditEvent.__mapper__.column_attrs["detail"].deferred is False


def test_list_does_not_expose_deferred_fields(client: TestClient) -> None:
    tokens = register_login(client, "perf@example.com", "agent", "ten-1")
    client.post(
        "/v1/tickets",
        json={"subject": "Asunto listado", "description": "Descripción pesada y sensible"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    response = client.get(
        "/v1/tickets",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert "description" not in items[0]
    assert items[0]["subject"] == "Asunto listado"


def test_detail_still_returns_description(client: TestClient) -> None:
    tokens = register_login(client, "perf2@example.com", "agent", "ten-1")
    created = client.post(
        "/v1/tickets",
        json={"subject": "Asunto detalle", "description": "Contenido sensible del detalle"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).json()
    response = client.get(
        f"/v1/tickets/{created['id']}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Contenido sensible del detalle"


def test_list_does_not_trigger_per_row_loads() -> None:
    """Listar N tickets no debe emitir N+1 SELECT (el campo diferido no se carga)."""
    from sqlalchemy import event

    from app.database import SessionLocal
    from app.models.ticket import Ticket
    from app.repositories.tickets import TicketRepository

    with SessionLocal() as db:
        for i in range(5):
            db.add(
                Ticket(
                    tenant_id="perf-tenant",
                    subject=f"s{i}",
                    description=f"d{i}",
                    status="open",
                )
            )
        db.commit()

        statements: list[str] = []

        @event.listens_for(engine, "before_cursor_execute")
        def _record(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement.strip())

        try:
            repo = TicketRepository(db, "perf-tenant")
            items, _ = repo.list(limit=10, offset=0)
            assert len(items) == 5
            # listado: 1 SELECT principal + 1 COUNT; sin N+1 por descripción
            selects = [s for s in statements if s.upper().startswith("SELECT")]
            assert len(selects) <= 2
        finally:
            event.remove(engine, "before_cursor_execute", _record)