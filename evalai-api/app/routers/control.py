"""Tablas de control: errores, auditoría de claves, bitácora de notas y estado de los objetos."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app import schemas
from app.db import filas, get_conn

router = APIRouter(prefix="/control", tags=["Control"])

OBJETOS_PLSQL = (
    "SP_PROCESO_NOCTURNO", "SP_RESUMEN_CURSOS", "SP_REGISTRA_ERROR",
    "FN_CALCULAR_NOTA", "FN_EVALUACIONES_PENDIENTES", "PKG_RESULTADOS",
    "TRG_HOJA_VALIDA", "TRG_HOJA_EVALUACION", "TRG_RESPUESTA_VALIDA",
    "TRG_PREGUNTA_AUDITA", "TRG_PREGUNTA_BLOQUEO", "TRG_RESULTADO_BITACORA",
)


@router.get("/errores", response_model=list[schemas.ErrorProceso])
def errores(limite: int = Query(default=100, ge=1, le=1000), conn: Connection = Depends(get_conn)):
    """ERROR_PROCESO: hojas que requieren nueva foto y otros errores de los procesos."""
    return filas(
        conn,
        """SELECT id_error, subprograma, mensaje, usuario, fecha
             FROM error_proceso ORDER BY id_error DESC FETCH FIRST :n ROWS ONLY""",
        n=limite,
    )


@router.get("/auditoria-preguntas", response_model=list[schemas.AuditoriaPregunta])
def auditoria_preguntas(id_pregunta: int | None = None, conn: Connection = Depends(get_conn)):
    """AUDITORIA_PREGUNTA: cambios de clave registrados por TRG_PREGUNTA_AUDITA."""
    return filas(
        conn,
        """SELECT id_auditoria, id_pregunta, alternativa_anterior, alternativa_nueva, usuario, fecha
             FROM auditoria_pregunta
            WHERE :p IS NULL OR id_pregunta = :p
            ORDER BY id_auditoria DESC""",
        p=id_pregunta,
    )


@router.get("/bitacora", response_model=list[schemas.Bitacora])
def bitacora(limite: int = Query(default=100, ge=1, le=1000), conn: Connection = Depends(get_conn)):
    """BITACORA_OPERACION: operaciones sobre RESULTADO_ESTUDIANTE (RNF-3)."""
    return filas(
        conn,
        """SELECT id_bitacora, tabla, operacion, usuario, fecha
             FROM bitacora_operacion ORDER BY id_bitacora DESC FETCH FIRST :n ROWS ONLY""",
        n=limite,
    )


@router.get("/bitacora/resumen", response_model=dict[str, int])
def bitacora_resumen(conn: Connection = Depends(get_conn)):
    """Operaciones por tipo (prueba 2 del informe: 46 INSERT y 11 UPDATE)."""
    return {
        r["operacion"]: r["total"]
        for r in filas(conn, "SELECT operacion, COUNT(*) AS total FROM bitacora_operacion GROUP BY operacion")
    }


@router.get("/objetos", response_model=list[schemas.ObjetoPlsql])
def objetos(conn: Connection = Depends(get_conn)):
    """Estado de los programas y triggers (prueba 8: todos VALID)."""
    nombres = ", ".join(f"'{n}'" for n in OBJETOS_PLSQL)
    return filas(
        conn,
        f"""SELECT object_name, object_type, status
              FROM user_objects
             WHERE object_name IN ({nombres})
             ORDER BY object_type, object_name""",
    )
