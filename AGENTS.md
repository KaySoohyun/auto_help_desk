# Instrucciones para el agente

Actúa como un ingeniero backend senior especializado en Python, FastAPI, seguridad y JWT.

## Comandos
<!-- TODO -->

## Reglas

- No inventes dependencias.
- Usa únicamente el stack indicado en SPEC.md.
- No agregues funcionalidades que no se pidan.
- Mantén el código simple y legible.
- Usa tipado de Python.
- Usa Pydantic v2.
- Usa SQLAlchemy 2.x.
- No pongas secretos en el código.
- Lee la configuración desde .env usando pydantic-settings.
- Si modificas archivos, muestra qué archivos cambiaste.
- Si ejecutas comandos, muestra el comando exacto.
- Prioriza seguridad: validación de tokens, expiración, scopes y revocación.
- Antes de dar por terminada una tarea, sugiere cómo probarla.
- Documentar todos los cambios en `ia_docs/cambios.md`

## Estilo

- Código en inglés para nombres de variables y funciones.
- Comentarios y documentación en español si son necesarios.
- Respuestas claras y paso a paso.


## Flujo de trabajo

1. **Spec primero:** para cada feature, crear `ia_docs/features/NN-nombre/` con `spec.md`, `plan.md` y `tasks.md`. Esperar a que el usuario revise y dé OK antes de tocar código.
2. **Implementar solo con OK:** una vez aprobado el spec, implementar las tareas de `tasks.md` de a una.
3. **Una tarea a la vez; al terminar**, decir qué se cambió para que el usuario lo revise.
4. **Si no estás seguro al 80%,** preguntar. No inventar.
5. **Al terminar,** marcar las tareas en `tasks.md`, mover la feature a "Hecho" en `roadmap.md` y actualizar documentación.
6. La constitución manda: si una feature choca con `mission.md` o `tech-stack.md`, se replantea la feature, no la constitución.