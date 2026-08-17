# Auto Help Desk API

Backend multi-tenant (Python / FastAPI) de un **Agente IA de Soporte**: clasifica automáticamente tickets, genera resúmenes y sugiere respuestas editables para los agentes, con controles estrictos de seguridad, privacidad, auditoría y calidad de IA.

## Descripción

Asiste a los equipos de soporte en la gestión de tickets ayudándolos a responder más rápido y con mayor consistencia. La IA **nunca actúa sola**: toda sugerencia es editable y requiere aprobación humana antes de enviarse al cliente.

### Funcionalidades principales

- **Autenticación JWT/OAuth** — login, refresh rotativo, logout con revocación, validación de tokens (exp, iss, aud, roles) y hash de contraseñas con Argon2.
- **Multi-tenant con RBAC** — aislamiento por tenant (el alcance proviene del JWT, nunca del cliente), roles `platform_admin`, `tenant_admin`, `supervisor`, `agent`, `customer` y registro público en `agent`/`supervisor`/`customer`.
- **API de tickets** — creación, listado con filtros y paginación, detalle, mensajes, cierre, categorías y tags, con cifrado en reposo de campos sensibles.
- **Orquestador LLM** — punto único de llamadas a proveedores compatibles con OpenAI Chat Completions (Gemini, OpenRouter o cualquier gateway HTTP) con timeouts, reintentos con backoff, rate limit y fallback seguro. Incluye proveedor `mock` para desarrollo y tests.
- **Clasificación, resumen y sugerencia de respuesta IA** — pipeline seguro que redacta PII antes de llamar al LLM, valida la salida con schema y persiste `AISuggestion` versionadas (modelo y prompt).
- **Redacción de PII** — motor de detección/redacción (email, teléfono, tarjetas, DNI, fechas, IPs, URLs) con tokens seguros y modos `off`/`detect`/`redact`.
- **Guardrails de IA** — filtro contra prompt injection y contenido prohibido/bailbreak, validación de salida y auditoría de bloqueos.
- **Workspace del agente** — feedback sobre sugerencias (aceptar/editar/rechazar/flaggear), panel de sugerencias y bandeja `my-tickets`.
- **Portal de personas (rol customer)** — registro público que crea perfil de customer y permite al cliente ver/crear sus propios tickets (`/v1/me`).
- **Base de conocimiento (KB)** — categorías y artículos con versionado, publicación/archivado y grounding opcional para la IA.
- **Administración** — gestión de usuarios por tenant, políticas IA por tenant y globales (feature flags conectados al runtime).
- **Auditoría y trazabilidad** — `AuditEvent` append-only de acciones humanas e IA con modelo, versión de prompt, confianza, trace_id y resultado.
- **Observabilidad** — métricas Prometheus en memoria (`GET /v1/metrics`), middleware de latencia/errores con trace_id.
- **CI/CD** — pipeline de GitHub Actions (tests, sintaxis, chequeo de secretos, smoke `/health`) y `scripts/release.sh` para tags `vX.Y.Z`.

## Stack tecnológico

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x |
| Validación | Pydantic v2 / pydantic-settings |
| Base de datos | SQLite (local) / PostgreSQL (producción, ej. Supabase) |
| Autenticación | JWT (PyJWT) + Argon2 (passlib) |
| Cifrado | AES-GCM (`cryptography`) |
| LLM | httpx contra endpoints OpenAI-compatible (sin SDKs) |
| Tests | pytest |

## Estructura del proyecto

```
app/
  api/          # Routers FastAPI (auth, tickets, ia, pii, admin, audit, kb, ...)
  core/         # Config, seguridad, deps (tenant auth), permisos, guardrails, observabilidad
  models/       # Modelos SQLAlchemy (tenant, user, ticket, kb, policy, audit, ...)
  repositories/ # Capa de acceso a datos con filtro por tenant
  schemas/      # Schemas Pydantic v2
  services/     # Lógica de negocio (orquestador LLM, PII, clasificador, resumen, ...)
  prompts/      # Plantillas de prompt versionadas
ia_docs/        # Spec, constitución, ADRs, features, operación y cambios
scripts/        # Seeds, migraciones y release
tests/          # Suite de pruebas (funcionales, seguridad, rendimiento, red teaming)
```

La referencia técnica completa y la constitución del proyecto viven en `ia_docs/`:

- `ia_docs/spec.md` — especificación funcional completa del producto
- `ia_docs/constitution/mission.md`, `tech-stack.md`, `roadmap.md`
- `ia_docs/architecture/` — ADRs, modelo de datos, threat model y estrategia de IA
- `ia_docs/post-code/api.md` — referencia de API para el frontend
- `ia_docs/cambios.md` — registro de todos los cambios

## Requisitos

- Python **3.12** (ver `.python-version`)
- Linux / macOS (los scripts usan bash)

## Instalación

```bash
# 1. Crear el entorno virtual e instalar dependencias
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# 2. Configurar variables de entorno
#    Copia el ejemplo y edítalo (al menos SECRET_KEY y DATABASE_URL)
cp .env.example .env
#    Genera una SECRET_KEY segura si quieres cambiarla:
#    openssl rand -hex 32

# 3. (Opcional) Crear datos de prueba: tenants, customers, tags y usuarios por rol
.venv/bin/python scripts/seed_tenants_customers.py
.venv/bin/python scripts/seed_users.py
```

