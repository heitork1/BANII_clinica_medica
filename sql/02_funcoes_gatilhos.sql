--ETAPA 3 GATILHOS E FUNÇÕES

CREATE OR REPLACE FUNCTION fn_valida_conflito_agenda()
RETURNS TRIGGER AS $$
BEGIN
    -- Ignora consultas canceladas
    IF NEW.status = 'CANCELADA' THEN
        RETURN NEW;
    END IF;

    -- Conflito de médico
    IF EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_medico = NEW.id_medico
          AND c.data_hora_marcado = NEW.data_hora_marcado
          AND c.status <> 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION 'O médico % já possui consulta marcada em %.',
            NEW.id_medico, NEW.data_hora_marcado;
    END IF;

    -- Conflito de sala
    IF NEW.id_sala IS NOT NULL AND EXISTS (
        SELECT 1 FROM consulta c
        WHERE c.id_sala = NEW.id_sala
          AND c.data_hora_marcado = NEW.data_hora_marcado
          AND c.status <> 'CANCELADA'
          AND c.id_consulta <> COALESCE(NEW.id_consulta, -1)
    ) THEN
        RAISE EXCEPTION 'A sala % já está ocupada em %.',
            NEW.id_sala, NEW.data_hora_marcado;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_valida_conflito_agenda
BEFORE INSERT OR UPDATE OF data_hora_marcado, id_medico, id_sala, status
ON consulta
FOR EACH ROW
EXECUTE FUNCTION fn_valida_conflito_agenda();

CREATE OR REPLACE FUNCTION fn_valida_horario_medico()
RETURNS TRIGGER AS $$
DECLARE
    v_dia_semana TEXT;
    v_hora       TIME;
BEGIN
    IF NEW.status = 'CANCELADA' THEN
        RETURN NEW;
    END IF;

    v_dia_semana := CASE EXTRACT(DOW FROM NEW.data_hora_marcado)::INT
        WHEN 0 THEN 'DOMINGO'
        WHEN 1 THEN 'SEGUNDA'
        WHEN 2 THEN 'TERCA'
        WHEN 3 THEN 'QUARTA'
        WHEN 4 THEN 'QUINTA'
        WHEN 5 THEN 'SEXTA'
        WHEN 6 THEN 'SABADO'
    END;
    v_hora := NEW.data_hora_marcado::TIME;

    IF NOT EXISTS (
        SELECT 1
        FROM horario_medico hm
        JOIN horario h ON h.id_horario = hm.id_horario
        WHERE hm.id_medico = NEW.id_medico
          AND UPPER(h.dia_semana) = v_dia_semana
          AND v_hora >= h.hora_inicio
          AND v_hora <  h.hora_fim
    ) THEN
        RAISE EXCEPTION 'O médico % não atende em % às %.',
            NEW.id_medico, v_dia_semana, v_hora;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_valida_horario_medico
BEFORE INSERT OR UPDATE OF data_hora_marcado, id_medico
ON consulta
FOR EACH ROW
EXECUTE FUNCTION fn_valida_horario_medico();


-- GATILHO 3: recalcula conta.valor_procedimento quando os procedimentos da consulta mudam.
CREATE OR REPLACE FUNCTION fn_atualiza_valor_procedimento_conta()
RETURNS TRIGGER AS $$
DECLARE
    v_consulta_old INTEGER;
    v_consulta_new INTEGER;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_consulta_old := OLD.id_consulta;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_consulta_new := NEW.id_consulta;
    END IF;

    UPDATE conta ct
    SET valor_procedimento = (
        SELECT COALESCE(SUM(cp.quantidade * COALESCE(cp.valor_unitario, p.valor)), 0)
        FROM consulta c
        JOIN consulta_procedimento cp ON cp.id_consulta = c.id_consulta
        JOIN procedimento p ON p.id_procedimento = cp.id_procedimento
        WHERE c.id_conta = ct.id_conta
    )
    WHERE ct.id_conta IN (
        SELECT id_conta
        FROM consulta
        WHERE id_consulta IN (v_consulta_old, v_consulta_new)
    );

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_atualiza_valor_procedimento_conta ON consulta_procedimento;
CREATE TRIGGER trg_atualiza_valor_procedimento_conta
AFTER INSERT OR UPDATE OR DELETE
ON consulta_procedimento
FOR EACH ROW
EXECUTE FUNCTION fn_atualiza_valor_procedimento_conta();


-- GATILHO 4:
CREATE OR REPLACE FUNCTION fn_valida_pagamento()
RETURNS TRIGGER AS $$
DECLARE
    v_total     NUMERIC(10,2);
    v_ja_pago   NUMERIC(10,2);
    v_paciente  INTEGER;
    v_data      DATE := COALESCE(NEW.data_pagamento, CURRENT_DATE);
BEGIN
    IF NEW.id_conta IS NULL THEN
        RAISE EXCEPTION 'O pagamento precisa estar ligado a uma conta.';
    END IF;

    IF COALESCE(NEW.valor_pago, 0) < 0 OR COALESCE(NEW.valor_convenio, 0) < 0 THEN
        RAISE EXCEPTION 'Os valores do pagamento não podem ser negativos.';
    END IF;

    IF COALESCE(NEW.valor_pago, 0) + COALESCE(NEW.valor_convenio, 0) <= 0 THEN
        RAISE EXCEPTION 'O pagamento precisa ter algum valor.';
    END IF;

    IF NOT COALESCE(NEW.possui_convenio, FALSE) AND COALESCE(NEW.valor_convenio, 0) <> 0 THEN
        RAISE EXCEPTION 'Valor do convênio informado em um pagamento sem convênio.';
    END IF;

    IF NEW.possui_convenio THEN
        SELECT c.id_paciente INTO v_paciente
        FROM consulta c
        WHERE c.id_conta = NEW.id_conta
        LIMIT 1;

        IF NOT EXISTS (
            SELECT 1 FROM plano_convenio pc
            WHERE pc.id_paciente = v_paciente
              AND (pc.validade IS NULL OR pc.validade >= v_data)
        ) THEN
            RAISE EXCEPTION 'O paciente não tem convênio com carteirinha válida em %.',
                to_char(v_data, 'DD/MM/YYYY');
        END IF;
    END IF;


    SELECT COALESCE(ct.valor_consulta, 0) + COALESCE(ct.valor_procedimento, 0)
      INTO v_total
      FROM conta ct
     WHERE ct.id_conta = NEW.id_conta
       FOR UPDATE;

    SELECT COALESCE(SUM(COALESCE(pg.valor_pago, 0) + COALESCE(pg.valor_convenio, 0)), 0)
      INTO v_ja_pago
      FROM pagamento pg
     WHERE pg.id_conta = NEW.id_conta
       AND pg.id_pagamento IS DISTINCT FROM NEW.id_pagamento;

    IF v_ja_pago + COALESCE(NEW.valor_pago, 0) + COALESCE(NEW.valor_convenio, 0) > v_total THEN
        RAISE EXCEPTION 'O pagamento passa do total da conta (total R$ %, já pago R$ %, saldo R$ %).',
            replace(to_char(v_total, 'FM99999990.00'), '.', ','),
            replace(to_char(v_ja_pago, 'FM99999990.00'), '.', ','),
            replace(to_char(v_total - v_ja_pago, 'FM99999990.00'), '.', ',');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_valida_pagamento ON pagamento;
CREATE TRIGGER trg_valida_pagamento
BEFORE INSERT OR UPDATE
ON pagamento
FOR EACH ROW
EXECUTE FUNCTION fn_valida_pagamento();
