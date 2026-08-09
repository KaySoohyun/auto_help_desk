# Cambios

_Registro de cambios del proyecto. Formato: fecha · descripción · rama._

## 2026-08-08

- Creación de la constitución del proyecto (`ia_docs/constitution/`): misión, roadmap y tech-stack, derivados de `spec.md` y `plan-ejecucion.md`. — `main`
- Commit inicial del repo con spec, constitución y plan de ejecución. — `main`
- Creación de ramas `develop` (integración) y `feature/fase-1` (trabajo de Fase 1).

### Fase 1 · Descubrimiento y diseño de arquitectura — rama `feature/fase-1`

- Feature 001 creada en `ia_docs/features/001-fase-1-descubrimiento/`.
- Creados los entregables de arquitectura en `ia_docs/architecture/`:
  - `00-indice.md` — índice y trazabilidad de entregables.
  - `00-casos-de-uso-roles-flujos.md` — catálogo de CU-01..CU-05, roles y flujos de tickets.
  - `01-matriz-requisitos.md` — matriz FR/RD/RS/RA/RNF/RG trazable al espec.
  - `02-arquitectura-multi-tenant.md` — diagrama y componentes cloud multi-tenant.
  - `03-modelo-datos-pii.md` — modelo de datos y diccionario con clasificación de PII.
  - `04-threat-model-seguridad.md` — amenazas y controles (JWT/OAuth, tenant, auditoría).
  - `05-politica-pii-retencion.md` — política de redacción, retención y minimización.
  - `06-estrategia-ia-guardrails.md` — prompts, grounding, guardrails y métricas.
  - `07-backlog-priorizado.md` — backlog derivado del plan de ejecución.
  - `ADR/ADR-000..005` — decisiones de arquitectura (aislamiento, orquestador LLM, modelo de datos, redacción PII, autenticación JWT).
- Actualizado `constitution/roadmap.md`: Fase 1 marcada como Hecho; siguiente es Fase 2.
- Merge de `feature/fase-1` en `develop` (commit `2bf4957`).

### Fase 2 · Fundamentos de Plataforma, Identidad y Seguridad — rama `feature/fase-2`

- AGENTS.md actualizado: nueva regla "No mergear a main/master sin pedir permiso".
- Feature 002 (Autenticación JWT/OAuth) creada en `ia_docs/features/002-autenticacion-jwt/`.
- Código base del backend FastAPI:
  - `app/core/config.py` — Settings vía pydantic-settings (clave secreta validada, mín. 32 chars).
  - `app/core/security.py` — hash argon2 (passlib) y JWT HS256 (PyJWT) con claims mínimos y errores diferenciados (expirado vs inválido).
  - `app/database.py` — engine, sesión y Base SQLAlchemy 2.x.
  - `app/models/user.py` — modelo `User` (email único, password_hash, role, tenant_id, active).
  - `app/models/token.py` — modelo `RefreshToken` (jti, expiración, revocación).
  - `app/schemas/auth.py` — schemas Pydantic v2 (register, login, refresh, logout, user, token).
  - `app/api/routes_auth.py` — endpoints `/auth/register|login|refresh|logout|me`.
  - `app/core/deps.py` — dependencia `get_current_user` (valida JWT y resuelve usuario).
  - `app/main.py` — app FastAPI con routers y `/health`.
- Tests en `tests/`: 11 pasados (register, login, refresh con rotación, logout/revocación, claims, 401 diferenciado).
- `.env.example` y `.env` actualizados con clave secreta larga.

### Fase 2 · Autorización por tenant y RBAC — rama `feature/003-rbac-tenant`

- Feature 003 creada en `ia_docs/features/003-rbac-tenant/`.
- `app/core/permissions.py` — catálogo de permisos por rol (spec §10.3) y dependencias `require_permissions` / `require_roles` (403 sin permiso).
- `app/core/deps.py` — nueva dependencia `get_tenant_id` (lee tenant_id del token, nunca del cliente).
- `app/repositories/base.py` — `TenantScopedRepository` (filtro por tenant obligatorio, ADR-001).
- `app/api/routes_admin.py` — endpoint de ejemplo `/admin/users` (RBAC + filtro por tenant).
- `app/main.py` — router admin registrado.
- Tests: `tests/test_permissions.py` + `tests/test_tenant_isolation.py` (aislamiento multi-tenant).
- Suite completa: 20 tests pasados (incluye regresión de feature 002).

