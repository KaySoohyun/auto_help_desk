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

## Siguiente 🔜

_Lo próximo a abordar: Fase 3 (Backend / Almacenamiento Cloud), una feature en curso a la vez._

9. **009 · Observabilidad del backend** — métricas, trazas y alertas.

8. **008 · Optimización de consultas y rendimiento** — índices, paginación, caché y proyecciones ligeras.

## Fase 3: Backend / Almacenamiento Cloud 💾

9. **009 · Observabilidad del backend** — métricas, trazas y alertas.

## Fase 4: Integración API IA 🤖

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
