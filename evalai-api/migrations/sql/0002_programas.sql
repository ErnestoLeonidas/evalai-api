-- EvalAI · Migración 0002: programas almacenados (Anexo A del Informe N°2).
-- Se copian tal cual del informe. Orden: los procedimientos y funciones antes
-- que el cuerpo del package que los usa; los triggers al final.

-- 4.1 Procedimiento con parámetros: registra errores sin depender de la
--     transacción del proceso que falló (transacción autónoma).
CREATE OR REPLACE PROCEDURE sp_registra_error (
  p_subprograma  IN VARCHAR2,
  p_mensaje      IN VARCHAR2
) IS
  PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
  INSERT INTO error_proceso
  VALUES (seq_error.NEXTVAL, SUBSTR(p_subprograma, 1, 60), SUBSTR(p_mensaje, 1, 400), USER, SYSDATE);
  COMMIT;
END sp_registra_error;
/

-- 4.2 Especificación del package: lo único visible desde fuera.
CREATE OR REPLACE PACKAGE pkg_resultados IS
  -- constructores públicos
  c_exigencia           CONSTANT NUMBER := 60;   -- % de logro para la nota 4,0
  g_hojas_procesadas    NUMBER := 0;
  g_hojas_omitidas      NUMBER := 0;

  PROCEDURE sp_procesar (p_id_evaluacion IN NUMBER);
  PROCEDURE sp_procesar;   -- sobrecarga: todas las evaluaciones pendientes
  FUNCTION  fn_pct_indicador (p_id_evaluacion IN NUMBER, p_id_indicador IN NUMBER) RETURN NUMBER;
END pkg_resultados;
/

-- 4.3 Función con parámetros: nota en escala de 1,0 a 7,0 según el % de logro.
--     Se usa en el package y en sentencias SQL.
CREATE OR REPLACE FUNCTION fn_calcular_nota (
  p_pct        IN NUMBER,
  p_exigencia  IN NUMBER DEFAULT pkg_resultados.c_exigencia
) RETURN NUMBER IS
  v_nota  NUMBER;
BEGIN
  IF p_pct < p_exigencia THEN
    v_nota := 1 + 3 * p_pct / p_exigencia;
  ELSE
    v_nota := 4 + 3 * (p_pct - p_exigencia) / (100 - p_exigencia);
  END IF;
  RETURN ROUND(v_nota, 1);
END fn_calcular_nota;
/

-- 4.4 Función sin parámetros: evaluaciones aplicadas que esperan proceso.
CREATE OR REPLACE FUNCTION fn_evaluaciones_pendientes RETURN NUMBER IS
  v_total  NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_total
    FROM evaluacion
   WHERE estado = 'APLICADA';
  RETURN v_total;
END fn_evaluaciones_pendientes;
/

