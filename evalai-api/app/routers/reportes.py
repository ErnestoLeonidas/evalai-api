"""Reportes sobre las tablas que generan los procesos (sección 9 del informe)."""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import Connection

from app import schemas
from app.db import ejecutar_plsql, filas, get_conn
from app.routers.catalogo import obtener_estudiante
from app.routers.evaluaciones import obtener_evaluacion

router = APIRouter(tags=["Reportes"])

# Reporte de UTP (sección 6.3): usa la función del package dentro del SELECT.
SQL_LOGRO_INDICADOR = """
    SELECT e.id_evaluacion, c.nivel || ' ' || c.letra AS curso, i.id_indicador, i.descripcion,
           li.total_estudiantes, li.puntaje_obtenido, li.puntaje_total,
           pkg_resultados.fn_pct_indicador(e.id_evaluacion, i.id_indicador) AS pct_logro,
           li.nivel_logro
      FROM logro_indicador li
      JOIN evaluacion e      ON e.id_evaluacion = li.id_evaluacion
      JOIN curso c           ON c.id_curso = e.id_curso
      JOIN indicador_logro i ON i.id_indicador = li.id_indicador
"""


@router.get("/reportes/evaluaciones", response_model=list[schemas.ResumenEvaluacion])
def resumen_evaluaciones(conn: Connection = Depends(get_conn)):
    """Hojas procesadas, omitidas, logro y nota promedio por evaluación (tabla 7)."""
    return filas(
        conn,
        """SELECT e.id_evaluacion, e.titulo, c.nivel || ' ' || c.letra AS curso, e.id_asignatura, e.estado,
                  (SELECT COUNT(*) FROM resultado_estudiante r WHERE r.id_evaluacion = e.id_evaluacion) AS hojas,
                  (SELECT COUNT(*) FROM hoja_respuesta h
                    WHERE h.id_evaluacion = e.id_evaluacion AND h.estado <> 'CORREGIDA') AS omitidas,
                  (SELECT ROUND(AVG(r.pct_logro), 1) FROM resultado_estudiante r
                    WHERE r.id_evaluacion = e.id_evaluacion) AS pct_logro_promedio,
                  (SELECT ROUND(AVG(r.nota), 1) FROM resultado_estudiante r
                    WHERE r.id_evaluacion = e.id_evaluacion) AS nota_promedio
             FROM evaluacion e
             JOIN curso c ON c.id_curso = e.id_curso
            ORDER BY e.id_evaluacion""",
    )


@router.get("/evaluaciones/{id_evaluacion}/resultados", response_model=list[schemas.ResultadoEstudiante])
def resultados_evaluacion(id_evaluacion: int, conn: Connection = Depends(get_conn)):
    """Resultado por estudiante; la nota se verifica con FN_CALCULAR_NOTA en el SELECT."""
    obtener_evaluacion(id_evaluacion, conn)
    return filas(
        conn,
        """SELECT r.id_evaluacion, r.id_estudiante, s.nombre, r.puntaje_obtenido, r.puntaje_total,
                  r.pct_logro, r.nota,
                  fn_calcular_nota(r.puntaje_obtenido / r.puntaje_total * 100) AS nota_verificada,
                  r.nivel_logro, r.fecha_proceso
             FROM resultado_estudiante r
             JOIN estudiante s ON s.id_estudiante = r.id_estudiante
            WHERE r.id_evaluacion = :id
            ORDER BY r.id_estudiante""",
        id=id_evaluacion,
    )


@router.get("/evaluaciones/{id_evaluacion}/logro-indicadores", response_model=list[schemas.LogroIndicador])
def logro_indicadores_evaluacion(id_evaluacion: int, conn: Connection = Depends(get_conn)):
    """Logro del curso por indicador en una evaluación (RF-10, RN-2)."""
    obtener_evaluacion(id_evaluacion, conn)
    return filas(conn, SQL_LOGRO_INDICADOR + " WHERE e.id_evaluacion = :id ORDER BY i.id_indicador",
                 id=id_evaluacion)


