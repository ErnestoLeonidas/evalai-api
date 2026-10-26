-- EvalAI · Migración 0001: tablas y secuencias (sección 2.5 del Informe N°2).
-- Formato SQL*Plus: las sentencias SQL terminan en ';' y los bloques PL/SQL en '/'.

-- 1. Base curricular ---------------------------------------------------------
CREATE TABLE asignatura (
  id_asignatura  VARCHAR2(10)  CONSTRAINT pk_asignatura PRIMARY KEY,
  nombre         VARCHAR2(60)  NOT NULL
);

CREATE TABLE objetivo_aprendizaje (
  id_oa          NUMBER(6)     CONSTRAINT pk_oa PRIMARY KEY,
  codigo         VARCHAR2(20)  NOT NULL CONSTRAINT uq_oa_codigo UNIQUE,
  id_asignatura  VARCHAR2(10)  NOT NULL CONSTRAINT fk_oa_asignatura REFERENCES asignatura,
  nivel          VARCHAR2(20)  NOT NULL,
  descripcion    VARCHAR2(400) NOT NULL
);

CREATE TABLE indicador_logro (
  id_indicador   NUMBER(6)     CONSTRAINT pk_indicador PRIMARY KEY,
  id_oa          NUMBER(6)     NOT NULL CONSTRAINT fk_indicador_oa REFERENCES objetivo_aprendizaje,
  descripcion    VARCHAR2(300) NOT NULL
);

-- 2. Comunidad escolar -------------------------------------------------------
CREATE TABLE curso (
  id_curso       NUMBER(6)     CONSTRAINT pk_curso PRIMARY KEY,
  nivel          VARCHAR2(20)  NOT NULL,
  letra          CHAR(1)       NOT NULL,
  CONSTRAINT uq_curso UNIQUE (nivel, letra)
);

CREATE TABLE docente (
  id_docente     NUMBER(6)     CONSTRAINT pk_docente PRIMARY KEY,
  run            VARCHAR2(12)  NOT NULL CONSTRAINT uq_docente_run UNIQUE,
  nombre         VARCHAR2(80)  NOT NULL,
  email          VARCHAR2(100) NOT NULL CONSTRAINT uq_docente_email UNIQUE
);

CREATE TABLE estudiante (
  id_estudiante  NUMBER(8)     CONSTRAINT pk_estudiante PRIMARY KEY,
  run            VARCHAR2(12)  NOT NULL CONSTRAINT uq_estudiante_run UNIQUE,
  nombre         VARCHAR2(80)  NOT NULL,
  id_curso       NUMBER(6)     NOT NULL CONSTRAINT fk_estudiante_curso REFERENCES curso,
  estado         VARCHAR2(10)  DEFAULT 'ACTIVO' NOT NULL
                 CONSTRAINT ck_estudiante_estado CHECK (estado IN ('ACTIVO', 'RETIRADO'))
);

-- 3. Ciclo de la evaluación --------------------------------------------------
CREATE TABLE evaluacion (
  id_evaluacion     NUMBER(8)     CONSTRAINT pk_evaluacion PRIMARY KEY,
  titulo            VARCHAR2(120) NOT NULL,
  id_docente        NUMBER(6)     NOT NULL CONSTRAINT fk_evaluacion_docente REFERENCES docente,
  id_curso          NUMBER(6)     NOT NULL CONSTRAINT fk_evaluacion_curso REFERENCES curso,
  id_asignatura     VARCHAR2(10)  NOT NULL CONSTRAINT fk_evaluacion_asignatura REFERENCES asignatura,
  fecha_aplicacion  DATE,
  estado            VARCHAR2(10)  DEFAULT 'BORRADOR' NOT NULL
                    CONSTRAINT ck_evaluacion_estado
                    CHECK (estado IN ('BORRADOR', 'PUBLICADA', 'APLICADA', 'CERRADA'))
);