-- 4.5 Cuerpo del package: implementación y constructores privados.
CREATE OR REPLACE PACKAGE BODY pkg_resultados IS

  -- constructores privados -------------------------------------------
  TYPE t_umbrales IS VARRAY(2) OF NUMBER(3);
  TYPE t_niveles  IS VARRAY(3) OF VARCHAR2(25);
  v_umbrales  t_umbrales;   -- % mínimo de cada nivel superior
  v_niveles   t_niveles;    -- nombre de cada nivel de logro

  e_evaluacion_invalida  EXCEPTION;
  e_hoja_sin_corregir    EXCEPTION;

  PROCEDURE sp_validar_evaluacion (p_id_evaluacion IN NUMBER) IS
    v_estado  evaluacion.estado%TYPE;
  BEGIN
    SELECT estado INTO v_estado
      FROM evaluacion
     WHERE id_evaluacion = p_id_evaluacion;
    IF v_estado NOT IN ('APLICADA', 'CERRADA') THEN
      RAISE e_evaluacion_invalida;     -- borrador o publicada: aún no hay hojas
    END IF;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RAISE e_evaluacion_invalida;     -- la evaluación no existe
  END sp_validar_evaluacion;

  FUNCTION fn_nivel_logro (p_pct IN NUMBER) RETURN VARCHAR2 IS
    v_nivel  VARCHAR2(25) := v_niveles(1);
  BEGIN
    FOR i IN 1 .. v_umbrales.COUNT LOOP
      IF p_pct >= v_umbrales(i) THEN
        v_nivel := v_niveles(i + 1);
      END IF;
    END LOOP;
    RETURN v_nivel;
  END fn_nivel_logro;

  -- constructores públicos -------------------------------------------
  PROCEDURE sp_procesar (p_id_evaluacion IN NUMBER) IS
    CURSOR c_hojas (p_id_eval NUMBER) IS
      SELECT h.id_hoja, h.id_estudiante, h.estado
        FROM hoja_respuesta h
       WHERE h.id_evaluacion = p_id_eval
       ORDER BY h.id_estudiante;

    CURSOR c_indicadores (p_id_eval NUMBER, p_id_hoja NUMBER) IS
      SELECT p.id_indicador,
             SUM(CASE WHEN r.alternativa = p.alternativa_correcta
                      THEN p.puntaje ELSE 0 END)  AS obtenido,
             SUM(p.puntaje)                       AS posible
        FROM pregunta p
        LEFT JOIN respuesta r
               ON r.id_pregunta = p.id_pregunta
              AND r.id_hoja = p_id_hoja
       WHERE p.id_evaluacion = p_id_eval
       GROUP BY p.id_indicador
       ORDER BY p.id_indicador;

    CURSOR c_agregado (p_id_eval NUMBER) IS
      SELECT id_indicador, COUNT(*) AS estudiantes,
             SUM(puntaje_obtenido) AS obtenido, SUM(puntaje_total) AS posible
        FROM logro_estudiante_indicador
       WHERE id_evaluacion = p_id_eval
       GROUP BY id_indicador
       ORDER BY id_indicador;

    TYPE t_total_eval IS RECORD (
      hojas     NUMBER := 0,
      suma_pct  NUMBER := 0,
      suma_nota NUMBER := 0
    );
    r_eval  t_total_eval;
    r_res   resultado_estudiante%ROWTYPE;
    r_vacio resultado_estudiante%ROWTYPE;
    r_lei   logro_estudiante_indicador%ROWTYPE;
    r_li    logro_indicador%ROWTYPE;
  BEGIN
    sp_validar_evaluacion(p_id_evaluacion);
    DELETE FROM logro_estudiante_indicador WHERE id_evaluacion = p_id_evaluacion;
    DELETE FROM logro_indicador WHERE id_evaluacion = p_id_evaluacion;

    FOR reg_hoja IN c_hojas(p_id_evaluacion) LOOP                     -- loop: hojas
      SAVEPOINT sp_hoja;
      BEGIN
        IF reg_hoja.estado <> 'CORREGIDA' THEN
          RAISE e_hoja_sin_corregir;
        END IF;

        r_res                  := r_vacio;
        r_res.id_evaluacion    := p_id_evaluacion;
        r_res.id_estudiante    := reg_hoja.id_estudiante;
        r_res.puntaje_obtenido := 0;
        r_res.puntaje_total    := 0;

        FOR reg_ind IN c_indicadores(p_id_evaluacion, reg_hoja.id_hoja) LOOP  -- loop anidado: indicadores
          r_lei.id_evaluacion    := p_id_evaluacion;
          r_lei.id_estudiante    := reg_hoja.id_estudiante;
          r_lei.id_indicador     := reg_ind.id_indicador;
          r_lei.puntaje_obtenido := reg_ind.obtenido;
          r_lei.puntaje_total    := reg_ind.posible;
          r_lei.pct_logro        := ROUND(reg_ind.obtenido / reg_ind.posible * 100, 1);
          r_lei.nivel_logro      := fn_nivel_logro(r_lei.pct_logro);
          INSERT INTO logro_estudiante_indicador VALUES r_lei;

          r_res.puntaje_obtenido := r_res.puntaje_obtenido + reg_ind.obtenido;
          r_res.puntaje_total    := r_res.puntaje_total + reg_ind.posible;
        END LOOP;

        r_res.pct_logro     := ROUND(r_res.puntaje_obtenido / r_res.puntaje_total * 100, 1);
        r_res.nota          := fn_calcular_nota(r_res.puntaje_obtenido / r_res.puntaje_total * 100);
        r_res.nivel_logro   := fn_nivel_logro(r_res.pct_logro);
        r_res.fecha_proceso := SYSDATE;

        BEGIN
          INSERT INTO resultado_estudiante VALUES r_res;
        EXCEPTION
          WHEN DUP_VAL_ON_INDEX THEN     -- re-proceso: se reemplaza el resultado
            UPDATE resultado_estudiante
               SET ROW = r_res
             WHERE id_evaluacion = p_id_evaluacion
               AND id_estudiante = reg_hoja.id_estudiante;
        END;

        r_eval.hojas     := r_eval.hojas + 1;
        r_eval.suma_pct  := r_eval.suma_pct + r_res.pct_logro;
        r_eval.suma_nota := r_eval.suma_nota + r_res.nota;
        g_hojas_procesadas := g_hojas_procesadas + 1;

      EXCEPTION
        WHEN e_hoja_sin_corregir THEN
          g_hojas_omitidas := g_hojas_omitidas + 1;
          sp_registra_error('PKG_RESULTADOS.SP_PROCESAR',
            'Evaluación ' || p_id_evaluacion || ': hoja ' || reg_hoja.id_hoja || ' del estudiante '
            || reg_hoja.id_estudiante || ' en estado ' || reg_hoja.estado || ', requiere nueva foto.');
        WHEN OTHERS THEN               -- un error en una hoja no detiene el proceso
          ROLLBACK TO sp_hoja;         -- deshace lo que alcanzó a grabar esa hoja
          g_hojas_omitidas := g_hojas_omitidas + 1;
          sp_registra_error('PKG_RESULTADOS.SP_PROCESAR',
            'Evaluación ' || p_id_evaluacion || ', hoja ' || reg_hoja.id_hoja || ': ' || SQLERRM);
      END;
    END LOOP;

    -- logro del curso por indicador (reporte de UTP, RN-2)
    FOR reg_agr IN c_agregado(p_id_evaluacion) LOOP
      r_li.id_evaluacion     := p_id_evaluacion;
      r_li.id_indicador      := reg_agr.id_indicador;
      r_li.total_estudiantes := reg_agr.estudiantes;
      r_li.puntaje_obtenido  := reg_agr.obtenido;
      r_li.puntaje_total     := reg_agr.posible;
      r_li.pct_logro         := ROUND(reg_agr.obtenido / reg_agr.posible * 100, 1);
      r_li.nivel_logro       := fn_nivel_logro(r_li.pct_logro);
      INSERT INTO logro_indicador VALUES r_li;
    END LOOP;

    UPDATE evaluacion SET estado = 'CERRADA' WHERE id_evaluacion = p_id_evaluacion;
    COMMIT;

    IF r_eval.hojas > 0 THEN
      DBMS_OUTPUT.PUT_LINE('Evaluación ' || p_id_evaluacion || ': ' || r_eval.hojas || ' hojas · logro '
        || TO_CHAR(ROUND(r_eval.suma_pct / r_eval.hojas, 1), 'FM990D0') || '% · nota promedio '
        || TO_CHAR(ROUND(r_eval.suma_nota / r_eval.hojas, 1), 'FM0D0'));
    END IF;
  EXCEPTION
    WHEN e_evaluacion_invalida THEN
      sp_registra_error('PKG_RESULTADOS.SP_PROCESAR', 'Evaluación no procesable: ' || p_id_evaluacion);
      RAISE_APPLICATION_ERROR(-20010, 'La evaluación ' || p_id_evaluacion
                              || ' no existe o aún no tiene hojas aplicadas.');
  END sp_procesar;

  PROCEDURE sp_procesar IS
    CURSOR c_pendientes IS
      SELECT id_evaluacion
        FROM evaluacion
       WHERE estado = 'APLICADA'
       ORDER BY id_evaluacion;
  BEGIN
    g_hojas_procesadas := 0;
    g_hojas_omitidas   := 0;
    FOR reg_ev IN c_pendientes LOOP                                    -- loop externo: evaluaciones
      sp_procesar(reg_ev.id_evaluacion);
    END LOOP;
    DBMS_OUTPUT.PUT_LINE('Hojas procesadas: ' || g_hojas_procesadas
                         || ' · hojas omitidas: ' || g_hojas_omitidas);
  END sp_procesar;

  FUNCTION fn_pct_indicador (p_id_evaluacion IN NUMBER, p_id_indicador IN NUMBER) RETURN NUMBER IS
    v_pct  logro_indicador.pct_logro%TYPE;
  BEGIN
    SELECT pct_logro
      INTO v_pct
      FROM logro_indicador
     WHERE id_evaluacion = p_id_evaluacion
       AND id_indicador = p_id_indicador;
    RETURN v_pct;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RETURN NULL;                     -- indicador sin resultados en esa evaluación
  END fn_pct_indicador;