@router.get("/reportes/logro-indicadores", response_model=list[schemas.LogroIndicador])
def logro_indicadores(
    id_curso: int | None = None,
    nivel_logro: schemas.NivelLogro | None = None,
    conn: Connection = Depends(get_conn),
):
    """Reporte de UTP: logro por curso e indicador de todas las evaluaciones (tabla 8)."""
    return filas(
        conn,
        SQL_LOGRO_INDICADOR + """
         WHERE (:curso IS NULL OR e.id_curso = :curso)
           AND (:nivel IS NULL OR li.nivel_logro = :nivel)
         ORDER BY e.id_evaluacion, i.id_indicador""",
        curso=id_curso,
        nivel=nivel_logro,
    )


@router.get("/estudiantes/{id_estudiante}/retroalimentacion", response_model=list[schemas.Retroalimentacion])
def retroalimentacion(
    id_estudiante: int, id_evaluacion: int | None = None, conn: Connection = Depends(get_conn)
):
    """Logro del estudiante por indicador en cada evaluación procesada (RF-11, HU-5)."""
    obtener_estudiante(id_estudiante, conn)
    resultados = filas(
        conn,
        """SELECT r.id_evaluacion, e.titulo, r.id_estudiante, s.nombre, r.pct_logro, r.nota, r.nivel_logro
             FROM resultado_estudiante r
             JOIN evaluacion e ON e.id_evaluacion = r.id_evaluacion
             JOIN estudiante s ON s.id_estudiante = r.id_estudiante
            WHERE r.id_estudiante = :est AND (:ev IS NULL OR r.id_evaluacion = :ev)
            ORDER BY r.id_evaluacion""",
        est=id_estudiante,
        ev=id_evaluacion,
    )
    for r in resultados:
        r["indicadores"] = filas(
            conn,
            """SELECT l.id_indicador, i.descripcion, l.puntaje_obtenido, l.puntaje_total,
                      l.pct_logro, l.nivel_logro
                 FROM logro_estudiante_indicador l
                 JOIN indicador_logro i ON i.id_indicador = l.id_indicador
                WHERE l.id_evaluacion = :ev AND l.id_estudiante = :est
                ORDER BY l.id_indicador""",
            ev=r["id_evaluacion"],
            est=id_estudiante,
        )
    return resultados


@router.get("/reportes/resumen-mensual/{periodo}", response_model=list[schemas.ResumenCursoMes])
def resumen_mensual(
    periodo: str = Path(pattern=r"^\d{4}(0[1-9]|1[0-2])$", examples=["202610"]),
    conn: Connection = Depends(get_conn),
):
    """RESUMEN_CURSO_MES de un periodo YYYYMM (tabla 9)."""
    return filas(
        conn,
        """SELECT r.periodo, r.id_curso, c.nivel || ' ' || c.letra AS curso, r.id_asignatura,
                  r.total_evaluaciones, r.total_resultados, r.pct_logro_promedio,
                  r.nota_promedio, r.estudiantes_bajo_4
             FROM resumen_curso_mes r
             JOIN curso c ON c.id_curso = r.id_curso
            WHERE r.periodo = :periodo
            ORDER BY r.id_curso, r.id_asignatura""",
        periodo=periodo,
    )


@router.get("/reportes/nota", response_model=schemas.Nota)
def calcular_nota(
    pct: float = Query(ge=0, le=100, description="Porcentaje de logro."),
    exigencia: float | None = Query(default=None, gt=0, lt=100,
                                    description="Por defecto pkg_resultados.c_exigencia (60)."),
    conn: Connection = Depends(get_conn),
):
    """FN_CALCULAR_NOTA (RB-03): nota de 1,0 a 7,0 para un porcentaje de logro."""
    # En 19c una constante de package no se puede leer desde SQL: se usa un bloque PL/SQL.
    _, r = ejecutar_plsql(
        conn,
        """BEGIN
             :exigencia := NVL(:ex, pkg_resultados.c_exigencia);
             :nota      := fn_calcular_nota(:pct, :exigencia);
           END;""",
        salidas=("exigencia", "nota"),
        pct=pct,
        ex=exigencia,
    )
    return {"pct": pct, "exigencia": r["exigencia"], "nota": r["nota"]}
