"""Tests de despliegue y operación (018): kill-switch, rollout por tenant,
overrides de `GlobalPolicy` y health check con versión.
"""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_login

from app import __version__
from app.core.config import settings
from app.core.metrics import metrics
from app.core.rate_limit import rate_limit_store
from app.database import SessionLocal
from app.models.audit import AuditEvent
from app.models.policy import GlobalPolicy, TenantPolicy
from app.services.admin import effective_global_policy
from app.services.guardrails import Guardrails
from app.services.policy import PolicyResolver

AI_ENDPOINTS = [
    ("/v1/ai/ping", {}),
    ("/v1/ai/tickets/1/classify", {}),
    ("/v1/ai/tickets/1/summary", {}),
    ("/v1/ai/tickets/1/suggested-reply", {}),
]


@pytest.fixture(autouse=True)
def reset_state() -> None:
    metrics.reset()
    rate_limit_store.reset()
    yield
    metrics.reset()
    rate_limit_store.reset()


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _insert_global_policy(**fields) -> None:
    with SessionLocal() as db:
        policy = GlobalPolicy(id=1, **fields)
        db.add(policy)
        db.commit()


# --- health check -----------------------------------------------------------


def test_health_includes_version(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


# --- kill-switch global (ai_features_enabled) -------------------------------


@pytest.mark.parametrize("path,body", AI_ENDPOINTS)
def test_kill_switch_blocks_all_ai_endpoints(client: TestClient, monkeypatch, path: str, body: dict) -> None:
    monkeypatch.setattr(settings, "ai_features_enabled", False)
    tokens = register_login(client, f"kill-{path.split('/')[-1].replace('-', '_')}@example.com", "agent", "ten")
    resp = client.post(path, headers=_headers(tokens), json=body)
    assert resp.status_code == 503
    assert resp.json()["detail"] == "IA deshabilitada"


def test_kill_switch_audits_and_metrics(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_features_enabled", False)
    tokens = register_login(client, "kill-audit@example.com", "agent", "ten")
    client.post("/v1/ai/ping", headers=_headers(tokens))
    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(AuditEvent.action == "ai.disabled").all()
    assert len(events) >= 1
    assert events[0].result == "disabled"
    assert events[0].service == "ai"
    rendered = metrics.render_prometheus()
    assert "ai_disabled_total" in rendered


def test_kill_switch_restores_when_enabled(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_features_enabled", False)
    tokens = register_login(client, "kill-restore@example.com", "agent", "ten")
    assert client.post("/v1/ai/ping", headers=_headers(tokens)).status_code == 503
    monkeypatch.setattr(settings, "ai_features_enabled", True)
    resp = client.post("/v1/ai/ping", headers=_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# --- rollout por tenant (TenantPolicy.ai_enabled) ----------------------------


def test_tenant_disabled_blocks_ai(client: TestClient) -> None:
    tokens = register_login(client, "tenant-off@example.com", "agent", "ten-x")
    with SessionLocal() as db:
        db.add(TenantPolicy(tenant_id="ten-x", ai_enabled=False))
        db.commit()
    resp = client.post("/v1/ai/ping", headers=_headers(tokens))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "IA deshabilitada para este tenant"
    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(AuditEvent.action == "ai.tenant_disabled").all()
    assert len(events) >= 1
    assert "ai_tenant_disabled_total" in metrics.render_prometheus()


def test_tenant_disabled_does_not_block_other_endpoints(client: TestClient) -> None:
    tokens = register_login(client, "tenant-sup@example.com", "supervisor", "ten-y")
    with SessionLocal() as db:
        db.add(TenantPolicy(tenant_id="ten-y", ai_enabled=False))
        db.commit()
    resp = client.get("/v1/ai/info", headers=_headers(tokens))
    assert resp.status_code == 200


def test_tenant_without_policy_is_enabled_by_default(client: TestClient) -> None:
    tokens = register_login(client, "tenant-default@example.com", "agent", "ten-z")
    resp = client.post("/v1/ai/ping", headers=_headers(tokens))
    assert resp.status_code == 200


# --- overrides de GlobalPolicy -----------------------------------------------


def test_effective_global_policy_honors_overrides() -> None:
    _insert_global_policy(
        llm_model="custom-model-x",
        ai_confidence_threshold=0.1,
        guardrails_enabled=False,
        llm_rate_max_calls=7,
    )
    with SessionLocal() as db:
        effective = PolicyResolver(db).effective_global()
    assert effective["llm_model"] == "custom-model-x"
    assert effective["ai_confidence_threshold"] == 0.1
    assert effective["guardrails_enabled"] is False
    assert effective["llm_rate_max_calls"] == 7


def test_effective_global_policy_defaults_without_row() -> None:
    with SessionLocal() as db:
        effective = PolicyResolver(db).effective_global()
    assert effective["llm_model"] == settings.llm_model
    assert effective["ai_confidence_threshold"] == settings.ai_confidence_threshold
    assert effective["guardrails_enabled"] == settings.guardrails_enabled
    assert effective["llm_rate_max_calls"] == settings.llm_rate_max_calls


def test_effective_global_policy_defaults_on_null_fields() -> None:
    _insert_global_policy(llm_model=None, ai_confidence_threshold=None, guardrails_enabled=None, llm_rate_max_calls=None)
    with SessionLocal() as db:
        effective = PolicyResolver(db).effective_global()
    assert effective == effective_global_policy(GlobalPolicy(id=1))
    assert effective["llm_model"] == settings.llm_model


def test_llm_model_override_reaches_ping(client: TestClient) -> None:
    _insert_global_policy(llm_model="custom-model-x")
    tokens = register_login(client, "override-model@example.com", "agent", "ten")
    resp = client.post("/v1/ai/ping", headers=_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["model"] == "custom-model-x"


def test_rate_limit_override_applies_429(client: TestClient) -> None:
    _insert_global_policy(llm_rate_max_calls=1)
    tokens = register_login(client, "override-rate@example.com", "agent", "ten")
    assert client.post("/v1/ai/ping", headers=_headers(tokens)).status_code == 200
    assert client.post("/v1/ai/ping", headers=_headers(tokens)).status_code == 429


def test_guardrails_override_disabled_skips_output_filter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "guardrails_enabled", True)
    report = Guardrails(enabled=False).check_output("Contacta al usuario en cliente@example.com")
    assert not report.blocked