BEGIN
  -- inicialización del package: niveles de logro del colegio
  v_umbrales := t_umbrales(60, 80);
  v_niveles  := t_niveles('POR LOGRAR', 'MEDIANAMENTE LOGRADO', 'LOGRADO');
END pkg_resultados;
/

-- 4.6 Procedimiento con parámetros: resumen mensual por curso y asignatura.
CREATE OR REPLACE PROCEDURE sp_resumen_cursos (p_periodo IN VARCHAR2) IS
  CURSOR c_cursos IS
    SELECT id_curso, nivel, letra
      FROM curso
     ORDER BY id_curso;

  CURSOR c_asignaturas (p_id_curso NUMBER, p_per VARCHAR2) IS
    SELECT e.id_asignatura,
           COUNT(DISTINCT e.id_evaluacion)               AS evaluaciones,
           COUNT(*)                                      AS resultados,
           ROUND(AVG(r.pct_logro), 1)                    AS pct_promedio,
           ROUND(AVG(r.nota), 1)                         AS nota_promedio,
           SUM(CASE WHEN r.nota < 4 THEN 1 ELSE 0 END)   AS bajo_4
      FROM resultado_estudiante r
      JOIN evaluacion e ON e.id_evaluacion = r.id_evaluacion
     WHERE e.id_curso = p_id_curso
       AND TO_CHAR(e.fecha_aplicacion, 'YYYYMM') = p_per
     GROUP BY e.id_asignatura
     ORDER BY e.id_asignatura;

  TYPE t_menor IS RECORD (
    curso       VARCHAR2(30),
    asignatura  asignatura.id_asignatura%TYPE,
    pct         NUMBER := 101
  );
  r_menor       t_menor;
  r_resumen     resumen_curso_mes%ROWTYPE;
  v_total       NUMBER := 0;
  e_sin_resultados EXCEPTION;
