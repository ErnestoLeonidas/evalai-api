"""Procesamiento de resultados: invoca los programas almacenados (secciones 6 y 7).

Los programas hacen su propio COMMIT y registran sus errores en ERROR_PROCESO.
"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy import Connection

from app import schemas
from app.db import fila, filas, get_conn, ejecutar_plsql

router = APIRouter(prefix="/procesos", tags=["Procesamiento"])

# Los contadores del package son variables de sesión: se leen en el mismo bloque.
CONTADORES = """
  :procesadas := pkg_resultados.g_hojas_procesadas;
  :omitidas   := pkg_resultados.g_hojas_omitidas;
"""


def _pendientes(conn: Connection) -> int:
    return fila(conn, "SELECT fn_evaluaciones_pendientes AS n FROM dual")["n"]


def _resultado(conn: Connection, salida: list[str], valores: dict) -> dict:
    return {
        "salida": salida,
        "hojas_procesadas": valores.get("procesadas"),
        "hojas_omitidas": valores.get("omitidas"),
        "pendientes": _pendientes(conn),
    }


@router.get("/pendientes", response_model=schemas.Pendientes)
def pendientes(conn: Connection = Depends(get_conn)):
    """FN_EVALUACIONES_PENDIENTES y estado del parámetro PROCESO_EN_CURSO."""
    evaluaciones = filas(
        conn, "SELECT id_evaluacion FROM evaluacion WHERE estado = 'APLICADA' ORDER BY id_evaluacion"
    )
    en_curso = fila(conn, "SELECT valor FROM parametro_proceso WHERE nombre = 'PROCESO_EN_CURSO'")
    return {
        "pendientes": _pendientes(conn),
        "evaluaciones": [e["id_evaluacion"] for e in evaluaciones],
        "proceso_en_curso": bool(en_curso and en_curso["valor"] == "S"),
    }


@router.post("/nocturno", response_model=schemas.ResultadoProceso)
def proceso_nocturno(conn: Connection = Depends(get_conn)):
    """SP_PROCESO_NOCTURNO: procesa todas las pendientes y genera el resumen del mes actual."""
    salida, valores = ejecutar_plsql(
        conn, "BEGIN sp_proceso_nocturno;" + CONTADORES + "END;", salidas=("procesadas", "omitidas")
    )
    return _resultado(conn, salida, valores)


@router.post("/evaluaciones", response_model=schemas.ResultadoProceso)
def procesar_pendientes(conn: Connection = Depends(get_conn)):
    """PKG_RESULTADOS.sp_procesar sin parámetros (sobrecarga): todas las pendientes, sin resumen."""
    salida, valores = ejecutar_plsql(
        conn, "BEGIN pkg_resultados.sp_procesar;" + CONTADORES + "END;", salidas=("procesadas", "omitidas")
    )
    return _resultado(conn, salida, valores)


@router.post("/evaluaciones/{id_evaluacion}", response_model=schemas.ResultadoProceso)
def procesar_evaluacion(id_evaluacion: int, conn: Connection = Depends(get_conn)):
    """PKG_RESULTADOS.sp_procesar(p_id_evaluacion): procesa una evaluación en el momento.

    Una evaluación que no está APLICADA ni CERRADA responde 409 (ORA-20010).
    """
    salida, valores = ejecutar_plsql(
        conn,
        """BEGIN
             pkg_resultados.g_hojas_procesadas := 0;
             pkg_resultados.g_hojas_omitidas   := 0;
             pkg_resultados.sp_procesar(:id);""" + CONTADORES + "END;",
        salidas=("procesadas", "omitidas"),
        id=id_evaluacion,
    )
    return _resultado(conn, salida, valores)


@router.post("/resumen/{periodo}", response_model=schemas.ResultadoProceso)
def resumen_mensual(
    periodo: str = Path(pattern=r"^\d{4}(0[1-9]|1[0-2])$", examples=["202610"]),
    conn: Connection = Depends(get_conn),
):
    """SP_RESUMEN_CURSOS(p_periodo): rehace el resumen por curso y asignatura de un mes (YYYYMM)."""
    salida, _ = ejecutar_plsql(conn, "BEGIN sp_resumen_cursos(:periodo); END;", periodo=periodo)
    return _resultado(conn, salida, {})
