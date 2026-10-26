from fastapi import Depends, FastAPI
from sqlalchemy import Connection

from app import errores
from app.db import fila, get_conn
from app.routers import catalogo, control, evaluaciones, hojas, procesos, reportes

app = FastAPI(
    title="EvalAI API",
    version="1.0.0",
    description=(
        "API local de EvalAI sobre Oracle Autonomous Database (Informe N°2, BDY1103). "
        "Las reglas de negocio viven en la base de datos: los triggers validan hojas, "
        "respuestas y preguntas, y PKG_RESULTADOS calcula puntajes, notas y logro por indicador."
    ),
)
errores.registrar(app)

for modulo in (catalogo, evaluaciones, hojas, procesos, reportes, control):
    app.include_router(modulo.router)


@app.get("/health", tags=["Estado"])
def health(conn: Connection = Depends(get_conn)):
    """Verifica la conexión con la base de datos a través del wallet."""
    r = fila(
        conn,
        """SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') AS usuario,
                  SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS servicio,
                  (SELECT version_full FROM product_component_version WHERE ROWNUM = 1) AS version
             FROM dual""",
    )
    return {"estado": "ok", **r}
