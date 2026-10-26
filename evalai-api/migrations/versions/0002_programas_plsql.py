"""Procedimientos, funciones, package PKG_RESULTADOS y triggers (Anexo A)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""
from collections.abc import Sequence

from alembic import op

from migrations.utilidades_sql import ejecutar_script, verificar_objetos_validos

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRIGGERS = [
    "trg_hoja_valida", "trg_hoja_evaluacion", "trg_respuesta_valida",
    "trg_pregunta_audita", "trg_pregunta_bloqueo", "trg_resultado_bitacora",
]
PROGRAMAS = [
    ("PROCEDURE", "sp_proceso_nocturno"),
    ("PROCEDURE", "sp_resumen_cursos"),
    ("PACKAGE", "pkg_resultados"),          # elimina también el cuerpo
    ("FUNCTION", "fn_evaluaciones_pendientes"),
    ("FUNCTION", "fn_calcular_nota"),
    ("PROCEDURE", "sp_registra_error"),
]


def upgrade() -> None:
    ejecutar_script("0002_programas.sql")
    verificar_objetos_validos(TRIGGERS + [nombre for _, nombre in PROGRAMAS])


def downgrade() -> None:
    conn = op.get_bind()
    for trigger in TRIGGERS:
        conn.exec_driver_sql(f"DROP TRIGGER {trigger}")
    for tipo, nombre in PROGRAMAS:
        conn.exec_driver_sql(f"DROP {tipo} {nombre}")
