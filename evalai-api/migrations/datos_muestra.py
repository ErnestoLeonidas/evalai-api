"""Datos de muestra del Informe N°2 (sección 2.4), Colegio Alerce Andino (ficticio).

3 cursos, 36 estudiantes, 3 docentes, 2 asignaturas, 3 OA con 8 indicadores y
5 evaluaciones de octubre de 2026: 4 aplicadas (46 preguntas, 47 hojas, una de
ellas ilegible, y 528 respuestas) y 1 publicada que aún no se aplica.

Las respuestas se generan a partir de PUNTAJES (puntaje de cada estudiante en
cada indicador), elegidos para que el proceso reproduzca las tablas 7, 8 y 9
del informe. Por ejemplo, el estudiante 2003 obtiene 4/4, 3/4 y 2/4 en la
evaluación 1001 (sección 9.1).
"""
from datetime import date, timedelta

ASIGNATURAS = [
    {"id_asignatura": "MAT", "nombre": "Matemática"},
    {"id_asignatura": "LEN", "nombre": "Lenguaje y Comunicación"},
]

OBJETIVOS = [
    {"id_oa": 1, "codigo": "MA07 OA 01", "id_asignatura": "MAT", "nivel": "7° básico",
     "descripcion": "Comprender la adición y la sustracción de números enteros, representándolas "
                    "en la recta numérica y aplicándolas en problemas cotidianos."},
    {"id_oa": 2, "codigo": "LE07 OA 03", "id_asignatura": "LEN", "nivel": "7° básico",
     "descripcion": "Analizar e interpretar cuentos, identificando su idea principal y el "
                    "propósito del autor a partir de evidencias del texto."},
    {"id_oa": 3, "codigo": "LE08 OA 10", "id_asignatura": "LEN", "nivel": "8° básico",
     "descripcion": "Analizar y evaluar textos argumentativos, distinguiendo hechos de opiniones, "
                    "la tesis y la validez de sus argumentos."},
]

INDICADORES = [
    {"id_indicador": 101, "id_oa": 1, "descripcion": "Representa números enteros en la recta numérica."},
    {"id_indicador": 102, "id_oa": 1, "descripcion": "Resuelve adiciones y sustracciones de números enteros."},
    {"id_indicador": 103, "id_oa": 1, "descripcion": "Resuelve problemas cotidianos con números enteros."},
    {"id_indicador": 201, "id_oa": 2, "descripcion": "Identifica la idea principal de un texto narrativo."},
    {"id_indicador": 202, "id_oa": 2, "descripcion": "Infiere el propósito del autor a partir de evidencias del texto."},
    {"id_indicador": 301, "id_oa": 3, "descripcion": "Distingue hechos de opiniones en un texto argumentativo."},
    {"id_indicador": 302, "id_oa": 3, "descripcion": "Identifica la tesis y los argumentos que la sostienen."},
    {"id_indicador": 303, "id_oa": 3, "descripcion": "Evalúa la validez de los argumentos de un texto."},
]

CURSOS = [
    {"id_curso": 701, "nivel": "7° básico", "letra": "A"},
    {"id_curso": 702, "nivel": "7° básico", "letra": "B"},
    {"id_curso": 801, "nivel": "8° básico", "letra": "A"},
]