BEGIN
  DELETE FROM resumen_curso_mes WHERE periodo = p_periodo;

  FOR reg_cur IN c_cursos LOOP                                       -- loop: cursos
    FOR reg_asig IN c_asignaturas(reg_cur.id_curso, p_periodo) LOOP  -- loop anidado: asignaturas
      r_resumen.periodo            := p_periodo;
      r_resumen.id_curso           := reg_cur.id_curso;
      r_resumen.id_asignatura      := reg_asig.id_asignatura;
      r_resumen.total_evaluaciones := reg_asig.evaluaciones;
      r_resumen.total_resultados   := reg_asig.resultados;
      r_resumen.pct_logro_promedio := reg_asig.pct_promedio;
      r_resumen.nota_promedio      := reg_asig.nota_promedio;
      r_resumen.estudiantes_bajo_4 := reg_asig.bajo_4;
      INSERT INTO resumen_curso_mes VALUES r_resumen;
      v_total := v_total + 1;
      IF reg_asig.pct_promedio < r_menor.pct THEN
        r_menor.curso      := reg_cur.nivel || ' ' || reg_cur.letra;
        r_menor.asignatura := reg_asig.id_asignatura;
        r_menor.pct        := reg_asig.pct_promedio;
      END IF;
    END LOOP;
  END LOOP;

  IF v_total = 0 THEN
    RAISE e_sin_resultados;
  END IF;
  COMMIT;
  DBMS_OUTPUT.PUT_LINE('Menor logro en ' || p_periodo || ': ' || r_menor.curso || ' · '
                       || r_menor.asignatura || ' (' || TO_CHAR(r_menor.pct, 'FM990D0') || '%)');
