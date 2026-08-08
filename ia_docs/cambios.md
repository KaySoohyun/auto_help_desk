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