import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_login

from app.core.metrics import metrics


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    metrics.reset()
    yield
    metrics.reset()


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _register(client: TestClient) -> dict:
    return register_login(client, "agent@example.com", "agent", "ten")


def _metrics_user(client: TestClient) -> dict:
    return register_login(client, "sup@example.com", "supervisor", "ten")


def _new_metrics(client: TestClient, tokens: dict) -> str:
    resp = client.get("/v1/metrics", headers=_headers(tokens))
    assert resp.status_code == 200, resp.text
    return resp.text


def _create(client: TestClient, tokens: dict, *, subject: str = "Problema", body: str = "Descripción") -> dict:
    resp = client.post(
        "/v1/tickets",
        json={"subject": subject, "description": body},
        headers=_headers(tokens),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_metrics_requires_token(client: TestClient) -> None:
    assert client.get("/v1/metrics").status_code == 401


def test_metrics_requires_view_audit_permission(client: TestClient) -> None:
    tokens = register_login(client, "agent-low@example.com", "agent", "ten-m")
    assert client.get("/v1/metrics", headers=_headers(tokens)).status_code == 403


def test_metrics_ok_for_supervisor(client: TestClient) -> None:
    tokens = register_login(client, "sup@example.com", "supervisor", "ten-m")
    resp = client.get("/v1/metrics", headers=_headers(tokens))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "# TYPE" in resp.text


def test_http_counters_record_real_requests(client: TestClient) -> None:
    tokens = _register(client)
    viewer = _metrics_user(client)
    _create(client, tokens)
    client.get("/v1/tickets", headers=_headers(tokens))
    client.get("/v1/no-existe", headers=_headers(tokens))
    text = _new_metrics(client, viewer)

    assert "http_requests_total" in text
    assert "http_request_duration_seconds_count" in text
    assert "http_request_duration_seconds_bucket" in text
    assert "http_errors_total" in text
    assert "tickets_created_total" in text
    assert 'tenant_id="ten"' in text


def test_histogram_count_and_sum_present(client: TestClient) -> None:
    tokens = _register(client)
    viewer = _metrics_user(client)
    ticket = _create(client, tokens)
    client.get(f"/v1/tickets/{ticket['id']}", headers=_headers(tokens))
    text = _new_metrics(client, viewer)

    assert "http_request_duration_seconds_count" in text
    assert "http_request_duration_seconds_bucket" in text
    assert "http_request_duration_seconds_sum" in text
    assert 'le="+Inf"' in text


def test_http_errors_increment_on_404(client: TestClient) -> None:
    tokens = _register(client)
    viewer = _metrics_user(client)
    resp = client.get("/v1/no-existe", headers=_headers(tokens))
    assert resp.status_code == 404
    text = _new_metrics(client, viewer)
    assert "http_errors_total" in text
    assert 'status="404"' in text


def test_business_metrics_create_and_close(client: TestClient) -> None:
    tokens = _register(client)
    viewer = _metrics_user(client)
    ticket = _create(client, tokens)
    resp = client.post(f"/v1/tickets/{ticket['id']}/close", headers=_headers(tokens))
    assert resp.status_code == 200
    text = _new_metrics(client, viewer)
    assert "tickets_created_total" in text
    assert "tickets_closed_total" in text
    assert 'tenant_id="ten"' in text


def test_metrics_do_not_leak_pii(client: TestClient) -> None:
    tokens = register_login(client, "pii@example.com", "agent", "ten-m")
    viewer = register_login(client, "pii-sup@example.com", "supervisor", "ten-m")
    _create(client, tokens, subject="Sujeto confidencial", body="Tarjeta 4111 1111 1111 1111")
    text = _new_metrics(client, viewer)

    assert "Sujeto confidencial" not in text
    assert "Tarjeta" not in text
    assert "4111" not in text
    assert "pii@example.com" not in text


def test_prometheus_format(client: TestClient) -> None:
    tokens = _register(client)
    viewer = _metrics_user(client)
    _create(client, tokens)
    text = _new_metrics(client, viewer)
    line_body = [l for l in text.splitlines() if l and not l.startswith("#")]
    assert line_body
    for line in line_body:
        assert " " in line
        assert not line.startswith(" ")
    # cada serie está precedida por su TYPE
    for name in ("http_requests_total", "tickets_created_total"):
        assert f"# TYPE {name}" in text