CREATE TABLE pregunta (
  id_pregunta           NUMBER(8)    CONSTRAINT pk_pregunta PRIMARY KEY,
  id_evaluacion         NUMBER(8)    NOT NULL CONSTRAINT fk_pregunta_evaluacion REFERENCES evaluacion,
  numero                NUMBER(3)    NOT NULL,
  id_indicador          NUMBER(6)    NOT NULL CONSTRAINT fk_pregunta_indicador REFERENCES indicador_logro,
  alternativa_correcta  CHAR(1)      NOT NULL
                        CONSTRAINT ck_pregunta_alternativa CHECK (alternativa_correcta IN ('A', 'B', 'C', 'D')),
  puntaje               NUMBER(4,1)  DEFAULT 1 NOT NULL CONSTRAINT ck_pregunta_puntaje CHECK (puntaje > 0),
  origen                VARCHAR2(10) DEFAULT 'IA' NOT NULL
                        CONSTRAINT ck_pregunta_origen CHECK (origen IN ('IA', 'DOCENTE')),
  CONSTRAINT uq_pregunta_numero UNIQUE (id_evaluacion, numero)
);

CREATE TABLE hoja_respuesta (
  id_hoja           NUMBER(10)   CONSTRAINT pk_hoja PRIMARY KEY,
  id_evaluacion     NUMBER(8)    NOT NULL CONSTRAINT fk_hoja_evaluacion REFERENCES evaluacion,
  id_estudiante     NUMBER(8)    NOT NULL CONSTRAINT fk_hoja_estudiante REFERENCES estudiante,
  codigo_qr         VARCHAR2(30) NOT NULL CONSTRAINT uq_hoja_qr UNIQUE,   -- lo genera TRG_HOJA_VALIDA
  estado            VARCHAR2(10) DEFAULT 'PENDIENTE' NOT NULL
                    CONSTRAINT ck_hoja_estado CHECK (estado IN ('PENDIENTE', 'CORREGIDA', 'ILEGIBLE')),
  fecha_correccion  DATE,
  CONSTRAINT uq_hoja_eval_estudiante UNIQUE (id_evaluacion, id_estudiante)
);

CREATE TABLE respuesta (
  id_hoja      NUMBER(10) NOT NULL CONSTRAINT fk_respuesta_hoja REFERENCES hoja_respuesta,
  id_pregunta  NUMBER(8)  NOT NULL CONSTRAINT fk_respuesta_pregunta REFERENCES pregunta,
  alternativa  CHAR(1)    CONSTRAINT ck_respuesta_alternativa CHECK (alternativa IN ('A', 'B', 'C', 'D')),
  CONSTRAINT pk_respuesta PRIMARY KEY (id_hoja, id_pregunta)
);

-- 4. Tablas que generan los procesos -----------------------------------------
CREATE TABLE resultado_estudiante (
  id_evaluacion     NUMBER(8)    NOT NULL CONSTRAINT fk_res_evaluacion REFERENCES evaluacion,
  id_estudiante     NUMBER(8)    NOT NULL CONSTRAINT fk_res_estudiante REFERENCES estudiante,
  puntaje_obtenido  NUMBER(6,1)  NOT NULL,
  puntaje_total     NUMBER(6,1)  NOT NULL,
  pct_logro         NUMBER(4,1)  NOT NULL,
  nota              NUMBER(2,1)  NOT NULL,
  nivel_logro       VARCHAR2(25) NOT NULL,
  fecha_proceso     DATE         NOT NULL,
  CONSTRAINT pk_resultado_estudiante PRIMARY KEY (id_evaluacion, id_estudiante)
);

CREATE TABLE logro_estudiante_indicador (
  id_evaluacion     NUMBER(8)    NOT NULL CONSTRAINT fk_lei_evaluacion REFERENCES evaluacion,
  id_estudiante     NUMBER(8)    NOT NULL CONSTRAINT fk_lei_estudiante REFERENCES estudiante,
  id_indicador      NUMBER(6)    NOT NULL CONSTRAINT fk_lei_indicador REFERENCES indicador_logro,
  puntaje_obtenido  NUMBER(6,1)  NOT NULL,
  puntaje_total     NUMBER(6,1)  NOT NULL,
  pct_logro         NUMBER(4,1)  NOT NULL,
  nivel_logro       VARCHAR2(25) NOT NULL,
  CONSTRAINT pk_logro_estudiante_indicador PRIMARY KEY (id_evaluacion, id_estudiante, id_indicador)
);

