"""Hojas de respuesta y respuestas leídas desde la foto.

Validaciones que hacen los triggers (la API solo traduce sus errores):
- TRG_HOJA_VALIDA: estudiante activo y del curso de la evaluación; genera el QR (RB-06, RF-7).
- TRG_HOJA_EVALUACION: una hoja CORREGIDA deja la evaluación pendiente (APLICADA).
- TRG_RESPUESTA_VALIDA: alternativa A a D (en mayúscula) y pregunta de la misma evaluación.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text

from app import schemas
from app.db import fila, filas, get_conn
from app.routers.evaluaciones import obtener_evaluacion

router = APIRouter(tags=["Hojas de respuesta"])

SQL_HOJA = """
    SELECT h.id_hoja, h.id_evaluacion, h.id_estudiante, s.nombre AS estudiante,
           h.codigo_qr, h.estado, h.fecha_correccion
      FROM hoja_respuesta h
      JOIN estudiante s ON s.id_estudiante = h.id_estudiante
"""


def _detalle(conn: Connection, hoja: dict) -> dict:
    hoja["respuestas"] = filas(
        conn,
        """SELECT p.id_pregunta, p.numero, r.alternativa, p.alternativa_correcta,
                  CASE WHEN r.alternativa = p.alternativa_correcta THEN 1 ELSE 0 END AS correcta
             FROM respuesta r
             JOIN pregunta p ON p.id_pregunta = r.id_pregunta
            WHERE r.id_hoja = :id
            ORDER BY p.numero""",
        id=hoja["id_hoja"],
    )
    return hoja


@router.get("/evaluaciones/{id_evaluacion}/hojas", response_model=list[schemas.Hoja])
def listar_hojas(
    id_evaluacion: int, estado: schemas.EstadoHoja | None = None, conn: Connection = Depends(get_conn)
):
    obtener_evaluacion(id_evaluacion, conn)
    return filas(
        conn,
        SQL_HOJA + """
         WHERE h.id_evaluacion = :id AND (:estado IS NULL OR h.estado = :estado)
         ORDER BY h.id_estudiante""",
        id=id_evaluacion,
        estado=estado,
    )


@router.post(
    "/evaluaciones/{id_evaluacion}/hojas",
    response_model=schemas.Hoja,
    status_code=status.HTTP_201_CREATED,
)
def crear_hoja(id_evaluacion: int, datos: schemas.HojaCrear, conn: Connection = Depends(get_conn)):
    """Genera la hoja de un estudiante para imprimirla; el código QR lo asigna el trigger."""
    id_hoja = conn.execute(text("SELECT seq_hoja.NEXTVAL FROM dual")).scalar_one()
    conn.execute(
        text("""INSERT INTO hoja_respuesta (id_hoja, id_evaluacion, id_estudiante, estado)
                VALUES (:id, :id_evaluacion, :id_estudiante, 'PENDIENTE')"""),
        {"id": id_hoja, "id_evaluacion": id_evaluacion, "id_estudiante": datos.id_estudiante},
    )
    conn.commit()
    return obtener_hoja(id_hoja, conn)


@router.get("/hojas/qr/{codigo_qr}", response_model=schemas.HojaDetalle)
def obtener_hoja_por_qr(codigo_qr: str, conn: Connection = Depends(get_conn)):
    """Identifica la hoja a partir del QR leído en la foto (RF-8)."""
    hoja = fila(conn, SQL_HOJA + " WHERE h.codigo_qr = :qr", qr=codigo_qr)
    if not hoja:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No hay una hoja con el código {codigo_qr}.")
    return _detalle(conn, hoja)


@router.get("/hojas/{id_hoja}", response_model=schemas.HojaDetalle)
def obtener_hoja(id_hoja: int, conn: Connection = Depends(get_conn)):
    hoja = fila(conn, SQL_HOJA + " WHERE h.id_hoja = :id", id=id_hoja)
    if not hoja:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"La hoja {id_hoja} no existe.")
    return _detalle(conn, hoja)


@router.put("/hojas/{id_hoja}/lectura", response_model=schemas.HojaDetalle)
def registrar_lectura(id_hoja: int, datos: schemas.LecturaHoja, conn: Connection = Depends(get_conn)):
    """Graba lo que la aplicación leyó de la foto (reemplaza una lectura anterior).

    Con estado CORREGIDA se guardan las respuestas y la evaluación queda pendiente
    de proceso. Con ILEGIBLE no se guardan respuestas: se pide una nueva foto (HU-2.2).
    Todo ocurre en una transacción: si una respuesta no es válida, no se graba nada.
    """
    hoja = obtener_hoja(id_hoja, conn)
    if datos.estado == "ILEGIBLE" and datos.respuestas:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Una hoja ILEGIBLE no lleva respuestas.")

    preguntas = {
        p["numero"]: p["id_pregunta"]
        for p in filas(conn, "SELECT numero, id_pregunta FROM pregunta WHERE id_evaluacion = :id",
                       id=hoja["id_evaluacion"])
    }
    desconocidas = sorted({r.numero for r in datos.respuestas} - preguntas.keys())
    if desconocidas:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La evaluación {hoja['id_evaluacion']} no tiene las preguntas {desconocidas}.",
        )

    conn.execute(text("DELETE FROM respuesta WHERE id_hoja = :id"), {"id": id_hoja})
    if datos.respuestas:
        conn.execute(
            text("INSERT INTO respuesta (id_hoja, id_pregunta, alternativa) VALUES (:hoja, :pregunta, :alt)"),
            [{"hoja": id_hoja, "pregunta": preguntas[r.numero], "alt": r.alternativa}
             for r in datos.respuestas],
        )
    conn.execute(
        text("""UPDATE hoja_respuesta
                   SET estado = :estado,
                       fecha_correccion = CASE WHEN :estado = 'CORREGIDA' THEN SYSDATE END
                 WHERE id_hoja = :id"""),
        {"estado": datos.estado, "id": id_hoja},
    )
    conn.commit()
    return obtener_hoja(id_hoja, conn)