def _run(numero: int) -> str:
    """RUN chileno con dígito verificador (módulo 11), formato 12.345.678-5."""
    suma, factor = 0, 2
    for d in reversed(str(numero)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    dv = 11 - suma % 11
    dv_txt = {10: "K", 11: "0"}.get(dv, str(dv))
    return f"{numero:,}".replace(",", ".") + "-" + dv_txt


DOCENTES = [
    {"id_docente": 11, "run": _run(13456782), "nombre": "Marcela Fuentes Araya",
     "email": "mfuentes@alerceandino.cl"},
    {"id_docente": 12, "run": _run(15872304), "nombre": "Rodrigo Vergara Silva",
     "email": "rvergara@alerceandino.cl"},
    {"id_docente": 13, "run": _run(16203958), "nombre": "Paula Contreras Muñoz",
     "email": "pcontreras@alerceandino.cl"},
]

_NOMBRES = [
    # 7° básico A: 2001 a 2012
    "Martina González Pérez", "Tomás Muñoz Rojas", "Benjamín Cárdenas Tapia", "Isidora Díaz Soto",
    "Vicente Morales Castro", "Florencia Reyes Vega", "Agustín Fernández Lagos", "Josefa Herrera Núñez",
    "Maximiliano Torres Pino", "Antonella Sepúlveda Ríos", "Joaquín Castillo Bravo", "Emilia Flores Campos",
    # 7° básico B: 2013 a 2024
    "Lucas Espinoza Navarro", "Catalina Jara Salinas", "Matías Vásquez Ortiz", "Sofía Riquelme Fuentes",
    "Cristóbal Contreras Lillo", "Valentina Gutiérrez Mora", "Gaspar Alarcón Peña", "Amanda Sandoval Toro",
    "Bastián Carrasco Leiva", "Trinidad Figueroa Paz", "Diego Olivares Méndez", "Javiera Pizarro Cortés",
    # 8° básico A: 2025 a 2036
    "Felipe Saavedra Lara", "Constanza Bustos Ibarra", "Ignacio Parra Valdés", "Fernanda Gallardo Mella",
    "Sebastián Aguilera Ruiz", "Antonia Cáceres Molina", "Nicolás Henríquez Vera", "Renata Orellana Zúñiga",
    "Alonso Montecinos Farías", "Maite Vidal Cornejo", "Franco Escobar Godoy", "Agustina Medina Yáñez",
]

ESTUDIANTES = [
    {
        "id_estudiante": 2001 + i,
        "run": _run(24100000 + 7919 * (i + 1)),
        "nombre": nombre,
        "id_curso": (701, 702, 801)[i // 12],
        # 2024 se retiró en septiembre: por eso 7° B rinde 11 hojas
        "estado": "RETIRADO" if 2001 + i == 2024 else "ACTIVO",
    }
    for i, nombre in enumerate(_NOMBRES)
]

EVALUACIONES = [
    {"id_evaluacion": 1001, "titulo": "Números enteros: unidad 1", "id_docente": 11, "id_curso": 701,
     "id_asignatura": "MAT", "fecha_aplicacion": date(2026, 10, 6), "estado": "APLICADA"},
    {"id_evaluacion": 1002, "titulo": "Números enteros: unidad 1", "id_docente": 11, "id_curso": 702,
     "id_asignatura": "MAT", "fecha_aplicacion": date(2026, 10, 7), "estado": "APLICADA"},
    {"id_evaluacion": 1003, "titulo": "Comprensión lectora: el cuento", "id_docente": 12, "id_curso": 701,
     "id_asignatura": "LEN", "fecha_aplicacion": date(2026, 10, 13), "estado": "APLICADA"},
    {"id_evaluacion": 1004, "titulo": "Textos argumentativos", "id_docente": 13, "id_curso": 801,
     "id_asignatura": "LEN", "fecha_aplicacion": date(2026, 10, 15), "estado": "APLICADA"},
    {"id_evaluacion": 1005, "titulo": "Comprensión lectora: el cuento", "id_docente": 12, "id_curso": 702,
     "id_asignatura": "LEN", "fecha_aplicacion": date(2026, 10, 29), "estado": "PUBLICADA"},
]

# Indicadores de cada evaluación y preguntas por indicador (1 punto cada una).
ESTRUCTURA = {
    1001: ([101, 102, 103], 4),
    1002: ([101, 102, 103], 4),
    1003: ([201, 202], 5),
    1004: ([301, 302, 303], 4),
    1005: ([201, 202], 5),
}

# Estudiantes que rinden cada evaluación aplicada, en orden de id.
RINDEN = {
    1001: list(range(2001, 2013)),
    1002: list(range(2013, 2024)),
    1003: list(range(2001, 2013)),
    1004: list(range(2025, 2037)),
}

HOJA_ILEGIBLE = (1001, 2007)   # hoja 40007: requiere nueva foto (HU-2.2)

# Puntaje por indicador de cada hoja corregida, en el orden de RINDEN
# (sin la hoja ilegible).
PUNTAJES = {
    1001: [(3, 3, 1), (4, 3, 0), (4, 3, 2), (3, 1, 0), (0, 4, 1), (3, 2, 2),
           (4, 4, 3), (4, 1, 1), (3, 4, 1), (4, 4, 4), (4, 2, 4)],
    1002: [(4, 2, 3), (4, 4, 2), (2, 4, 4), (3, 4, 2), (4, 4, 1), (4, 2, 4),
           (4, 0, 0), (2, 3, 3), (4, 2, 2), (3, 1, 4), (4, 2, 4)],
    1003: [(3, 1), (5, 5), (3, 1), (2, 4), (5, 2), (4, 4),
           (5, 0), (5, 3), (5, 4), (4, 2), (2, 2), (3, 4)],
    1004: [(1, 4, 3), (3, 3, 4), (4, 0, 0), (4, 3, 0), (4, 4, 0), (4, 0, 4),
           (1, 1, 0), (4, 2, 3), (4, 2, 4), (1, 1, 0), (4, 2, 3), (4, 4, 0)],
}

_CLAVES = "BDACCABDADBCACDB"
_LETRAS = "ABCD"


def preguntas() -> list[dict]:
    filas, id_pregunta, k = [], 30001, 0
    for id_eval, (indicadores, por_indicador) in ESTRUCTURA.items():
        numero = 1
        for id_ind in indicadores:
            for _ in range(por_indicador):
                filas.append({
                    "id_pregunta": id_pregunta, "id_evaluacion": id_eval, "numero": numero,
                    "id_indicador": id_ind, "alternativa_correcta": _CLAVES[k % len(_CLAVES)],
                    "puntaje": 1,
                    # algunas preguntas las reescribió el docente (RF-5)
                    "origen": "DOCENTE" if numero % 7 == 0 else "IA",
                })
                id_pregunta += 1
                numero += 1
                k += 1
    return filas


def hojas() -> list[dict]:
    fechas = {e["id_evaluacion"]: e["fecha_aplicacion"] for e in EVALUACIONES}
    filas, id_hoja = [], 40001
    for id_eval, estudiantes in RINDEN.items():
        for id_est in estudiantes:
            ilegible = (id_eval, id_est) == HOJA_ILEGIBLE
            filas.append({
                "id_hoja": id_hoja, "id_evaluacion": id_eval, "id_estudiante": id_est,
                "estado": "ILEGIBLE" if ilegible else "CORREGIDA",
                "fecha_correccion": None if ilegible else fechas[id_eval] + timedelta(days=1),
            })
            id_hoja += 1
    return filas


def respuestas() -> list[dict]:
    """Una fila por pregunta en cada hoja corregida; NULL si la pregunta se omitió."""
    por_eval: dict[int, list[dict]] = {}
    for p in preguntas():
        por_eval.setdefault(p["id_evaluacion"], []).append(p)

    filas = []
    for id_eval, hojas_eval in _hojas_corregidas().items():
        indicadores, q = ESTRUCTURA[id_eval]
        for fila_est, (id_hoja, puntajes) in enumerate(hojas_eval):
            for j, id_ind in enumerate(indicadores):
                preg = [p for p in por_eval[id_eval] if p["id_indicador"] == id_ind]
                # qué preguntas del indicador acierta: se rotan según el estudiante
                orden = sorted(range(q), key=lambda x: (x + fila_est) % q)
                correctas = set(orden[: puntajes[j]])
                for x, p in enumerate(preg):
                    clave = p["alternativa_correcta"]
                    if x in correctas:
                        alt = clave
                    elif (fila_est + x) % 5 == 0:
                        alt = None                                    # omitida
                    else:
                        alt = _LETRAS[(_LETRAS.index(clave) + 1 + (fila_est + x) % 3) % 4]
                    filas.append({"id_hoja": id_hoja, "id_pregunta": p["id_pregunta"], "alternativa": alt})
    return filas


def _hojas_corregidas() -> dict[int, list[tuple[int, tuple]]]:
    res: dict[int, list[tuple[int, tuple]]] = {}
    for h in hojas():
        if h["estado"] == "CORREGIDA":
            res.setdefault(h["id_evaluacion"], []).append(h["id_hoja"])
    return {ev: list(zip(ids, PUNTAJES[ev], strict=True)) for ev, ids in res.items()}


PARAMETROS = [{"nombre": "PROCESO_EN_CURSO", "valor": "N"}]