### Fase 2 · Cifrado, secretos y protección de datos — rama `feature/004-cifrado-secretos`

- Feature 004 creada en `ia_docs/features/004-cifrado-secretos/`.
- `app/core/crypto.py` — cifrado AES-GCM de campos con clave derivada por HKDF desde `SECRET_KEY`; formato versionado `cipher:<v>:<salt>:<nonce>:<ct>:<tag>` con detección de manipulación.
- `app/core/config.py` — propiedad `encryption_key` (derivada de `SECRET_KEY`, nunca persistida).
- `ia_docs/architecture/04-threat-model-seguridad.md` — sección 6: cifrado en reposo/tránsito y plan de gestión de secretos (Vault).
- Tests: `tests/test_crypto.py` (round-trip, unicode, tamper nonce/ct, clave incorrecta, versión, formato, interop GCM).
- Suite completa: 31 tests pasados (incluye regresión de features 002-003).

### Fase 2 · Auditoría, logging y trazabilidad — rama `feature/005-auditoria`

- Feature 005 creada en `ia_docs/features/005-auditoria/`.
- `app/models/audit.py` — modelo `AuditEvent` append-only con campos mínimos del spec §11.2 (timestamp UTC, tenant, user, acción, trace_id, resultado, confianza, detail sin PII).
- `app/services/audit.py` — `AuditService` con `log(...)` (solo insert; sin update/delete).
- `app/core/deps.py` — dependencia `get_trace_id` (uuid por request).
- `app/api/routes_auth.py` — eventos auditados: login ok/fallido, refresh ok/fallido, logout, register, acceso a `/auth/me`.
- `app/api/routes_audit.py` — `GET /audit/events` protegido (`VIEW_AUDIT`), filtrado por tenant y paginado.
- `app/schemas/audit.py` — schema de salida `AuditEventOut`.
- Tests: `tests/test_audit.py` (auditoría de auth, sin PII, aislamiento por tenant, permisos, append-only).
- Suite completa: 39 tests pasados (incluye regresión de features 002-004).
- Commit `14011a1` en `feature/005-auditoria`; merge a `develop` (commit `8d27183`).
- Commit `14011a1` en `feature/005-auditoria`; merge a `develop` (commit `8d27183`).

### Fase 3 · API core de tickets — rama `feature/006-tickets`

- Feature 006 creada en `ia_docs/features/006-tickets/`.
- `app/models/ticket.py` — modelos `Ticket` (subject/description cifrados, status, category, priority, language, assignee, timestamps) y `TicketMessage` (body cifrado, FK a ticket con ondelete CASCADE).
- `app/schemas/ticket.py` — schemas Pydantic v2 (`TicketCreate`, `TicketUpdate`, `TicketOut`, `TicketListOut`, `TicketMessageIn/Out`) con validación de status/prioridad.
- `app/repositories/tickets.py` — `TicketRepository` (filtro por tenant, cifrado AES-GCM al escribir, descifrado al leer) que devuelve `TicketView`/`MessageView` (dataclass espejo) para no mutar el ORM con texto plano.
- `app/api/routes_tickets.py` — `/v1/tickets`: `POST` (create), `GET /{id}`, `GET` (listado con filtros status/category/priority/assignee/fechas y paginación), `PATCH /{id}`, `POST /{id}/messages`, `GET /{id}/messages`, `POST /{id}/close`. RBAC aplicado; otro tenant → 404.
- Auditoría en escrituras (ticket.created/updated/message/closed) con `trace_id` y `detail.ticket_id`.
- `app/main.py` — router de tickets registrado.
- Tests: `tests/test_tickets.py` (14 tests: CRUD, mensajes, cierre, cifrado en reposo, aislamiento 404, auditoría).
- Suite completa: **53 tests pasados** (incluye regresión de features 002-005).
- Commit `497c5a1` en `feature/006-tickets`; merge a `develop` (commit `e5c723c`).

