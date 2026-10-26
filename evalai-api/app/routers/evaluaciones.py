"""Evaluaciones y sus preguntas.

Al cambiar la clave de una pregunta, TRG_PREGUNTA_AUDITA audita el cambio y deja
la evaluación pendiente de reproceso (RB-07). Mientras corre el proceso
nocturno, TRG_PREGUNTA_BLOQUEO rechaza cualquier cambio con 423 (RB-08).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text

from app import schemas
from app.db import fila, filas, get_conn

router = APIRouter(tags=["Evaluaciones"])

SQL_EVALUACION = """
    SELECT e.id_evaluacion, e.titulo, e.id_docente, d.nombre AS docente,
           e.id_curso, c.nivel || ' ' || c.letra AS curso, e.id_asignatura,
           e.fecha_aplicacion, e.estado,
           (SELECT COUNT(*) FROM pregunta p WHERE p.id_evaluacion = e.id_evaluacion) AS preguntas,
           (SELECT COUNT(*) FROM hoja_respuesta h WHERE h.id_evaluacion = e.id_evaluacion) AS hojas
      FROM evaluacion e
      JOIN docente d ON d.id_docente = e.id_docente
      JOIN curso c   ON c.id_curso = e.id_curso
"""
SQL_PREGUNTA = """
    SELECT id_pregunta, id_evaluacion, numero, id_indicador, alternativa_correcta, puntaje, origen
      FROM pregunta
"""


@router.get("/evaluaciones", response_model=list[schemas.Evaluacion])
def listar_evaluaciones(
    estado: schemas.EstadoEvaluacion | None = None,
    id_curso: int | None = None,
    id_asignatura: str | None = None,
    conn: Connection = Depends(get_conn),
):
    return filas(
        conn,
        SQL_EVALUACION + """
         WHERE (:estado IS NULL OR e.estado = :estado)
           AND (:curso IS NULL OR e.id_curso = :curso)
           AND (:asig IS NULL OR e.id_asignatura = :asig)
         ORDER BY e.id_evaluacion""",
        estado=estado,
        curso=id_curso,
        asig=id_asignatura,
    )


@router.get("/evaluaciones/{id_evaluacion}", response_model=schemas.Evaluacion)
def obtener_evaluacion(id_evaluacion: int, conn: Connection = Depends(get_conn)):
    evaluacion = fila(conn, SQL_EVALUACION + " WHERE e.id_evaluacion = :id", id=id_evaluacion)
    if not evaluacion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"La evaluación {id_evaluacion} no existe.")
    return evaluacion


@router.post("/evaluaciones", response_model=schemas.Evaluacion, status_code=status.HTTP_201_CREATED)
def crear_evaluacion(datos: schemas.EvaluacionCrear, conn: Connection = Depends(get_conn)):
    id_evaluacion = conn.execute(text("SELECT seq_evaluacion.NEXTVAL FROM dual")).scalar_one()
    conn.execute(
        text("""INSERT INTO evaluacion
                       (id_evaluacion, titulo, id_docente, id_curso, id_asignatura, fecha_aplicacion)
                VALUES (:id, :titulo, :id_docente, :id_curso, :id_asignatura, :fecha_aplicacion)"""),
        {"id": id_evaluacion, **datos.model_dump()},
    )
    conn.commit()
    return obtener_evaluacion(id_evaluacion, conn)


@router.patch("/evaluaciones/{id_evaluacion}", response_model=schemas.Evaluacion)
def actualizar_evaluacion(
    id_evaluacion: int, datos: schemas.EvaluacionActualizar, conn: Connection = Depends(get_conn)
):
    obtener_evaluacion(id_evaluacion, conn)
    cambios = datos.model_dump(exclude_none=True)
    if cambios:
        asignaciones = ", ".join(f"{columna} = :{columna}" for columna in cambios)
        conn.execute(
            text(f"UPDATE evaluacion SET {asignaciones} WHERE id_evaluacion = :id"),
            {**cambios, "id": id_evaluacion},
        )
        conn.commit()
    return obtener_evaluacion(id_evaluacion, conn)


@router.get("/evaluaciones/{id_evaluacion}/preguntas", response_model=list[schemas.Pregunta])
def listar_preguntas(id_evaluacion: int, conn: Connection = Depends(get_conn)):
    obtener_evaluacion(id_evaluacion, conn)
    return filas(conn, SQL_PREGUNTA + " WHERE id_evaluacion = :id ORDER BY numero", id=id_evaluacion)


@router.post(
    "/evaluaciones/{id_evaluacion}/preguntas",
    response_model=schemas.Pregunta,
    status_code=status.HTTP_201_CREATED,
)
def crear_pregunta(id_evaluacion: int, datos: schemas.PreguntaCrear, conn: Connection = Depends(get_conn)):
    obtener_evaluacion(id_evaluacion, conn)
    id_pregunta = conn.execute(text("SELECT seq_pregunta.NEXTVAL FROM dual")).scalar_one()
    conn.execute(
        text("""INSERT INTO pregunta
                       (id_pregunta, id_evaluacion, numero, id_indicador, alternativa_correcta, puntaje, origen)
                VALUES (:id, :id_evaluacion, :numero, :id_indicador, :alternativa_correcta, :puntaje, :origen)"""),
        {"id": id_pregunta, "id_evaluacion": id_evaluacion,
         **datos.model_dump(), "alternativa_correcta": datos.alternativa_correcta.upper()},
    )
    conn.commit()
    return fila(conn, SQL_PREGUNTA + " WHERE id_pregunta = :id", id=id_pregunta)


@router.patch("/preguntas/{id_pregunta}", response_model=schemas.PreguntaActualizada)
def actualizar_pregunta(
    id_pregunta: int, datos: schemas.PreguntaActualizar, conn: Connection = Depends(get_conn)
):
    """Corrige una pregunta generada por la IA (RF-5, HU-1.3).

    Si cambia la clave, queda en AUDITORIA_PREGUNTA y la evaluación vuelve a APLICADA.
    """
    if not fila(conn, SQL_PREGUNTA + " WHERE id_pregunta = :id", id=id_pregunta):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"La pregunta {id_pregunta} no existe.")
    cambios = datos.model_dump(exclude_none=True)
    if "alternativa_correcta" in cambios:
        cambios["alternativa_correcta"] = cambios["alternativa_correcta"].upper()
    if cambios:
        asignaciones = ", ".join(f"{columna} = :{columna}" for columna in cambios)
        conn.execute(
            text(f"UPDATE pregunta SET {asignaciones} WHERE id_pregunta = :id"),
            {**cambios, "id": id_pregunta},
        )
        conn.commit()
    return fila(
        conn,
        """SELECT p.id_pregunta, p.id_evaluacion, p.numero, p.id_indicador, p.alternativa_correcta,
                  p.puntaje, p.origen, e.estado AS estado_evaluacion
             FROM pregunta p JOIN evaluacion e ON e.id_evaluacion = p.id_evaluacion
            WHERE p.id_pregunta = :id""",
        id=id_pregunta,
    )