CREATE TABLE logro_indicador (
  id_evaluacion      NUMBER(8)    NOT NULL CONSTRAINT fk_li_evaluacion REFERENCES evaluacion,
  id_indicador       NUMBER(6)    NOT NULL CONSTRAINT fk_li_indicador REFERENCES indicador_logro,
  total_estudiantes  NUMBER(5)    NOT NULL,
  puntaje_obtenido   NUMBER(8,1)  NOT NULL,
  puntaje_total      NUMBER(8,1)  NOT NULL,
  pct_logro          NUMBER(4,1)  NOT NULL,
  nivel_logro        VARCHAR2(25) NOT NULL,
  CONSTRAINT pk_logro_indicador PRIMARY KEY (id_evaluacion, id_indicador)
);

CREATE TABLE resumen_curso_mes (
  periodo             VARCHAR2(6)  NOT NULL,   -- YYYYMM
  id_curso            NUMBER(6)    NOT NULL CONSTRAINT fk_rcm_curso REFERENCES curso,
  id_asignatura       VARCHAR2(10) NOT NULL CONSTRAINT fk_rcm_asignatura REFERENCES asignatura,
  total_evaluaciones  NUMBER(5)    NOT NULL,
  total_resultados    NUMBER(6)    NOT NULL,
  pct_logro_promedio  NUMBER(4,1),
  nota_promedio       NUMBER(2,1),
  estudiantes_bajo_4  NUMBER(5),
  CONSTRAINT pk_resumen_curso_mes PRIMARY KEY (periodo, id_curso, id_asignatura)
);

-- 5. Tablas de control (sin claves foráneas) ---------------------------------
CREATE TABLE error_proceso (
  id_error     NUMBER(10)    CONSTRAINT pk_error_proceso PRIMARY KEY,
  subprograma  VARCHAR2(60)  NOT NULL,
  mensaje      VARCHAR2(400) NOT NULL,
  usuario      VARCHAR2(128) NOT NULL,
  fecha        DATE          NOT NULL
);

CREATE TABLE auditoria_pregunta (
  id_auditoria          NUMBER(10)    CONSTRAINT pk_auditoria_pregunta PRIMARY KEY,
  id_pregunta           NUMBER(8)     NOT NULL,
  alternativa_anterior  CHAR(1),
  alternativa_nueva     CHAR(1),
  usuario               VARCHAR2(128) NOT NULL,
  fecha                 DATE          NOT NULL
);

CREATE TABLE bitacora_operacion (
  id_bitacora  NUMBER(10)    CONSTRAINT pk_bitacora_operacion PRIMARY KEY,
  tabla        VARCHAR2(30)  NOT NULL,
  operacion    VARCHAR2(10)  NOT NULL,
  usuario      VARCHAR2(128) NOT NULL,
  fecha        DATE          NOT NULL
);

CREATE TABLE parametro_proceso (
  nombre  VARCHAR2(30)  CONSTRAINT pk_parametro_proceso PRIMARY KEY,
  valor   VARCHAR2(100) NOT NULL
);

-- 6. Secuencias --------------------------------------------------------------
-- Las de datos de negocio parten después de los IDs de la muestra (migración 0003).
CREATE SEQUENCE seq_estudiante  START WITH 2100  NOCACHE;
CREATE SEQUENCE seq_evaluacion  START WITH 1100  NOCACHE;
CREATE SEQUENCE seq_pregunta    START WITH 31000 NOCACHE;
CREATE SEQUENCE seq_hoja        START WITH 41000 NOCACHE;
CREATE SEQUENCE seq_error       START WITH 1;
CREATE SEQUENCE seq_auditoria   START WITH 1;
CREATE SEQUENCE seq_bitacora    START WITH 1;