### Fase 3 · Redacción de PII — rama `feature/007-pii`

- Feature 007 creada en `ia_docs/features/007-pii/`.
- `app/services/pii.py` — `PIIRedactor`: detección no-solapada de tipos PII (email, teléfono, tarjeta con Luhn, DNI/NIE, passport, fecha nacimiento, IP, URL interna) y reemplazo por tokens `[[PII:TIPO:hash8]]` con salt por request; modos `off|detect|redact`; tarjeta con Luhn inválido no se redacta.
- `app/schemas/pii.py` — schemas `PIIRedactRequest`, `PIIRedactResponse`, `PIIReportOut` (sin valores en claro).
- `app/api/routes_pii.py` — `POST /v1/pii/redact` protegido con `REQUEST_AI_SUGGESTION`; audita `pii.redacted` sin texto original.
- `app/main.py` — router de PII registrado.
- Tests: `tests/test_pii.py` (15 tests: detección por tipo, múltiples ocurrencias, tokens sin fuga, modos, Luhn, auditoría sin PII, 401).
- Suite completa: **68 tests pasados** (incluye regresión de features 002-006).
- Commit `717258d` en `feature/007-pii`; merge a `develop` (commit `77fbd89`).

### Fase 3 · Optimización de consultas y rendimiento — rama `feature/008-rendimiento`

- Feature 008 creada en `ia_docs/features/008-rendimiento/`.
- `app/models/ticket.py` — índices compuestos `ix_tickets_tenant_status`, `ix_tickets_tenant_created`, `ix_tickets_tenant_priority`; `description` marcada como columna diferida (`deferred=True`). `TicketMessage`: índice `ix_messages_ticket_created` y `body` diferida.
- `app/models/audit.py` — índice compuesto `ix_audit_tenant_created`.
- `app/repositories/tickets.py` — nueva vista `TicketSummaryView` para listados que NO accede a la columna diferida (evita N+1); `list()` la usa.
- `app/schemas/ticket.py` — `TicketSummaryOut` (sin `description`); `TicketListOut.items` lo usa.
- `app/api/routes_tickets.py` — el listado devuelve el resumen; el detalle sigue con `description`.
- Tests: `tests/test_schema.py` (8 tests: índices en metadata y recreados, deferred de `description`/`body`, listado sin exposición de PII, detalle intacto, sin N+1).
- `tests/test_tickets.py` — ajustado el test de cifrado en reposo para leer dentro de la sesión (compatibilidad con deferred).
- Suite completa: **76 tests pasados** (incluye regresión de features 002-007).

### Fase 3 · Observabilidad del backend — rama `feature/009-observabilidad`

- Feature 009 creada en `ia_docs/features/009-observabilidad/`.
- `app/core/metrics.py` — `MetricsRegistry` en memoria (counter, gauge, histograma con buckets Prometheus) sin dependencias externas; serialización a formato de texto Prometheus (`render_prometheus()`); instancia global `metrics` con `reset()` para tests.
- `app/core/logging.py` — logger de aplicación con filtro de `trace_id` (ContextVar `trace_id_var`), idempotente; sin PII.
- `app/core/observability.py` — `MetricsMiddleware` (BaseHTTPMiddleware): `http_requests_total{method,route,status}`, `http_request_duration_seconds` (histograma), `http_errors_total{status}` (≥400), `http_exceptions_total`; header `X-Request-ID` con el `trace_id`.
- `app/api/routes_metrics.py` — `GET /v1/metrics` (text/plain, formato Prometheus) protegido con `VIEW_AUDIT` (permiso existente en el catálogo RBAC; no se añadió `VIEW_METRICS`).
- `app/api/routes_tickets.py` — métricas de negocio: `tickets_created_total` y `tickets_closed_total` con label `tenant_id`.
- `app/main.py` — middleware y router de métricas registrados.
- Tests: `tests/test_metrics.py` (9 tests: 401/403/200, contadores/histogramas con requests reales, errores 404, métricas de negocio create/close, no-PII, formato Prometheus, reset).
- Suite completa: **85 tests pasados** (incluye regresión de features 002-008).