### Configuración mínima de `.env`

```env
# Clave de firma JWT (mín. 32 chars)
SECRET_KEY=change-me-32-chars-minimo-cambia-me-please

# Base de datos (SQLite por defecto en local; PostgreSQL en producción)
DATABASE_URL=sqlite:///./app.db

# Proveedor LLM: mock (sin red, recomendado para desarrollo) | gemini | openrouter | http
LLM_PROVIDER=mock
```

Ver `.env.example` para todas las opciones (proveedores LLM, expiración de tokens, guardrails, umbrales de confianza, kill-switch `AI_FEATURES_ENABLED`, etc.).

## Ejecutar en local

```bash
.venv/bin/uvicorn app.main:app --reload
```

La app arranca en `http://localhost:8000`.

- **Health check:** `curl -s localhost:8000/health` → `{"status":"ok","version":"0.1.1"}`
- **Docs interactivas (Swagger):** `http://localhost:8000/docs`
- **Redoc:** `http://localhost:8000/redoc`

La base de datos se crea automáticamente al arrancar (las tablas se crean en el evento `startup`), así que no hace falta migraciones manuales para empezar.

### Usuarios de prueba (seed)

| Email | Contraseña | Rol |
| --- | --- | --- |
| `agent@example.com` | `agent-pass-123` | agent |
| `supervisor@example.com` | `supervisor-pass-123` | supervisor |
| `tenant-admin@example.com` | `tenant-admin-pass-123` | tenant_admin |
| `platform-admin@example.com` | `platform-admin-pass-123` | platform_admin |

Estos roles **no** se pueden crear por `/auth/register` (solo `agent`/`supervisor`/`customer`); se crean vía seed.

### Flujo rápido de uso

1. **Login:** `POST /auth/login` con un email/contraseña del seed → devuelve `access_token` y `refresh_token`.
2. **Autenticación:** enviar `Authorization: Bearer <access_token>` en el resto de las llamadas.
3. **Crear un ticket:** `POST /v1/tickets`.
4. **Probar la IA:** `POST /v1/ai/tickets/{id}/classify`, `POST /v1/ai/tickets/{id}/summary` y `POST /v1/ai/tickets/{id}/suggested-reply` (con `LLM_PROVIDER=mock` funcionan sin credenciales ni red).

## Tests

```bash
.venv/bin/python -m pytest -q
```

La suite cubre auth, tickets, multi-tenancy, RBAC, PII, cifrado, guardrails, red teaming de prompt injection, rendimiento, evaluación de IA, portales y despliegue.

## Otros comandos útiles

| Comando | Descripción |
| --- | --- |
| `.venv/bin/python -m compileall -q app tests scripts` | Chequeo de sintaxis |
| `bash scripts/check_secrets.sh` | Chequeo de secretos en archivos versionados |
| `bash scripts/release.sh [--push]` | Release: crea tag `vX.Y.Z` |
| `.venv/bin/python scripts/seed_tenants_customers.py` | Seed de tenants/customers/tags |
| `.venv/bin/python scripts/seed_users.py` | Seed de usuarios por rol |

## Referencia de API

Una referencia completa de endpoints, schemas y errores de **Auto Help Desk API** está en `ia_docs/post-code/api.md`. Resumen de rutas:

| Grupo | Prefijo | Endpoints principales |
| --- | --- | --- |
| Auth | `/auth` | register, login, refresh, logout, me, switch-tenant, tenants, clear-tenant |
| Tickets | `/v1/tickets` | CRUD, mensajes, cierre, tags, categorías |
| IA | `/v1/ai` | ping, info, classify, summary, suggested-reply, analyze |
| Workspace | `/v1/workspace` | my-tickets, feedback, suggestions |
| PII | `/v1/pii` | redact |
| Admin | `/admin` | users, ai-policy, ai-policies/global |
| Auditoría | `/audit` | events |
| Métricas | `/v1/metrics` | formato Prometheus |
| KB | `/v1/kb` | categorías y artículos con versionado |
| Customers | `/v1/customers` | listado por tenant |
| Portal customer | `/v1/me` | perfil y "mis tickets" |
| Tenants | `/v1/tenants` | público y detalle |

## Despliegue

- **CI/CD:** GitHub Actions (`push` a `main`/`develop` y PRs) corre tests, `compileall`, chequeo de secretos y smoke de `/health`.
- **Release:** `workflow_dispatch` en `develop` con aprobación manual del entorno `production` ejecuta `scripts/release.sh --push` (tag `vX.Y.Z`).
- **Producción:** FastAPI Cloud / Supabase (ver `.fastapicloud/`). La app maneja URLs de transacción de Supabase (limpiando opciones DSN no soportadas por psycopg2 en `app/database.py`).

## Seguridad

- Los tokens JWT se validan en cada request (exp, iss, aud); el tenant proviene de los claims, nunca de inputs del cliente.
- Cifrado AES-GCM (con formato versionado y anti-tamper) para campos sensibles.
- La PII se redacta antes de cualquier llamada al LLM; los prompts no se guardan en auditoría.
- Ninguna respuesta IA se envía automáticamente al cliente (aprobación humana obligatoria).
- Secrets siempre desde `.env` (pydantic-settings) y nunca en el código o logs.

## Documentación de operaciones

- `ia_docs/operations/dashboard.md`, `alerts.md` y `runbooks/` (release, rollback, incidentes).