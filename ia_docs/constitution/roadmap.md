# Roadmap

_Orden y estado de las features. Es la vista de "qué hay hecho, qué toca ahora y qué viene". Cada entrada apunta a su carpeta en `features/`. Las fases 1-6 referencian `ia_docs/plan-ejecucion.md`._

## Hecho ✅

1. **001 · Fundamentos y arquitectura** — base del repo, configuración `.env`, ADRs y backlog priorizado (Fase 1). Entregables en `ia_docs/architecture/`.
2. **002 · Autenticación JWT/OAuth** — login, refresh rotativo, logout con revocación, validación de tokens (exp, iss, aud, roles) y hash argon2.
3. **003 · Autorización por tenant y RBAC** — catálogo de permisos por rol, `require_roles`/`require_permissions`, repositorio con filtro por tenant (ADR-001) y tests de aislamiento multi-tenant.
4. **004 · Cifrado, secretos y protección de datos** — cifrado AES-GCM de campos (formato versionado, anti-tamper), validación de `SECRET_KEY` y plan de secretos (Vault).
5. **005 · Auditoría, logging y trazabilidad** — modelo `AuditEvent` append-only, `AuditService`, eventos de auth auditados, endpoint `GET /audit/events` protegido y paginado.
6. **006 · API core de tickets** — creación, consulta, listado con filtros/paginación, actualización, mensajes y cierre, con cifrado en reposo de campos sensibles y aislamiento por tenant.
7. **007 · Redacción de PII** — motor de detección/redacción de datos sensibles (email, teléfono, tarjetas, DNIs, fechas, IPs, URLs internas) con tokens seguros, modos off/detect/redact y auditoría sin valores originales.
8. **008 · Optimización de consultas** — índices compuestos (tenant+status/created/priority, ticket+created, audit+created), campos diferidos para PII pesada (listados sin `description`/`body`) y paginación con límites.
9. **009 · Observabilidad del backend** — registro de métricas en memoria (contadores, gauge e histogramas), middleware de latencia/errores/excepciones con `trace_id`, `GET /v1/metrics` en formato texto Prometheus protegido con `VIEW_AUDIT`, y métricas de negocio de tickets por tenant (sin PII). Sin dependencias externas.
10. **010 · Orquestador LLM y conectores de IA** — punto único de llamadas LLM (ADR-002): proveedores HTTP (httpx, OpenAI-compatible) y mock, timeout/reintentos con backoff, rate limit en memoria por tenant+usuario, fallback seguro (`LLMUnavailableError`), métricas de tokens/latencia/errores (feature 009) y auditoría `llm.call` sin prompts. Expone `POST /v1/ai/ping` y `GET /v1/ai/info`.
11. **011 · Clasificación automática de tickets** — servicio `TicketClassifier` sobre el orquestador: contexto redactado de PII, prompt versionado, salida JSON validada (categoría, subcategoría, intención, prioridad, confianza, rationale, warnings), persistencia en `ai_suggestions` (draft) y umbral de confianza con advertencia de revisión humana. `POST /v1/ai/tickets/{id}/classify`.
12. **012 · Resumen automático de tickets** — `TicketSummarizer` con el mismo pipeline seguro: contexto redactado, tarea `summary`, resumen breve y accionable + información faltante, persistencia en `ai_suggestions` (draft) y umbral de confianza. `POST /v1/ai/tickets/{id}/summary`.
13. **013 · Sugerencia de respuesta editable** — `TicketReplySuggester` con el mismo pipeline seguro: contexto redactado, tarea `reply`, borrador editable con grounding y fuentes (FR-08), `policyFlags` para aspectos no verificables, persistencia en `ai_suggestions` (draft) y umbral de confianza. `POST /v1/ai/tickets/{id}/suggested-reply`.
14. **014 · Guardrails de IA** — capa de guardrails en el orquestador (ADR-002): filtro de salida (PII cruda + contenido prohibido/jailbreak) que bloquea y audita `ai_guardrail_blocks_total` con 422 "Contenido bloqueado por política de seguridad", y alerta de prompt injection en entrada (audita sin bloquear).
15. **015 · Workspace de agente** — feedback del agente sobre sugerencias IA (`POST /v1/ai/tickets/{id}/feedback` con accepted/edited/rejected/flagged que actualiza el estado de la `AISuggestion`), panel IA por ticket (`GET /v1/ai/tickets/{id}/suggestions`) y bandeja del agente (`GET /v1/workspace/my-tickets`). Regenerar/escalar reutilizan endpoints existentes.

## Siguiente 🔜

_Lo próximo a abordar: Fase 5 (Experiencia de Agente y Administración), una feature en curso a la vez._

16. **016 · Administración de tenants y auditoría** — usuarios, roles, permisos, políticas IA y vistas de auditoría.

## Fase 3: Backend / Almacenamiento Cloud 💾

_Completada (features 006-009)._

## Fase 4: Integración API IA 🤖

_Completada (features 010-014)._

10. **010 · Orquestador LLM y conectores de IA** — gateway con timeouts, reintentos, fallback y límites de uso.
11. **011 · Clasificación automática de tickets** — categoría, subcategoría, intención y prioridad sugerida con confianza.
12. **012 · Resumen automático de tickets** — problema principal, acciones previas, estado actual e información faltante.
13. **013 · Sugerencia de respuesta editable** — borrador con grounding y fuentes.
14. **014 · Guardrails de IA** — prompt injection, control de alucinaciones, validación de salida y fallback seguro.

## Fase 5: Experiencia de Agente y Administración 🖥️

15. **015 · Workspace de agente** — gestión de tickets, colas y panel de asistencia IA (aceptar/editar/rechazar/escalar).
16. **016 · Administración de tenants y auditoría** — usuarios, roles, permisos, políticas IA y vistas de auditoría.

## Fase 6: Testing / Despliegue 🚀

17. **017 · Pruebas y red teaming** — funcionales, seguridad/privacidad multi-tenancy, rendimiento y evaluación de IA.
18. **018 · CI/CD y operación** — pipelines, rollout por tenants, feature flags, dashboards, runbooks y release a producción.

## Backlog / ideas 💡

_Sin comprometer ni ordenar del todo. Ideas que respetan la constitución._

- **Base de conocimiento por tenant (RAG avanzado)** — artículos aprobados con filtro por idioma y vigencia.
- **Métricas de calidad y uso** — precisión de clasificación, tasas de aceptación/rechazo y evaluación con dataset de control.
- **Detección proactiva de tickets duplicados** — sugerir próximos mejores acciones.
- **Analítica de calidad por agente y por equipo.**
- **Soporte multi-idioma completo.**

> Cada feature nueva se crea como `features/NNN-nombre-feature/` con `spec.md`, `plan.md` y `tasks.md` antes de tocar código.