### Fase 4 · Orquestador LLM y conectores de IA — rama `feature/010-orquestador-llm`

- Feature 010 creada en `ia_docs/features/010-orquestador-llm/`.
- `app/services/llm.py` — conectores: `LLMUsage`, `LLMResponse`, `LLMUnavailableError` (fallback seguro) y `LLMRateLimitExceeded`; `HTTPLLMProvider` (httpx, OpenAI Chat Completions, timeout) y `MockLLMProvider` (determinista, dev/tests sin red); fábrica `get_llm_provider` según env.
- `app/core/config.py` — settings LLM (`llm_provider`, `llm_base_url`, `llm_api_key` SecretStr, model, timeout, retries, backoff, max_tokens, rate limit por ventana).
- `app/core/rate_limit.py` — `RateLimitStore` en memoria (ventana deslizante, thread-safe; sin Redis en el stack).
- `app/services/llm_orchestrator.py` — `LLMOrchestrator.complete()`: rate limit `tenant_id:user_id`, reintentos con backoff ante timeout/connect/5xx, métricas (`llm_calls_total{task,status}`, `llm_latency_seconds`, `llm_tokens_total`) reutilizando 009, y auditoría `llm.call` (sin prompts ni respuestas).
- `app/api/routes_ai.py` — `POST /v1/ai/ping` (REQUEST_AI_SUGGESTION; 429 por rate limit, 503 si LLM caído) y `GET /v1/ai/info` (VIEW_AUDIT, config sin secretos).
- `app/schemas/llm.py` — `LLMPingInfo`.
- `app/main.py` — router de IA registrado.
- Tests: `tests/test_llm.py` (13 tests: mock determinista, rate limit, retry→éxito, unavailable tras reintentos, auditoría, ping 401/200, info 401/403/200, ping auditado en DB).
- Suite completa: **98 tests pasados** (incluye regresión de features 002-009).

### Fase 4 · Clasificación automática de tickets — rama `feature/011-clasificacion`

- Feature 011 creada en `ia_docs/features/011-clasificacion/`.
- `app/models/ai_suggestion.py` — modelo `AISuggestion` (`ai_suggestions`): tenant_id, ticket_id (FK CASCADE), type (`classification|summary|reply`), output JSON (sin PII), confidence, model, prompt_version, state (`draft|accepted|rejected`), timestamps; índice compuesto `(tenant_id, ticket_id)`. Base para features 012/013 y feedback 015.
- `app/core/config.py` — `ai_confidence_threshold` (0.6), catálogos `ai_classify_categories` y `ai_classify_intents`.
- `app/prompts/classification.py` — prompt versionado `1.0.0` con separación instrucciones/datos (guardrail §12.1) y builders `build_classify_system`/`build_classify_user_prompt`.
- `app/services/classifier.py` — `TicketClassifier.classify()`: redacta PII del contexto (asunto/descripción/historial con `PiiRedactor`), invoca orquestador (tarea `classify`), valida JSON estructurado (`ClassificationError` como fallback seguro), persiste `AISuggestion` draft, audita `ai.classified` sin PII y registra `ai_classifications_total`.
- `app/schemas/ai.py` — `ClassificationOut` (contrato §15.1 + suggestionId + traceId).
- `app/api/routes_ai.py` — `POST /v1/ai/tickets/{ticket_id}/classify` con `REQUEST_AI_SUGGESTION`; 404 otro tenant, 429 rate limit, 503 LLM caído, 422 JSON inválido.
- Tests: `tests/test_classify.py` (8 tests: éxito con mock, baja confianza→warnings, otro tenant→404, 401, 503, 422, persistencia sin PII, auditoría+métricas; inyección del proveedor vía monkeypatch).
- Suite completa: **106 tests pasados** (incluye regresión de features 002-010).

### Fase 4 · Resumen automático de tickets — rama `feature/012-resumen`

