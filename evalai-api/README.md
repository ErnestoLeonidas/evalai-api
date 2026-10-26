# EvalAI API

API local en **Python + FastAPI** para la capa de base de datos de EvalAI (Informe N°2, BDY1103).
Se conecta a Oracle Autonomous Database con el **wallet** de la carpeta `../wallet`, usando
`python-oracledb` en modo *thin*, así que no hace falta instalar Oracle Instant Client.

La lógica de negocio sigue en la base de datos, tal como la describe el informe. Los triggers
validan hojas, respuestas y preguntas, y `PKG_RESULTADOS` calcula puntajes, notas y logro por
indicador. La API expone esos objetos por HTTP y traduce sus errores (`RAISE_APPLICATION_ERROR`)
a códigos HTTP.

## Estructura

```
evalai-api/
├── app/
│   ├── main.py            # aplicación FastAPI
│   ├── config.py          # lee .env
│   ├── db.py              # engine con el wallet, helpers SQL y PL/SQL (DBMS_OUTPUT)
│   ├── errores.py         # ORA-200xx -> HTTP
│   ├── schemas.py         # modelos Pydantic
│   └── routers/           # catalogo, evaluaciones, hojas, procesos, reportes, control
├── migrations/
│   ├── versions/          # 0001 esquema · 0002 PL/SQL · 0003 datos de muestra
│   ├── sql/               # scripts SQL*Plus (también se pueden ejecutar con F5 en SQL Developer)
│   └── datos_muestra.py   # datos de octubre de 2026 (sección 2.4)
├── alembic.ini
└── requirements.txt
```

## 1. Instalación

```powershell
cd evalai-api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuración

Copia `.env.example` como `.env` y completa los valores:

| Variable          | Valor                                                                                    |
|-------------------|------------------------------------------------------------------------------------------|
| `DB_USER`         | Usuario del esquema (por ejemplo `ADMIN`).                                               |
| `DB_PASSWORD`     | Su clave.                                                                                |
| `DB_DSN`          | Alias de `tnsnames.ora`: `ut9bjwcq3z8a1dug_tp` (por defecto), `_low`, `_medium`, `_high`. |
| `WALLET_DIR`      | Carpeta del wallet; `../wallet` por defecto.                                             |
| `WALLET_PASSWORD` | La clave que elegiste al **descargar el wallet** en OCI (protege `ewallet.pem`).         |

## 3. Migraciones: cargar todo

```powershell
alembic upgrade head
```

| Revisión | Qué carga                                                                                                                                                                  |
|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0001`   | Las 18 tablas del modelo (sección 2.5) y las secuencias.                                                                                                                    |
| `0002`   | Los 13 objetos PL/SQL del Anexo A: `SP_REGISTRA_ERROR`, `FN_CALCULAR_NOTA`, `FN_EVALUACIONES_PENDIENTES`, `PKG_RESULTADOS`, `SP_RESUMEN_CURSOS`, `SP_PROCESO_NOCTURNO` y 6 triggers. Revisa `USER_ERRORS` y falla si algo no compila. |
| `0003`   | La muestra de la sección 2.4: 3 cursos, 36 estudiantes, 3 docentes, 2 asignaturas, 3 OA, 8 indicadores, 5 evaluaciones, 46 preguntas aplicadas, 47 hojas (la 40007 ilegible) y 528 respuestas. Las filas pasan por los triggers, que generan los códigos QR. |

Otros comandos útiles:

```powershell
alembic current            # en qué revisión está la base
alembic downgrade 0002     # borra solo los datos de muestra
alembic downgrade base     # borra todo (tablas, secuencias y programas)
```

> Si el esquema ya tiene estas tablas (por ejemplo, porque ejecutaste antes el script en SQL
> Developer), la migración `0001` falla con `ORA-00955`. Puedes borrarlas o, si ya están
> completas, marcar la base como migrada con `alembic stamp head`.

## 4. Levantar la API

```powershell
uvicorn app.main:app --reload
```

- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs
- Prueba de conexión: http://127.0.0.1:8000/health

## 5. Flujo del informe (sección 9)

Después de la migración hay 4 evaluaciones pendientes, igual que en el informe:

```powershell
curl http://127.0.0.1:8000/procesos/pendientes                 # pendientes: 4
curl -X POST http://127.0.0.1:8000/procesos/nocturno           # SP_PROCESO_NOCTURNO
curl http://127.0.0.1:8000/reportes/evaluaciones               # tabla 7
curl http://127.0.0.1:8000/reportes/logro-indicadores          # tabla 8 (reporte de UTP)
curl http://127.0.0.1:8000/reportes/resumen-mensual/202610     # tabla 9
curl http://127.0.0.1:8000/control/errores                     # hoja 40007 ilegible
```

`/procesos/nocturno` resume el mes actual (`SYSDATE`). En otro mes, procesa con
`POST /procesos/evaluaciones` y genera el resumen con `POST /procesos/resumen/202610`.

## Endpoints y objetos de la base de datos

| Endpoint                                                | Objeto que lo resuelve                                          |
|---------------------------------------------------------|-----------------------------------------------------------------|
| `POST /evaluaciones/{id}/hojas`                         | `TRG_HOJA_VALIDA`: valida el estudiante y genera el QR (RF-7)   |
| `GET /hojas/qr/{codigo}`                                | Identifica la hoja desde el QR de la foto (RF-8)                |
| `PUT /hojas/{id}/lectura`                               | `TRG_RESPUESTA_VALIDA` y `TRG_HOJA_EVALUACION`                  |
| `PATCH /preguntas/{id}`                                 | `TRG_PREGUNTA_AUDITA` y `TRG_PREGUNTA_BLOQUEO` (RB-07, RB-08)   |
| `GET /procesos/pendientes`                              | `FN_EVALUACIONES_PENDIENTES`                                    |
| `POST /procesos/nocturno`                               | `SP_PROCESO_NOCTURNO`                                           |
| `POST /procesos/evaluaciones[/{id}]`                    | `PKG_RESULTADOS.sp_procesar`, con o sin parámetro (sobrecarga)  |
| `POST /procesos/resumen/{periodo}`                      | `SP_RESUMEN_CURSOS`                                             |
| `GET /evaluaciones/{id}/resultados`                     | `RESULTADO_ESTUDIANTE` + `FN_CALCULAR_NOTA` en el SELECT        |
| `GET /reportes/logro-indicadores`                       | `LOGRO_INDICADOR` + `PKG_RESULTADOS.fn_pct_indicador` (RF-10)   |
| `GET /estudiantes/{id}/retroalimentacion`               | `LOGRO_ESTUDIANTE_INDICADOR` (RF-11)                            |
| `GET /reportes/nota?pct=75`                             | `FN_CALCULAR_NOTA` (RB-03)                                      |
| `GET /control/errores`, `/auditoria-preguntas`, `/bitacora` | Tablas de control                                           |
| `GET /control/objetos`                                  | Estado de los objetos PL/SQL en `USER_OBJECTS`                  |

### Errores de negocio

| Error Oracle | HTTP | Causa                                                    |
|--------------|------|----------------------------------------------------------|
| ORA-20001    | 404  | El estudiante o la evaluación de la hoja no existe       |
| ORA-20002/03 | 422  | Estudiante retirado o de otro curso                      |
| ORA-20004/05 | 422  | Alternativa no válida o pregunta de otra evaluación      |
| ORA-20006    | 404  | La hoja o la pregunta no existe                          |
| ORA-20010    | 409  | La evaluación no está aplicada (por ejemplo, la 1005)    |
| ORA-20020    | 423  | Preguntas bloqueadas mientras corre el proceso nocturno  |

La respuesta trae el mensaje del trigger tal cual, por ejemplo:
`{"detail": "El estudiante 2025 no pertenece al curso de la evaluación 1001.", "codigo_oracle": "ORA-20003"}`.
