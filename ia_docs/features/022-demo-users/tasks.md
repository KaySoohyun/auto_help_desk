# Tasks · Seed de usuarios demo

Estado: ☐ pendiente · ☐ en curso · ☑ hecho

- [ ] ☐ Crear `scripts/seed_demo_users.py`:
  - [ ] ☐ Usuarios demo de soporte (agente/supervisor/tenant_admin) con membresías en todos los tenants existentes.
  - [ ] ☐ Cliente demo por tenant (`demo.cliente.<slug>@example.com`) con fila en `customers` y membresía.
  - [ ] ☐ Admin de plataforma demo (sin tenant).
  - [ ] ☐ Tickets demo por tenant (creados vía `TicketRepository` para cifrado), con estados/prioridades/categorías variadas, algunos vinculados al cliente demo y asignados al agente demo; algunos con mensajes.
  - [ ] ☐ Idempotencia (sin duplicar al re-ejecutar).
- [ ] ☐ Ejecutar el script dos veces y verificar que no duplica.
- [ ] ☐ Verificar login con `demo.*@example.com` / `demo-pass-123` (con y sin `tenant_id`) contra FastAPI.
- [ ] ☐ Verificar `GET /v1/me/tickets` del cliente demo y `GET /v1/tenants` del platform_admin demo.
- [ ] ☐ `.venv/bin/python -m pytest -q` en verde (sin regresión).
- [ ] ☐ Documentar en `ia_docs/cambios.md` (credenciales demo y cómo correr el seed).
- [ ] ☐ Mover la feature a "Hecho" en `constitution/roadmap.md`.