- Feature 012 creada en `ia_docs/features/012-resumen/`.
- `app/prompts/summary.py` — prompt versionado `1.0.0` con separación instrucciones/datos (guardrail §12.1) y builders `build_summary_system`/`build_summary_user_prompt`.
- `app/services/summarizer.py` — `TicketSummarizer.summarize()`: contexto redactado de PII (asunto/descripción/historial), orquestador (tarea `summary`), validación JSON (`SummaryError` como fallback), persistencia `AISuggestion(type='summary')` draft, auditoría `ai.summarized` sin PII y métrica `ai_summaries_total`.
- `app/schemas/ai.py` — `SummaryOut` (contrato §15.2 + suggestionId + traceId).
- `app/api/routes_ai.py` — `POST /v1/ai/tickets/{ticket_id}/summary` con `REQUEST_AI_SUGGESTION`; 404 otro tenant, 429, 503, 422.
- Tests: `tests/test_summary.py` (8 tests: éxito con mock, baja confianza→warnings, otro tenant→404, 401, 503, 422, persistencia sin PII, auditoría+métricas).
- Suite completa: **114 tests pasados** (incluye regresión de features 002-011).

### Fase 4 · Sugerencia de respuesta editable — rama `feature/013-sugerencia-respuesta`

- Feature 013 creada en `ia_docs/features/013-sugerencia-respuesta/`.
- `app/prompts/reply.py` — prompt versionado `1.0.0` con separación instrucciones/datos (guardrail §12.1) y reglas de grounding (FR-08): basar solo en el contexto del ticket, no inventar precios/políticas/plazos, declarar fuentes y `policyFlags`.
- `app/services/reply_suggester.py` — `TicketReplySuggester.suggest_reply()`: contexto redactado de PII (asunto/descripción/historial con `PiiRedactor`), orquestador (tarea `reply`), validación JSON (`ReplyError` como fallback seguro), persistencia `AISuggestion(type='reply')` draft, auditoría `ai.replied` sin PII y métrica `ai_replies_total`.
- `app/schemas/ai.py` — `SuggestedReplyOut` (spec §15.3 + suggestionId + traceId) y `SuggestedReplyRequest` (tone/language opcionales).
- `app/api/routes_ai.py` — `POST /v1/ai/tickets/{ticket_id}/suggested-reply` con `REQUEST_AI_SUGGESTION`; 404 otro tenant, 429 rate limit, 503 LLM caído, 422 JSON inválido.
- Tests: `tests/test_reply.py` (9 tests: éxito con mock, tone/language, otro tenant→404, 401, 503, 422, baja confianza→warnings, persistencia sin PII, auditoría+métricas).
- Suite completa: **123 tests pasados** (incluye regresión de features 002-012).

### Fase 4 · Guardrails de IA — rama `feature/014-guardrails-ia`

- Feature 014 creada en `ia_docs/features/014-guardrails-ia/`.
- `app/services/guardrails.py` — `Guardrails` con `check_output()` (filtra salida del LLM: PII CRÍTICA no tokenizada vía `PiiRedactor.detect` = eco de PII T3, y contenido prohibido como jailbreak/cambio de rol/exfiltración; §12.3) y `check_input()` (patrones de prompt injection en el contexto del ticket, informativo sin bloquear; §12.1). `OutputBlockedError` y `GuardrailReport`.
- `app/core/config.py` — settings `guardrails_enabled`, `guardrail_prohibited_patterns` y `guardrail_injection_patterns` (regex conservadoras).
- `app/services/llm_orchestrator.py` — `complete()` aplica `check_input` (alerta auditada `llm.call` status `alert`, no bloquea) y `check_output` (si bloquea → métrica `ai_guardrail_blocks_total{reason,task}`, auditoría `llm.call` status `blocked` sin contenido, excepción `OutputBlockedError`); `_audit_call` ahora registra `result=status` (success/failure/blocked/alert).
- `app/api/routes_ai.py` — `OutputBlockedError` mapeado a 422 "Contenido bloqueado por política de seguridad" (spec §13.4) en classify/summary/suggested-reply/ping.
- Tests: `tests/test_guardrails.py` (11 tests: unitarios check_output/check_input, bloqueo por PII/jailbreak en salida, salida limpia pasa, auditoría+métricas del bloqueo, alerta de entrada auditada sin bloquear, `guardrails_enabled=False`).
- Suite completa: **134 tests pasados** (incluye regresión de features 002-013).