EXCEPTION
  WHEN e_sin_resultados THEN
    ROLLBACK;
    sp_registra_error('SP_RESUMEN_CURSOS',
                      'Periodo ' || p_periodo || ' sin resultados procesados: no se generó resumen.');
END sp_resumen_cursos;
/

-- 4.7 Procedimiento sin parámetros: proceso nocturno completo. Es el que
--     se programa como job todas las noches.
CREATE OR REPLACE PROCEDURE sp_proceso_nocturno IS
BEGIN
  IF fn_evaluaciones_pendientes = 0 THEN
    DBMS_OUTPUT.PUT_LINE('No hay evaluaciones pendientes.');
    RETURN;
  END IF;
  UPDATE parametro_proceso SET valor = 'S' WHERE nombre = 'PROCESO_EN_CURSO';
  COMMIT;

  pkg_resultados.sp_procesar;
  sp_resumen_cursos(TO_CHAR(SYSDATE, 'YYYYMM'));

  UPDATE parametro_proceso SET valor = 'N' WHERE nombre = 'PROCESO_EN_CURSO';
  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    UPDATE parametro_proceso SET valor = 'N' WHERE nombre = 'PROCESO_EN_CURSO';
    COMMIT;
    sp_registra_error('SP_PROCESO_NOCTURNO', SQLERRM);
    RAISE;
END sp_proceso_nocturno;
/

-- 2.1 Nivel de fila, BEFORE: valida que el estudiante esté activo y
--     pertenezca al curso de la evaluación, y genera el código QR (RF-7).
CREATE OR REPLACE TRIGGER trg_hoja_valida
BEFORE INSERT ON hoja_respuesta
FOR EACH ROW
DECLARE
  v_curso_est   estudiante.id_curso%TYPE;
  v_estado_est  estudiante.estado%TYPE;
  v_curso_eval  evaluacion.id_curso%TYPE;
BEGIN
  BEGIN
    SELECT id_curso, estado INTO v_curso_est, v_estado_est
      FROM estudiante
     WHERE id_estudiante = :NEW.id_estudiante;
    SELECT id_curso INTO v_curso_eval
      FROM evaluacion
     WHERE id_evaluacion = :NEW.id_evaluacion;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20001, 'Hoja ' || :NEW.id_hoja
                              || ': el estudiante o la evaluación no existe.');
  END;
  IF v_estado_est = 'RETIRADO' THEN
    RAISE_APPLICATION_ERROR(-20002, 'El estudiante ' || :NEW.id_estudiante || ' está retirado.');
  END IF;
  IF v_curso_est <> v_curso_eval THEN
    RAISE_APPLICATION_ERROR(-20003, 'El estudiante ' || :NEW.id_estudiante
                            || ' no pertenece al curso de la evaluación ' || :NEW.id_evaluacion || '.');
  END IF;
  -- código QR único: evaluación + estudiante
  :NEW.codigo_qr := 'EVAI-' || LPAD(:NEW.id_evaluacion, 6, '0') || '-' || LPAD(:NEW.id_estudiante, 6, '0');
END trg_hoja_valida;
/

-- 2.2 Nivel de fila, AFTER: una hoja corregida deja la evaluación como
--     APLICADA, es decir, pendiente de procesar (también si ya estaba CERRADA).
CREATE OR REPLACE TRIGGER trg_hoja_evaluacion
AFTER INSERT OR UPDATE OF estado ON hoja_respuesta
FOR EACH ROW
WHEN (NEW.estado = 'CORREGIDA')
BEGIN
  UPDATE evaluacion
     SET estado = 'APLICADA'
   WHERE id_evaluacion = :NEW.id_evaluacion
     AND estado IN ('PUBLICADA', 'CERRADA');
END trg_hoja_evaluacion;
/

