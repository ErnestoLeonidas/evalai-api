"""Tablas y secuencias del modelo de datos de EvalAI

Revision ID: 0001
Revises:
Create Date: 2026-10-25
"""
from collections.abc import Sequence

from alembic import op

from migrations.utilidades_sql import ejecutar_script

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# En orden inverso a las claves foráneas.
TABLAS = [
    "parametro_proceso", "bitacora_operacion", "auditoria_pregunta", "error_proceso",
    "resumen_curso_mes", "logro_indicador", "logro_estudiante_indicador", "resultado_estudiante",
    "respuesta", "hoja_respuesta", "pregunta", "evaluacion",
    "estudiante", "docente", "curso",
    "indicador_logro", "objetivo_aprendizaje", "asignatura",
]
SECUENCIAS = [
    "seq_estudiante", "seq_evaluacion", "seq_pregunta", "seq_hoja",
    "seq_error", "seq_auditoria", "seq_bitacora",
]


def upgrade() -> None:
    ejecutar_script("0001_esquema.sql")


def downgrade() -> None:
    conn = op.get_bind()
    for tabla in TABLAS:
        conn.exec_driver_sql(f"DROP TABLE {tabla} CASCADE CONSTRAINTS PURGE")
    for secuencia in SECUENCIAS:
        conn.exec_driver_sql(f"DROP SEQUENCE {secuencia}")