### Fase 5 · Workspace de agente — rama `feat/15-workspace-agente`

- Feature 015 creada en `ia_docs/features/015-workspace-agente/`.
- `app/models/feedback.py` — modelo `Feedback` (`feedback`): `suggestion_id` FK único a `ai_suggestions` (ondelete CASCADE), `tenant_id`, `action` (accepted|edited|rejected|flagged), `reason`, `edited_content_hash`, timestamps; índice `(tenant_id, suggestion_id)`.
- `app/models/ai_suggestion.py` — `state` ampliado a `draft | accepted | edited | rejected | flagged` (FR-09).
- `app/schemas/ai.py` — `FeedbackIn` (suggestion_id, action Literal, reason?, edited_content_hash?), `FeedbackOut`, `SuggestionOut` (id, type, state, confidence, model, prompt_version, output, created_at).
- `app/services/feedback.py` — `FeedbackService.record()`: valida que la sugerencia sea del tenant (otro tenant → `PermissionError`), upsert de feedback por `suggestion_id`, actualiza `AISuggestion.state`, audita `ai.feedback` (sin reason ni PII) y métrica `ai_feedback_total{action}`.
- `app/api/routes_workspace.py` — router `v1`:
  - `POST /v1/ai/tickets/{ticket_id}/feedback` (`EDIT_RESPONSE`): 404 ticket/sugerencia de otro tenant o inexistente; 422 action inválido.
  - `GET /v1/ai/tickets/{ticket_id}/suggestions` (`READ_TICKETS`): lista sugerencias del ticket del tenant (sin PII).
  - `GET /v1/workspace/my-tickets` (`READ_TICKETS`): bandeja del agente (tickets asignados a él), paginado, `TicketSummaryView`.
- `app/main.py` — router workspace registrado.
- Tests: `tests/test_workspace.py` (10 tests: feedback por acción actualiza state, 404 otro tenant/sugerencia inexistente, 422 action, listado de sugerencias con aislamiento por tenant, bandeja solo mis tickets, auditoría `ai.feedback` y métrica `ai_feedback_total`, 401).
- Suite completa: **144 tests pasados** (incluye regresión de features 002-014).

### Fase 5 · Administración de tenants y auditoría — rama `feat/16-administracion-auditoria`

- Feature 016 creada en `ia_docs/features/016-administracion-auditoria/` (spec §4.3/§4.4, FR-06, §11).
- `app/models/policy.py` — `TenantPolicy` (`tenant_policies`): `tenant_id` único, `ai_enabled`, `tone`, `language`, `allowed_categories` (JSON), `escalation_rules` (JSON), timestamps. `GlobalPolicy` (`global_policies`): fila única (id=1) con overrides de modelo/umbral/guardrails/rate; nulos = default de `.env`. Registrados en `app/models/__init__.py`.
- `app/schemas/admin.py` — `UserCreate`, `UserUpdate` (al menos role o is_active), `TenantPolicyIn/Out`, `GlobalPolicyIn/Out`.
- `app/services/admin.py` — `AdminService`: `create_user` (tenant_admin solo su tenant y sin crear `platform_admin`; platform_admin en cualquier tenant con tenant_id obligatorio; 409 email duplicado; 422 sin tenant_id), `update_user` (404 inexistente/otro tenant, 403 auto-desactivación y rol fuera de alcance), `get/save_tenant_policy` (upsert por tenant, FR-06), `get/save_global_policy` (overrides), y `effective_global_policy` (overrides + defaults). Auditoría `admin.user_created/user_updated/tenant_policy_updated/global_policy_updated` sin PII.
- `app/api/routes_admin.py` — `POST /admin/users` (201), `PATCH /admin/users/{user_id}`, `GET /admin/users` con paginación (limit/offset), `GET/PUT /admin/ai-policy` (`CONFIGURE_TENANT`), `GET/PUT /admin/ai-policies/global` (`MANAGE_AI_POLICIES`).
- `app/api/routes_audit.py` — `GET /audit/events` con filtros opcionales (action, service, user_id, result, date_from, date_to) y evento `audit.view` registrado al leer (§11.1).
- Tests: `tests/test_admin.py` (27 tests: CRUD de usuarios con restricciones de rol/tenant y aislamiento, políticas por tenant con aislamiento, políticas globales solo platform_admin, filtros de auditoría, evento `audit.view`, auditoría de acciones admin sin PII).
- Suite completa: **171 tests pasados** (incluye regresión de features 002-015).

