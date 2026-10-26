"""Base curricular (asignaturas, OA, indicadores) y comunidad escolar (cursos, docentes, estudiantes)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text

from app import schemas
from app.db import fila, filas, get_conn

router = APIRouter(tags=["Catálogo"])

SQL_CURSO = """
    SELECT c.id_curso, c.nivel, c.letra, c.nivel || ' ' || c.letra AS nombre,
           (SELECT COUNT(*) FROM estudiante e
             WHERE e.id_curso = c.id_curso AND e.estado = 'ACTIVO') AS estudiantes_activos
      FROM curso c
"""
SQL_ESTUDIANTE = "SELECT id_estudiante, run, nombre, id_curso, estado FROM estudiante"


@router.get("/asignaturas", response_model=list[schemas.Asignatura])
def listar_asignaturas(conn: Connection = Depends(get_conn)):
    return filas(conn, "SELECT id_asignatura, nombre FROM asignatura ORDER BY id_asignatura")


@router.get("/objetivos", response_model=list[schemas.ObjetivoAprendizaje])
def listar_objetivos(id_asignatura: str | None = None, conn: Connection = Depends(get_conn)):
    return filas(
        conn,
        """SELECT id_oa, codigo, id_asignatura, nivel, descripcion
             FROM objetivo_aprendizaje
            WHERE :asig IS NULL OR id_asignatura = :asig
            ORDER BY id_oa""",
        asig=id_asignatura,
    )


@router.get("/indicadores", response_model=list[schemas.Indicador])
def listar_indicadores(id_oa: int | None = None, conn: Connection = Depends(get_conn)):
    return filas(
        conn,
        """SELECT id_indicador, id_oa, descripcion
             FROM indicador_logro
            WHERE :oa IS NULL OR id_oa = :oa
            ORDER BY id_indicador""",
        oa=id_oa,
    )


@router.get("/cursos", response_model=list[schemas.Curso])
def listar_cursos(conn: Connection = Depends(get_conn)):
    return filas(conn, SQL_CURSO + " ORDER BY c.id_curso")


@router.get("/cursos/{id_curso}", response_model=schemas.Curso)
def obtener_curso(id_curso: int, conn: Connection = Depends(get_conn)):
    curso = fila(conn, SQL_CURSO + " WHERE c.id_curso = :id", id=id_curso)
    if not curso:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"El curso {id_curso} no existe.")
    return curso


@router.get("/cursos/{id_curso}/estudiantes", response_model=list[schemas.Estudiante])
def listar_estudiantes_curso(id_curso: int, conn: Connection = Depends(get_conn)):
    obtener_curso(id_curso, conn)
    return filas(conn, SQL_ESTUDIANTE + " WHERE id_curso = :id ORDER BY id_estudiante", id=id_curso)


@router.get("/docentes", response_model=list[schemas.Docente])
def listar_docentes(conn: Connection = Depends(get_conn)):
    return filas(conn, "SELECT id_docente, run, nombre, email FROM docente ORDER BY id_docente")


@router.get("/estudiantes", response_model=list[schemas.Estudiante])
def listar_estudiantes(
    id_curso: int | None = None,
    estado: schemas.EstadoEstudiante | None = None,
    conn: Connection = Depends(get_conn),
):
    return filas(
        conn,
        SQL_ESTUDIANTE + """
            WHERE (:curso IS NULL OR id_curso = :curso)
              AND (:estado IS NULL OR estado = :estado)
            ORDER BY id_estudiante""",
        curso=id_curso,
        estado=estado,
    )


@router.get("/estudiantes/{id_estudiante}", response_model=schemas.Estudiante)
def obtener_estudiante(id_estudiante: int, conn: Connection = Depends(get_conn)):
    estudiante = fila(conn, SQL_ESTUDIANTE + " WHERE id_estudiante = :id", id=id_estudiante)
    if not estudiante:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"El estudiante {id_estudiante} no existe.")
    return estudiante


@router.post("/estudiantes", response_model=schemas.Estudiante, status_code=status.HTTP_201_CREATED)
def crear_estudiante(datos: schemas.EstudianteCrear, conn: Connection = Depends(get_conn)):
    id_estudiante = conn.execute(text("SELECT seq_estudiante.NEXTVAL FROM dual")).scalar_one()
    conn.execute(
        text("""INSERT INTO estudiante (id_estudiante, run, nombre, id_curso)
                VALUES (:id, :run, :nombre, :curso)"""),
        {"id": id_estudiante, "run": datos.run, "nombre": datos.nombre, "curso": datos.id_curso},
    )
    conn.commit()
    return obtener_estudiante(id_estudiante, conn)


@router.patch("/estudiantes/{id_estudiante}", response_model=schemas.Estudiante)
def actualizar_estudiante(
    id_estudiante: int, datos: schemas.EstudianteActualizar, conn: Connection = Depends(get_conn)
):
    obtener_estudiante(id_estudiante, conn)
    cambios = datos.model_dump(exclude_none=True)
    if cambios:
        asignaciones = ", ".join(f"{columna} = :{columna}" for columna in cambios)
        conn.execute(
            text(f"UPDATE estudiante SET {asignaciones} WHERE id_estudiante = :id"),
            {**cambios, "id": id_estudiante},
        )
        conn.commit()
    return obtener_estudiante(id_estudiante, conn)
