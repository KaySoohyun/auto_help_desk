import re

from fastapi.testclient import TestClient
from tests.conftest import register_login

from app.database import SessionLocal
from app.models.audit import AuditEvent
from app.services.pii import PiiRedactor

TOKEN_RE = re.compile(r"\[\[PII:[a-z_]+:[0-9a-f]{8}\]\]")


def _types(result) -> dict[str, int]:
    return result.report.types


def test_redact_email() -> None:
    result = PiiRedactor().redact("Contacto: ana@example.com")
    assert "ana@example.com" not in result.text
    assert _types(result)["email"] == 1
    assert "[[PII:email:" in result.text


def test_redact_phone() -> None:
    result = PiiRedactor().redact("Llamar al +34 600 123 456")
    assert "+34 600 123 456" not in result.text
    assert _types(result)["phone"] == 1


def test_redact_card_with_luhn() -> None:
    result = PiiRedactor().redact("Tarjeta 4111 1111 1111 1111")
    assert "4111 1111 1111 1111" not in result.text
    assert _types(result)["card"] == 1
    assert "[[PII:card:" in result.text


def test_redact_id_document() -> None:
    result = PiiRedactor().redact("DNI 12345678Z")
    assert "12345678Z" not in result.text
    assert _types(result)["id_number"] == 1


def test_redact_birth_date() -> None:
    result = PiiRedactor().redact("Nació el 12/05/1990")
    assert "12/05/1990" not in result.text
    assert _types(result)["birth_date"] == 1


def test_redact_ip() -> None:
    result = PiiRedactor().redact("Servidor 192.168.1.10")
    assert "192.168.1.10" not in result.text
    assert _types(result)["ip_address"] == 1


def test_redact_internal_url() -> None:
    result = PiiRedactor().redact("Acceso http://admin.internal/x")
    assert "admin.internal" not in result.text
    assert _types(result)["internal_url"] == 1


def test_multiple_ocurrences_and_types() -> None:
    result = PiiRedactor().redact("a@a.com +34 600 000 000 b@b.com")
    assert "a@a.com" not in result.text
    assert "b@b.com" not in result.text
    assert _types(result)["email"] == 2
    assert _types(result)["phone"] == 1


def test_invalid_luhn_card_not_redacted() -> None:
    result = PiiRedactor().redact("Tarjeta inválida: 1234 5678 9012 3456")
    assert "card" not in _types(result)
    assert "1234 5678 9012 3456" in result.text


def test_token_does_not_leak_original() -> None:
    text = "a@example.com con 4111 1111 1111 1111 y 12345678Z"
    result = PiiRedactor().redact(text)
    for match in TOKEN_RE.finditer(result.text):
        assert "a@example" not in match.group(0)
        assert "4111" not in match.group(0)
        assert "12345678Z" not in match.group(0)


def test_off_mode_returns_text_unchanged() -> None:
    text = "a@a.com y 4111 1111 1111 1111"
    result = PiiRedactor().redact(text, mode="off")
    assert result.text == text
    assert result.report.total == 0


def test_detect_mode_reports_without_replacing() -> None:
    result = PiiRedactor().redact("a@a.com", mode="detect")
    assert result.text == "a@a.com"
    assert _types(result)["email"] == 1


def test_redact_is_consistent_repeatable() -> None:
    text = "a@example.com"
    redactor = PiiRedactor()
    assert redactor.redact(text).text == redactor.redact(text).text


def test_endpoint_redacts_and_audits_without_pii(client: TestClient) -> None:
    tokens = register_login(client, "agent-pii@example.com", "agent", "ten-1")
    text = "Reportar a soporte@example.com con DNI 12345678Z"
    response = client.post(
        "/v1/pii/redact",
        json={"text": text, "mode": "redact"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "soporte@example.com" not in body["text"]
    assert body["report"]["types"]["email"] == 1
    assert body["report"]["types"]["id_number"] == 1
    assert body["report"]["total"] == 2

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(AuditEvent.tenant_id == "ten-1").all()
    redaction_events = [e for e in events if e.action == "pii.redacted"]
    assert len(redaction_events) == 1
    serialized = str(redaction_events[0].__dict__)
    assert "soporte@example.com" not in serialized
    assert "12345678Z" not in serialized
    assert redaction_events[0].detail["total"] == 2


def test_endpoint_requires_auth(client: TestClient) -> None:
    assert client.post("/v1/pii/redact", json={"text": "a@a.com"}).status_code == 401