### Fase 6 · Pruebas y red teaming — rama `feat/17-pruebas-red-teaming`

- Feature 017 creada en `ia_docs/features/017-pruebas-red-teaming/` (épicas 6.1-6.4; verificación, sin cambios de código de producto).
- `tests/datasets/` — paquete de datasets de control:
  - `redteam.py` — `INJECTION_PAYLOADS`: 6 payloads de prompt injection cubriendo 5 efectos (rol_change, exfiltration, reveal_prompt, embedded_instructions, jailbreak) con `expected_effect` y `expect_blocked_output`.
  - `classification.py` — `CLASSIFICATION_CASES`: 7 tickets de control (categorías billing/technical/account/general/feedback/urgent/other, intenciones request/incident/question/complaint/other, prioridades low/medium/high/urgent) con salida esperada, y `MockClassifyProvider` (mock determinista por caso, FR-01).
- `tests/test_redteam.py` (épica 6.4, §12.1):
  - Parametrizado `test_injection_payloads_do_not_execute_or_leak`: la inyección en el ticket NO se ejecuta ni filtra PII, y queda auditada como `llm.call` con `result="alert"`.
  - Parametrizado `test_blocked_output_when_llm_cooperates`: si el LLM "coopera" devolviendo el contenido peligroso, los guardrails responden 422 "Contenido bloqueado por política de seguridad".
  - `test_classify_ticket_of_other_tenant_404` / `test_suggestions_of_other_tenant_404`: cruce de tenants en classify/suggestions.
  - `test_rate_limit_exceeded_429`: exceder `llm_rate_max_calls` → 429 y auditoría `result="rate_limited"`.
- `tests/test_ia_evaluation.py` (épica 6.4, §17.2):
  - Parametrizado `test_classification_matches_dataset` sobre `CLASSIFICATION_CASES`: schema válido y categoría/intención/prioridad coherentes (FR-01).
  - `test_low_confidence_warning`: confianza 0.3 → warning de revisión humana (FR-07).
  - `test_reply_without_sources_has_warning` y `test_no_hallucination_when_no_grounding`: respuesta sugerida sin fuentes no alucina y advierte (FR-08).
- `tests/test_performance.py` (épica 6.3, §16): fixture `query_counter` (evento `after_cursor_execute` en el engine).
  - `test_list_does_not_load_deferred_description`: el listado no expone `description` (columna diferida, feature 008).
  - `test_list_emits_bounded_queries`: número fijo/bajo de queries (sin N+1), independiente del tamaño de la página.
  - `test_pagination_respects_limits` y `test_total_count_with_filters`: `limit`/`offset`/`total` correctos con y sin filtros.
- Evaluación IA y red teaming usan mock provider (dataset listo para proveedor real en 018); rendimiento mide patrón de consultas, no latencia absoluta (inestable en CI). Reutiliza `register_login`/`clean_db` del conftest y el patrón de mock de `test_guardrails.py`.
- Suite completa: **200 tests pasados** (baseline `171 passed` + 29 nuevos, sin regresión).
- `roadmap.md`: 017 movida a Hecho; Fase 6 iniciada; siguiente es 018 (CI/CD y operación).

### Fase 6 · CI/CD y operación — rama `feat/18-cicd-operacion`

