"""Traduce los errores de Oracle a respuestas HTTP.

Los triggers y el package lanzan RAISE_APPLICATION_ERROR con mensajes de
negocio (sección 5.2 del informe); la API los entrega tal cual al cliente.
"""
import oracledb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

# código ORA -> estado HTTP
ESTADOS_HTTP = {
    20001: 404,   # TRG_HOJA_VALIDA: el estudiante o la evaluación no existe
    20002: 422,   # TRG_HOJA_VALIDA: estudiante retirado
    20003: 422,   # TRG_HOJA_VALIDA: estudiante de otro curso
    20004: 422,   # TRG_RESPUESTA_VALIDA: alternativa no válida
    20005: 422,   # TRG_RESPUESTA_VALIDA: pregunta de otra evaluación
    20006: 404,   # TRG_RESPUESTA_VALIDA: la hoja o la pregunta no existe
    20010: 409,   # PKG_RESULTADOS: evaluación no procesable
    20020: 423,   # TRG_PREGUNTA_BLOQUEO: proceso nocturno en curso
    1: 409,       # restricción UNIQUE o PRIMARY KEY
    1400: 422,    # NOT NULL
    2290: 422,    # CHECK
    2291: 422,    # clave foránea: no existe la fila padre
    2292: 409,    # clave foránea: la fila tiene dependientes
}


def _error_oracle(exc: Exception) -> oracledb._Error | None:
    original = exc.orig if isinstance(exc, DBAPIError) else exc
    if isinstance(original, oracledb.Error) and original.args:
        return original.args[0]
    return None


def _respuesta(exc: Exception) -> JSONResponse:
    error = _error_oracle(exc)
    if error is None:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    # solo la primera línea: las siguientes son la pila ORA-06512 del PL/SQL
    primera = error.message.splitlines()[0]
    mensaje = primera.split(": ", 1)[1] if ": " in primera else primera
    codigo = error.code or 0
    return JSONResponse(
        status_code=ESTADOS_HTTP.get(codigo, 500),
        content={"detail": mensaje, "codigo_oracle": error.full_code},
    )


def registrar(app: FastAPI) -> None:
    @app.exception_handler(DBAPIError)
    async def _sqlalchemy(_: Request, exc: DBAPIError) -> JSONResponse:
        return _respuesta(exc)

    @app.exception_handler(oracledb.Error)
    async def _oracledb(_: Request, exc: oracledb.Error) -> JSONResponse:
        return _respuesta(exc)