-- 2.3 Nivel de fila, BEFORE: normaliza la alternativa leída por la IA y
--     verifica que la pregunta sea de la misma evaluación que la hoja.
CREATE OR REPLACE TRIGGER trg_respuesta_valida
BEFORE INSERT OR UPDATE ON respuesta
FOR EACH ROW
DECLARE
  v_eval_hoja      hoja_respuesta.id_evaluacion%TYPE;
  v_eval_pregunta  pregunta.id_evaluacion%TYPE;
BEGIN
  :NEW.alternativa := UPPER(TRIM(:NEW.alternativa));
  IF :NEW.alternativa IS NOT NULL AND :NEW.alternativa NOT IN ('A','B','C','D') THEN
    RAISE_APPLICATION_ERROR(-20004, 'Alternativa no válida: ' || :NEW.alternativa);
  END IF;
  SELECT id_evaluacion INTO v_eval_hoja FROM hoja_respuesta WHERE id_hoja = :NEW.id_hoja;
  SELECT id_evaluacion INTO v_eval_pregunta FROM pregunta WHERE id_pregunta = :NEW.id_pregunta;
  IF v_eval_hoja <> v_eval_pregunta THEN
    RAISE_APPLICATION_ERROR(-20005, 'La pregunta ' || :NEW.id_pregunta
                            || ' no pertenece a la evaluación de la hoja ' || :NEW.id_hoja || '.');
  END IF;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20006, 'La hoja ' || :NEW.id_hoja || ' o la pregunta '
                            || :NEW.id_pregunta || ' no existe.');
END trg_respuesta_valida;
/

-- 2.4 Nivel de fila, AFTER, con WHEN: si el docente corrige la clave de una
--     pregunta, se audita el cambio y la evaluación vuelve a quedar pendiente.
CREATE OR REPLACE TRIGGER trg_pregunta_audita
AFTER UPDATE OF alternativa_correcta ON pregunta
FOR EACH ROW
WHEN (NEW.alternativa_correcta <> OLD.alternativa_correcta)
BEGIN
  INSERT INTO auditoria_pregunta
  VALUES (seq_auditoria.NEXTVAL, :OLD.id_pregunta, :OLD.alternativa_correcta,
          :NEW.alternativa_correcta, USER, SYSDATE);
  UPDATE evaluacion
     SET estado = 'APLICADA'
   WHERE id_evaluacion = :NEW.id_evaluacion
     AND estado = 'CERRADA';
END trg_pregunta_audita;
/

-- 2.5 Nivel de sentencia, BEFORE: impide modificar preguntas mientras corre
--     el proceso nocturno de resultados. Se dispara una vez por sentencia.
CREATE OR REPLACE TRIGGER trg_pregunta_bloqueo
BEFORE INSERT OR UPDATE OR DELETE ON pregunta
DECLARE
  v_en_curso  parametro_proceso.valor%TYPE;
BEGIN
  SELECT valor INTO v_en_curso
    FROM parametro_proceso
   WHERE nombre = 'PROCESO_EN_CURSO';
  IF v_en_curso = 'S' THEN
    RAISE_APPLICATION_ERROR(-20020,
      'No se pueden modificar preguntas mientras se procesan los resultados.');
  END IF;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    NULL;  -- si el parámetro no existe, no hay proceso en curso
END trg_pregunta_bloqueo;
/

-- 2.6 Nivel de sentencia, AFTER: deja en bitácora quién modificó las notas
--     (datos personales de estudiantes, RNF-3).
CREATE OR REPLACE TRIGGER trg_resultado_bitacora
AFTER INSERT OR UPDATE OR DELETE ON resultado_estudiante
DECLARE
  v_operacion  bitacora_operacion.operacion%TYPE;
BEGIN
  IF INSERTING THEN
    v_operacion := 'INSERT';
  ELSIF UPDATING THEN
    v_operacion := 'UPDATE';
  ELSE
    v_operacion := 'DELETE';
  END IF;
  INSERT INTO bitacora_operacion
  VALUES (seq_bitacora.NEXTVAL, 'RESULTADO_ESTUDIANTE', v_operacion, USER, SYSDATE);
END trg_resultado_bitacora;
/
