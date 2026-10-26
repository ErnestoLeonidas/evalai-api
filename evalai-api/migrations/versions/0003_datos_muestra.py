"""Datos de muestra de octubre de 2026 (sección 2.4 del informe)

Las filas pasan por los triggers: TRG_HOJA_VALIDA genera el código QR de cada
hoja y TRG_RESPUESTA_VALIDA valida cada respuesta.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations import datos_muestra as d

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tabla(nombre: str, filas: list[dict]) -> sa.TableClause:
    return sa.table(nombre, *(sa.column(c) for c in filas[0]))


def upgrade() -> None:
    cargas = [
        ("parametro_proceso", d.PARAMETROS),
        ("asignatura", d.ASIGNATURAS),
        ("objetivo_aprendizaje", d.OBJETIVOS),
        ("indicador_logro", d.INDICADORES),
        ("curso", d.CURSOS),
        ("docente", d.DOCENTES),
        ("estudiante", d.ESTUDIANTES),
        ("evaluacion", d.EVALUACIONES),
        ("pregunta", d.preguntas()),
        ("hoja_respuesta", d.hojas()),
        ("respuesta", d.respuestas()),
    ]
    for nombre, filas in cargas:
        op.bulk_insert(_tabla(nombre, filas), filas)


def downgrade() -> None:
    evals = ", ".join(str(e["id_evaluacion"]) for e in d.EVALUACIONES)
    cursos = ", ".join(str(c["id_curso"]) for c in d.CURSOS)
    conn = op.get_bind()
    for sql in [
        f"DELETE FROM respuesta WHERE id_hoja IN (SELECT id_hoja FROM hoja_respuesta WHERE id_evaluacion IN ({evals}))",
        f"DELETE FROM logro_estudiante_indicador WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM logro_indicador WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM resultado_estudiante WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM resumen_curso_mes WHERE id_curso IN ({cursos})",
        f"DELETE FROM hoja_respuesta WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM pregunta WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM evaluacion WHERE id_evaluacion IN ({evals})",
        f"DELETE FROM estudiante WHERE id_curso IN ({cursos})",
        "DELETE FROM docente WHERE id_docente IN (" + ", ".join(str(x["id_docente"]) for x in d.DOCENTES) + ")",
        f"DELETE FROM curso WHERE id_curso IN ({cursos})",
        "DELETE FROM indicador_logro WHERE id_oa IN (" + ", ".join(str(o["id_oa"]) for o in d.OBJETIVOS) + ")",
        "DELETE FROM objetivo_aprendizaje WHERE id_oa IN (" + ", ".join(str(o["id_oa"]) for o in d.OBJETIVOS) + ")",
        "DELETE FROM asignatura WHERE id_asignatura IN ('MAT', 'LEN')",
        "DELETE FROM error_proceso",
        "DELETE FROM auditoria_pregunta",
        "DELETE FROM bitacora_operacion",
        "DELETE FROM parametro_proceso WHERE nombre = 'PROCESO_EN_CURSO'",
    ]:
        conn.exec_driver_sql(sql)
