"""Conexión a Oracle Autonomous Database con el wallet (modo thin de python-oracledb).

El mismo engine lo usan la API y las migraciones de Alembic.
"""
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import oracledb
from sqlalchemy import Connection, Engine, create_engine, text

from app.config import get_settings


def crear_engine() -> Engine:
    s = get_settings()
    wallet = str(s.wallet_path)
    return create_engine(
        "oracle+oracledb://",
        connect_args={
            "user": s.db_user,
            "password": s.db_password,
            "dsn": s.db_dsn,             # alias definido en tnsnames.ora del wallet
            "config_dir": wallet,        # dónde está tnsnames.ora
            "wallet_location": wallet,   # dónde está ewallet.pem
            "wallet_password": s.wallet_password,
        },
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


@lru_cache
def get_engine() -> Engine:
    return crear_engine()


def get_conn() -> Iterator[Connection]:
    """Dependencia de FastAPI: una conexión por request.

    Las escrituras deben llamar a conn.commit(); si el request termina con una
    excepción, la transacción pendiente se deshace al devolver la conexión al pool.
    """
    with get_engine().connect() as conn:
        yield conn


def filas(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    """Ejecuta un SELECT y devuelve las filas como diccionarios (columnas en minúscula)."""
    return [{k.lower(): v for k, v in r.items()} for r in conn.execute(text(sql), params).mappings()]


def fila(conn: Connection, sql: str, **params: Any) -> dict[str, Any] | None:
    r = conn.execute(text(sql), params).mappings().first()
    return {k.lower(): v for k, v in r.items()} if r else None


def ejecutar_plsql(
    conn: Connection, bloque: str, salidas: tuple[str, ...] = (), **params: Any
) -> tuple[list[str], dict[str, Any]]:
    """Ejecuta un bloque PL/SQL con el driver (sin pasar por text()).

    Devuelve las líneas escritas con DBMS_OUTPUT y el valor de las variables
    bind de salida nombradas en `salidas` (numéricas).
    """
    cur = conn.connection.cursor()
    try:
        cur.callproc("dbms_output.enable", [None])
        variables = {nombre: cur.var(oracledb.DB_TYPE_NUMBER) for nombre in salidas}
        cur.execute(bloque, {**params, **variables})
        lineas: list[str] = []
        linea = cur.var(str)
        estado = cur.var(int)
        while True:
            cur.callproc("dbms_output.get_line", (linea, estado))
            if estado.getvalue() != 0:
                break
            lineas.append(linea.getvalue() or "")
        return lineas, {nombre: v.getvalue() for nombre, v in variables.items()}
    finally:
        cur.close()