- Feature 018 creada en `ia_docs/features/018-cicd-operacion/` (épicas 6.5-6.6; despliegue y operación).
- Dependencias reproducibles: `requirements.txt` (11 runtime pinneadas) y `requirements-dev.txt` (`-r requirements.txt` + `pytest==9.1.1`); verificadas con instalación limpia en venv nuevo → suite en verde. Se añadió `psycopg2-binary==2.9.12` para soportar `DATABASE_URL` PostgreSQL en producción (tech-stack lo contempla).
- `app/core/config.py` — `ai_features_enabled: bool = True` (kill-switch de despliegue); `SettingsConfigDict(extra="ignore")` para tolerar variables extra del entorno (p. ej. `DIRECT_URL` que genera Supabase) sin romper el arranque.
- Versionado: `app/__init__.py` → `__version__ = "0.1.0"`; `app/main.py` → `GET /health` devuelve `{"status": "ok", "version": __version__}` (smoke de release).
- Kill-switch (018): dependencia `_ai_features_enabled` en `routes_ai.py` sobre ping/classify/summary/suggested-reply → 503 "IA deshabilitada" + auditoría `ai.disabled` + métrica `ai_disabled_total`; no afecta a tickets ni al resto de la API.
- Rollout por tenant (018): dependencia `_tenant_ai_enabled` que respeta `TenantPolicy.ai_enabled` (default True si no hay fila) → 403 "IA deshabilitada para este tenant" + auditoría `ai.tenant_disabled` + métrica `ai_tenant_disabled_total`. Solo los endpoints de generación IA; listado de sugerencias, feedback e info no se bloquean.
- `app/services/policy.py` — `PolicyResolver.effective_global()`: valores efectivos de `GlobalPolicy` (via `effective_global_policy` de `admin.py`); sin fila → `GlobalPolicy(id=1)` con defaults de `.env` (sin cambio de comportamiento).
- Overrides de `GlobalPolicy` aplicados en runtime:
  - `LLMOrchestrator` acepta `model` y `rate_max_calls` (None = `settings`).
  - `Guardrails` acepta `enabled` (None = `settings.guardrails_enabled`).
  - `TicketClassifier`/`TicketSummarizer`/`TicketReplySuggester` aceptan `confidence_threshold` (antes leían settings internamente).
  - `routes_ai.py` construye el orquestador y los servicios con los valores efectivos del resolver (`_orchestrator(audit, policy)`).
- CI/release:
  - `.github/workflows/ci.yml` — job `test` (instala deps, `check_secrets.sh`, `compileall`, `pytest -q`, smoke `/health` con TestClient) y job `release` (`workflow_dispatch`, `environment: production`, `release.sh --push`, solo rama `develop`); `python-version: "3.12"`.
  - `scripts/check_secrets.sh` — verifica que `.env` no esté versionado y greps de patrones de secretos en archivos versionados.
  - `scripts/release.sh` — valida la suite, lee `__version__`, crea tag `vX.Y.Z`; `--push` opcional. Ambos scripts ejecutados OK localmente.
- `tests/conftest.py` — `/tmp/opencode` se crea con `mkdir(parents=True, exist_ok=True)` (robusto en CI con HOME limpio).
- `tests/test_deploy.py` — 16 tests: `/health` con `version`; kill-switch 503 en los 4 endpoints IA (auditoría `ai.disabled` + métrica, restauración al volver a `True`); rollout por tenant 403 (auditoría `ai.tenant_disabled` + métrica, `/v1/ai/info` no bloqueado, default sin fila = habilitado); overrides de `GlobalPolicy` (resolver honra overrides y defaults, `llm_model` llega al ping, `llm_rate_max_calls=1` → 429, `Guardrails(enabled=False)` vence a `settings`).
- Operación: `ia_docs/operations/` — `dashboard.md` (inventario de métricas de la 009 + queries PromQL sugeridas por panel), `alerts.md` (9 reglas base: LLM caído/degradado, 5xx, excepciones, guardrails, rate limit, kill-switch, tenant disabled, PII) y `runbooks/{release,rollback,incidents}.md` (LLM caído, prompt injection, fuga de PII, rate limit).
- `AGENTS.md` — comandos dev/test definidos (instalar deps, uvicorn dev, pytest, compileall, check_secrets, release, health).
- Suite completa: **216 tests pasados** (baseline `200 passed` + 16 nuevos, sin regresión).
- `roadmap.md`: 018 movida a Hecho; Fase 6 completada; el roadmap de las fases 1-6 está completo (features 001-018).
- Nota de entorno: el `.env` local apunta a PostgreSQL (Supabase) y quedó fuera de control de versiones; `extra="ignore"` + `psycopg2-binary` permiten arrancar con esa configuración.