from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

EstadoEstudiante = Literal["ACTIVO", "RETIRADO"]
EstadoEvaluacion = Literal["BORRADOR", "PUBLICADA", "APLICADA", "CERRADA"]
EstadoHoja = Literal["PENDIENTE", "CORREGIDA", "ILEGIBLE"]
Alternativa = Literal["A", "B", "C", "D", "a", "b", "c", "d"]   # el trigger la normaliza a mayúscula
NivelLogro = Literal["POR LOGRAR", "MEDIANAMENTE LOGRADO", "LOGRADO"]


# Base curricular y comunidad escolar ------------------------------------------
class Asignatura(BaseModel):
    id_asignatura: str
    nombre: str


class ObjetivoAprendizaje(BaseModel):
    id_oa: int
    codigo: str
    id_asignatura: str
    nivel: str
    descripcion: str


class Indicador(BaseModel):
    id_indicador: int
    id_oa: int
    descripcion: str


class Curso(BaseModel):
    id_curso: int
    nivel: str
    letra: str
    nombre: str
    estudiantes_activos: int


class Docente(BaseModel):
    id_docente: int
    run: str
    nombre: str
    email: str


class EstudianteCrear(BaseModel):
    run: str = Field(max_length=12, examples=["25.123.456-7"])
    nombre: str = Field(max_length=80)
    id_curso: int


class EstudianteActualizar(BaseModel):
    nombre: str | None = Field(default=None, max_length=80)
    id_curso: int | None = None
    estado: EstadoEstudiante | None = None


class Estudiante(BaseModel):
    id_estudiante: int
    run: str
    nombre: str
    id_curso: int
    estado: EstadoEstudiante


# Evaluaciones y preguntas ------------------------------------------------------
class EvaluacionCrear(BaseModel):
    titulo: str = Field(max_length=120)
    id_docente: int
    id_curso: int
    id_asignatura: str
    fecha_aplicacion: date | None = None


class EvaluacionActualizar(BaseModel):
    titulo: str | None = Field(default=None, max_length=120)
    fecha_aplicacion: date | None = None
    estado: Literal["BORRADOR", "PUBLICADA"] | None = Field(
        default=None,
        description="APLICADA y CERRADA las asignan los triggers y PKG_RESULTADOS.",
    )


class Evaluacion(BaseModel):
    id_evaluacion: int
    titulo: str
    id_docente: int
    docente: str
    id_curso: int
    curso: str
    id_asignatura: str
    fecha_aplicacion: date | None
    estado: EstadoEvaluacion
    preguntas: int
    hojas: int


class PreguntaCrear(BaseModel):
    numero: int = Field(ge=1)
    id_indicador: int
    alternativa_correcta: Alternativa
    puntaje: float = Field(default=1, gt=0)
    origen: Literal["IA", "DOCENTE"] = "IA"


class PreguntaActualizar(BaseModel):
    alternativa_correcta: Alternativa | None = None
    puntaje: float | None = Field(default=None, gt=0)
    origen: Literal["IA", "DOCENTE"] | None = None


class Pregunta(BaseModel):
    id_pregunta: int
    id_evaluacion: int
    numero: int
    id_indicador: int
    alternativa_correcta: str
    puntaje: float
    origen: str


class PreguntaActualizada(Pregunta):
    estado_evaluacion: EstadoEvaluacion


# Hojas de respuesta --------------------------------------------------------------
class HojaCrear(BaseModel):
    id_estudiante: int


class Hoja(BaseModel):
    id_hoja: int
    id_evaluacion: int
    id_estudiante: int
    estudiante: str
    codigo_qr: str
    estado: EstadoHoja
    fecha_correccion: datetime | None


class RespuestaLeida(BaseModel):
    numero: int = Field(ge=1, description="Número de la pregunta en la evaluación.")
    alternativa: Alternativa | None = Field(description="null si el estudiante omitió la pregunta.")


class LecturaHoja(BaseModel):
    """Lo que entrega la aplicación al leer la foto de una hoja."""
    estado: Literal["CORREGIDA", "ILEGIBLE"] = "CORREGIDA"
    respuestas: list[RespuestaLeida] = []


class Respuesta(BaseModel):
    id_pregunta: int
    numero: int
    alternativa: str | None
    alternativa_correcta: str
    correcta: bool


class HojaDetalle(Hoja):
    respuestas: list[Respuesta]


# Procesamiento -----------------------------------------------------------------
class Pendientes(BaseModel):
    pendientes: int
    evaluaciones: list[int]
    proceso_en_curso: bool


class ResultadoProceso(BaseModel):
    salida: list[str] = Field(description="Líneas de DBMS_OUTPUT del proceso.")
    hojas_procesadas: int | None = None
    hojas_omitidas: int | None = None
    pendientes: int


# Reportes ----------------------------------------------------------------------
class ResultadoEstudiante(BaseModel):
    id_evaluacion: int
    id_estudiante: int
    nombre: str
    puntaje_obtenido: float
    puntaje_total: float
    pct_logro: float
    nota: float
    nota_verificada: float
    nivel_logro: NivelLogro
    fecha_proceso: datetime


class LogroIndicador(BaseModel):
    id_evaluacion: int
    curso: str
    id_indicador: int
    descripcion: str
    total_estudiantes: int
    puntaje_obtenido: float
    puntaje_total: float
    pct_logro: float | None
    nivel_logro: NivelLogro


class LogroEstudianteIndicador(BaseModel):
    id_indicador: int
    descripcion: str
    puntaje_obtenido: float
    puntaje_total: float
    pct_logro: float
    nivel_logro: NivelLogro


class Retroalimentacion(BaseModel):
    id_evaluacion: int
    titulo: str
    id_estudiante: int
    nombre: str
    pct_logro: float
    nota: float
    nivel_logro: NivelLogro
    indicadores: list[LogroEstudianteIndicador]


class ResumenEvaluacion(BaseModel):
    id_evaluacion: int
    titulo: str
    curso: str
    id_asignatura: str
    estado: EstadoEvaluacion
    hojas: int
    omitidas: int
    pct_logro_promedio: float | None
    nota_promedio: float | None


class ResumenCursoMes(BaseModel):
    periodo: str
    id_curso: int
    curso: str
    id_asignatura: str
    total_evaluaciones: int
    total_resultados: int
    pct_logro_promedio: float | None
    nota_promedio: float | None
    estudiantes_bajo_4: int | None


class Nota(BaseModel):
    pct: float
    exigencia: float
    nota: float


# Control -----------------------------------------------------------------------
class ErrorProceso(BaseModel):
    id_error: int
    subprograma: str
    mensaje: str
    usuario: str
    fecha: datetime


class AuditoriaPregunta(BaseModel):
    id_auditoria: int
    id_pregunta: int
    alternativa_anterior: str | None
    alternativa_nueva: str | None
    usuario: str
    fecha: datetime


class Bitacora(BaseModel):
    id_bitacora: int
    tabla: str
    operacion: str
    usuario: str
    fecha: datetime


class ObjetoPlsql(BaseModel):
    object_name: str
    object_type: str
    status: str
