"""Ejecuta scripts en formato SQL*Plus desde las migraciones de Alembic."""
import re
from pathlib import Path

from alembic import op

SQL_DIR = Path(__file__).resolve().parent / "sql"

_INICIO_PLSQL = re.compile(
    r"^\s*(CREATE\s+(OR\s+REPLACE\s+)?(PROCEDURE|FUNCTION|PACKAGE|TRIGGER|TYPE)\b|BEGIN\b|DECLARE\b)",
    re.IGNORECASE,
)


def dividir(script: str) -> list[str]:
    """Separa un script en sentencias.

    Las sentencias SQL terminan con ';' al final de la línea y los bloques
    PL/SQL (CREATE PROCEDURE/FUNCTION/PACKAGE/TRIGGER, BEGIN, DECLARE) con una
    línea que solo contiene '/'. Los comentarios entre sentencias se descartan.
    """
    sentencias: list[str] = []
    buffer: list[str] = []
    es_plsql = False
    for linea in script.splitlines():
        limpia = linea.strip()
        if not buffer:
            if not limpia or limpia.startswith("--"):
                continue
            es_plsql = bool(_INICIO_PLSQL.match(linea))
        if es_plsql:
            if limpia == "/":
                sentencias.append("\n".join(buffer).rstrip())
                buffer = []
            else:
                buffer.append(linea)
        else:
            buffer.append(linea)
            if limpia.split("--", 1)[0].rstrip().endswith(";"):
                sentencias.append("\n".join(buffer).rstrip().rstrip(";"))
                buffer = []
    if any(l.strip() for l in buffer):
        raise ValueError("El script termina con una sentencia sin ';' o '/':\n" + "\n".join(buffer))
    return sentencias


def ejecutar_script(nombre: str) -> None:
    # exec_driver_sql y no op.execute: op.execute pasa por text() de SQLAlchemy,
    # que confundiría :NEW y :OLD de los triggers con variables bind.
    conn = op.get_bind()
    for sentencia in dividir((SQL_DIR / nombre).read_text(encoding="utf-8")):
        conn.exec_driver_sql(sentencia)


def verificar_objetos_validos(nombres: list[str]) -> None:
    """Oracle crea un objeto PL/SQL aunque tenga errores de compilación: se revisa aquí."""
    lista = ", ".join(f"'{n.upper()}'" for n in nombres)
    errores = op.get_bind().exec_driver_sql(
        f"SELECT name, type, line, text FROM user_errors WHERE name IN ({lista}) "
        "ORDER BY name, sequence"
    ).fetchall()
    if errores:
        detalle = "\n".join(f"{n} ({t}) línea {l}: {txt.strip()}" for n, t, l, txt in errores)
        raise RuntimeError("Objetos PL/SQL con errores de compilación:\n" + detalle)
