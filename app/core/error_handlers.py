"""Handlers globales de error (mensajes de la API en español).

FastAPI/Pydantic generan mensajes de error en inglés por defecto (validación 422,
404, 500, etc.). Estos handlers los traducen al español manteniendo la estructura
de respuesta. Los `HTTPException` que ya lanzan mensajes en español se devuelven
sin cambios.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.error")

# -- Traducción de mensajes de validación de Pydantic -----------------------

_PYDANTIC_MSG_ES: dict[str, str] = {
    "Field required": "Campo requerido",
    "Extra inputs are not permitted": "No se permiten campos adicionales",
    "Input should be a valid integer": "Debe ser un número entero válido",
    "Input should be a valid string": "Debe ser una cadena de texto válida",
    "Input should be a valid boolean": "Debe ser un valor booleano válido",
    "Input should be a valid email": "Debe ser un correo electrónico válido",
    "value is not a valid email address": "No es un correo electrónico válido",
    "Input should be a valid date": "Debe ser una fecha válida",
    "Input should be a valid datetime": "Debe ser una fecha y hora válida",
    "Input should be a valid time": "Debe ser una hora válida",
    "Input should be a valid UUID": "Debe ser un UUID válido",
    "Input should be a valid bytes": "Debe ser una secuencia de bytes válida",
    "Input should be a valid list": "Debe ser una lista válida",
    "Input should be a valid number": "Debe ser un número válido",
    "Input should be a valid float": "Debe ser un número decimal válido",
    "Input should be a valid URL": "Debe ser una URL válida",
    "Input should be a valid dict": "Debe ser un diccionario válido",
    "Input should be a valid dictionary or instance of dict": "Debe ser un diccionario válido",
}

_PYDANTIC_PATTERNS_ES: list[tuple[str, str]] = [
    (r"^String should have at most (\d+) characters$", r"Debe tener como máximo \1 caracteres"),
    (r"^String should have at least (\d+) characters$", r"Debe tener al menos \1 caracteres"),
    (r"^String should match pattern '.+'$", "No cumple el formato esperado"),
    (r"^Input should be less than or equal to (.+)$", r"Debe ser menor o igual que \1"),
    (r"^Input should be greater than or equal to (.+)$", r"Debe ser mayor o igual que \1"),
    (r"^Input should be less than (.+)$", r"Debe ser menor que \1"),
    (r"^Input should be greater than (.+)$", r"Debe ser mayor que \1"),
    (r"^List should have at most (\d+) items after validation, not \d+$", r"La lista no puede tener más de \1 elementos"),
    (r"^List should have at least (\d+) items after validation, not \d+$", r"La lista debe tener al menos \1 elementos"),
    (r"^Value error, ", "Error de valor: "),
    (r"^value is not a valid email address(?:: .+)?$", "No es un correo electrónico válido"),
]


def translate_pydantic_msg(msg: str) -> str:
    """Traduce un `msg` de validación de Pydantic v2 al español."""
    translated = _PYDANTIC_MSG_ES.get(msg, msg)
    if translated != msg:
        return translated
    for pattern, repl in _PYDANTIC_PATTERNS_ES:
        candidate = re.sub(pattern, repl, translated)
        if candidate != translated:
            translated = candidate
            break
    if translated.startswith("Value error, "):
        translated = "Error de valor: " + translated[len("Value error, ") :]
    if translated.startswith("Input should be "):
        translated = "Debe ser " + translated[len("Input should be ") :].replace(" or ", " o ")
    return translated


# -- Traducción de detalles HTTP por defecto de Starlette --------------------

_HTTP_DETAILS_ES: dict[int, str] = {
    400: "Solicitud inválida",
    401: "No autorizado",
    403: "Prohibido",
    404: "No encontrado",
    405: "Método no permitido",
    406: "No aceptable",
    409: "Conflicto",
    410: "Ya no disponible",
    411: "Longitud requerida",
    412: "Precondición fallida",
    413: "Carga demasiado grande",
    415: "Tipo de medio no soportado",
    422: "Entidad no procesable",
    429: "Demasiadas solicitudes",
    500: "Error interno del servidor",
    502: "Puerta de enlace inválida",
    503: "Servicio no disponible",
    504: "Tiempo de espera de la puerta de enlace agotado",
}

_HTTP_DEFAULT_DETAILS: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Payload Too Large",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


def _translate_http_detail(detail: Any, status_code: int) -> Any:
    if (
        isinstance(detail, str)
        and _HTTP_DEFAULT_DETAILS.get(status_code) == detail
        and status_code in _HTTP_DETAILS_ES
    ):
        return _HTTP_DETAILS_ES[status_code]
    return detail


# -- Handlers ----------------------------------------------------------------

async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = jsonable_encoder(exc.errors())
    for err in errors:
        err["msg"] = translate_pydantic_msg(str(err.get("msg", "")))
    return JSONResponse(status_code=422, content={"detail": errors})


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": _translate_http_detail(exc.detail, exc.status_code)},
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en la API", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


def register_error_handlers(app: FastAPI) -> None:
    """Registra los handlers de error en la app FastAPI."""
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
