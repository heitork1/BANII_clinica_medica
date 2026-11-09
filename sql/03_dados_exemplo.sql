-- Dados de exemplo para testar todas as telas do sistema.
-- Execute por último (depois de 01_esquema.sql e 02_funcoes_gatilhos.sql), UMA vez, num banco recém-criado:
-- os números dos registros (ids) dependem da ordem em que são inseridos.
-- Para recomeçar do zero, rode antes este comando (apaga tudo e zera os contadores):
--   TRUNCATE usuario, pagamento, consulta_procedimento, consulta, conta, horario_medico,
--            medico_especialidade, telefone_medico, medico, horario, plano_convenio, telefone_paciente,
--            paciente, convenio, procedimento, especialidade, sala RESTART IDENTITY CASCADE;
--
-- Logins para testar (senha de todos: 123456):
--   admin@admin.com      administrador (vê todas as abas)
--   medico@medico.com    Dr. Carlos Almeida (vê só Início, Consultas e Pacientes; só as consultas dele)
--   fernanda@medico.com  Dra. Fernanda Lima
--   inativo@medico.com   usuário desativado (deve recusar o login)


-- 1) Cadastros de apoio ------------------------------------------------------------------------
INSERT INTO sala (descricao) VALUES
    ('Sala 1 - Clínica Geral'), ('Sala 2 - Procedimentos'), ('Sala 3 - Pediatria'), ('Sala 4 - Dermatologia');

INSERT INTO especialidade (nome_especialidade) VALUES
    ('Clínica Geral'), ('Cardiologia'), ('Pediatria'), ('Dermatologia');

INSERT INTO convenio (nome) VALUES ('Unimed'), ('Bradesco Saúde'), ('Amil');

-- ids: 1 Eletrocardiograma, 2 Curativo, 3 Ecocardiograma, 4 Retirada de pontos,
--      5 Biópsia de pele, 6 Teste de alergia, 7 Aplicação de vacina
INSERT INTO procedimento (descricao, valor) VALUES
    ('Eletrocardiograma', 80.00),
    ('Curativo', 30.00),
    ('Ecocardiograma', 220.00),
    ('Retirada de pontos', 45.00),
    ('Biópsia de pele', 350.00),
    ('Teste de alergia', 150.00),
    ('Aplicação de vacina', 60.00);


-- 2) Horários de atendimento -------------------------------------------------------------------
-- dia_semana em maiúsculas e sem acento (exigência do gatilho de horário).
-- ids 1 a 10: segunda a sexta, 08:00-12:00 e 14:00-18:00
INSERT INTO horario (hora_inicio, hora_fim, dia_semana)
SELECT h.i, h.f, d FROM (VALUES ('08:00'::time,'12:00'::time), ('14:00'::time,'18:00'::time)) AS h(i,f),
     unnest(ARRAY['SEGUNDA','TERCA','QUARTA','QUINTA','SEXTA']) AS d;

-- ids 11 a 14: sábado e domingo (para os médicos de plantão)
INSERT INTO horario (hora_inicio, hora_fim, dia_semana)
SELECT h.i, h.f, d FROM (VALUES ('08:00'::time,'12:00'::time), ('14:00'::time,'18:00'::time)) AS h(i,f),
     unnest(ARRAY['SABADO','DOMINGO']) AS d;


-- 3) Médicos -----------------------------------------------------------------------------------
INSERT INTO medico (nome_medico, percentual_honorario, crm) VALUES
    ('Dr. Carlos Almeida', 30.00, 'CRM-SP 123456'),    -- id 1, Clínica Geral
    ('Dra. Fernanda Lima', 35.00, 'CRM-SP 234567'),    -- id 2, Cardiologia
    ('Dr. Paulo Mendes', 30.00, 'CRM-SP 345678'),      -- id 3, Pediatria
    ('Dra. Juliana Rocha', 40.00, 'CRM-SP 456789');    -- id 4, Dermatologia

INSERT INTO telefone_medico (numero_telefone, id_medico) VALUES
    ('(11) 99999-0001', 1), ('(11) 99999-0002', 2), ('(11) 99999-0003', 3), ('(11) 99999-0004', 4);

INSERT INTO medico_especialidade (id_medico, id_especialidade) VALUES (1, 1), (2, 2), (3, 3), (4, 4);

-- Médicos 1 e 2 atendem todos os dias (assim a tela inicial mostra consultas de hoje em qualquer dia).
INSERT INTO horario_medico (id_medico, id_horario)
SELECT m.id_medico, h.id_horario FROM medico m, horario h WHERE m.id_medico IN (1, 2);

-- Médico 3: segunda a sexta, só de manhã.
INSERT INTO horario_medico (id_medico, id_horario)
SELECT 3, id_horario FROM horario
WHERE hora_inicio = '08:00' AND dia_semana IN ('SEGUNDA','TERCA','QUARTA','QUINTA','SEXTA');

-- Médico 4: terça e quinta, só de tarde.
INSERT INTO horario_medico (id_medico, id_horario)
SELECT 4, id_horario FROM horario
WHERE hora_inicio = '14:00' AND dia_semana IN ('TERCA','QUINTA');


-- 4) Usuários (login) --------------------------------------------------------------------------
INSERT INTO usuario (nome, email, senha_hash, perfil, ativo, id_medico) VALUES
    ('Administrador', 'admin@admin.com', '123456', 'ADMIN', TRUE, NULL),
    ('Dr. Carlos Almeida', 'medico@medico.com', '123456', 'MEDICO', TRUE, 1),
    ('Dra. Fernanda Lima', 'fernanda@medico.com', '123456', 'MEDICO', TRUE, 2),
    ('Dr. Paulo Mendes', 'inativo@medico.com', '123456', 'MEDICO', FALSE, 3);


-- 5) Pacientes ---------------------------------------------------------------------------------
INSERT INTO paciente (nome, data_nasc, cpf, rg, sexo, endereco, "e-mail") VALUES
    ('Maria Silva Santos', '1985-03-12', '529.982.247-25', '12.345.678-9', 'Feminino', 'Rua das Flores, 100 - São Paulo', 'maria@email.com'),
    ('João Pedro Oliveira', '1978-07-25', '111.444.777-35', '23.456.789-0', 'Masculino', 'Av. Brasil, 250 - São Paulo', 'joao@email.com'),
    ('Ana Beatriz Costa', '1992-11-02', '390.533.447-05', '34.567.890-1', 'Feminino', 'Rua do Sol, 45 - Campinas', 'ana@email.com'),
    ('Carlos Eduardo Pereira', '1960-01-30', '123.456.789-09', '45.678.901-2', 'Masculino', 'Rua Verde, 12 - Santos', 'carlos.pereira@email.com'),
    ('Luiza Fernandes', '2018-05-14', '987.654.321-00', '56.789.012-3', 'Feminino', 'Rua Azul, 78 - São Paulo', 'responsavel.luiza@email.com'),
    ('Rafael Gomes', '2015-09-08', '452.861.930-05', '67.890.123-4', 'Masculino', 'Rua Amarela, 33 - Osasco', 'responsavel.rafael@email.com'),
    ('Patrícia Almeida', '1988-12-19', '275.184.630-08', '78.901.234-5', 'Feminino', 'Av. Paulista, 900 - São Paulo', 'patricia@email.com'),
    ('Roberto Martins', '1955-04-03', '836.420.915-98', '89.012.345-6', 'Masculino', 'Rua da Paz, 60 - Guarulhos', 'roberto@email.com');

INSERT INTO telefone_paciente (numero_telefone, id_paciente) VALUES
    ('(11) 98765-4321', 1), ('(11) 91234-5678', 1),
    ('(11) 98888-1111', 2),
    ('(19) 97777-2222', 3),
    ('(13) 96666-3333', 4),
    ('(11) 95555-4444', 5),
    ('(11) 94444-5555', 6),
    ('(11) 93333-6666', 7), ('(11) 92222-7777', 7),
    ('(11) 91111-8888', 8);

-- Carteirinhas de convênio. Ana (3) está vencida; Luiza (5) não tem validade (conta como válida).
-- Carlos (4), Rafael (6) e Roberto (8) são particulares.
INSERT INTO plano_convenio (id_paciente, id_convenio, numero_carteirinha, validade, tipo_plano) VALUES
    (1, 1, '0012345678', '2028-12-31', 'Básico'),
    (2, 2, '9876543210', '2028-06-30', 'Premium'),
    (3, 1, '0055512345', '2025-08-31', 'Básico'),
    (5, 1, '0077788899', NULL, 'Familiar'),
    (7, 2, '1122334455', '2028-12-31', 'Executivo');


-- 6) Consultas já realizadas, cada uma com a sua conta -----------------------------------------
-- As contas nascem com valor_procedimento 0; o gatilho 3 recalcula quando os procedimentos entram (passo 7).
-- Contas 1 a 4, na ordem das consultas realizadas 1 a 4.
INSERT INTO conta (valor_procedimento, valor_consulta) VALUES
    (0, 200.00), (0, 300.00), (0, 200.00), (0, 180.00);

-- Datas fixas no passado, em dias e horários em que o médico atende.
INSERT INTO consulta (data_hora_marcado, data_hora_realizado, status, sintomas, diagnostico, prescricao,
                      id_paciente, id_medico, id_sala, id_conta) VALUES
    ('2026-10-26 09:00', '2026-10-26 09:10', 'REALIZADA', 'Dor leve no peito e cansaço', 'Ansiedade, sem alteração no ECG', 'Repouso e retorno em 30 dias', 1, 1, 1, 1),
    ('2026-10-27 14:00', '2026-10-27 14:05', 'REALIZADA', 'Falta de ar ao subir escadas', 'Insuficiência cardíaca leve', 'Losartana 50 mg, 1 vez ao dia', 2, 2, 2, 2),
    ('2026-10-28 10:00', '2026-10-28 10:15', 'REALIZADA', 'Corte profundo na mão', 'Ferimento corto-contuso', 'Limpar e trocar o curativo a cada 2 dias', 4, 1, 1, 3),
    ('2026-10-29 09:00', '2026-10-29 09:20', 'REALIZADA', 'Vacinação em dia', 'Criança saudável', 'Vacina aplicada, retorno em 6 meses', 5, 3, 3, 4);


-- 7) Procedimentos realizados nessas consultas -------------------------------------------------
-- valor_unitario é o preço da época (fica congelado mesmo que o cadastro mude depois).
INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario) VALUES
    (1, 1, 1, 80.00),     -- Eletrocardiograma
    (2, 3, 1, 220.00),    -- Ecocardiograma
    (2, 1, 1, 80.00),     -- Eletrocardiograma
    (3, 2, 2, 30.00),     -- Curativo x2
    (4, 7, 2, 60.00);     -- Aplicação de vacina x2


-- 8) Pagamentos --------------------------------------------------------------------------------
-- Resultado nas telas Contas e Pagamentos:
--   Quitada:   conta 1
--   Parcial:   conta 2
--   Em aberto: contas 3 e 4 (sem pagamento: servem para testar o botão Novo Pagamento)
-- Pagamento com convênio: possui_convenio TRUE e valor_convenio preenchido.
INSERT INTO pagamento (data_pagamento, valor_pago, forma_pagamento, possui_convenio, valor_convenio, id_conta) VALUES
    ('2026-10-26', 80.00, 'CARTAO', FALSE, 0, 1),
    ('2026-10-26', 0.00, 'PIX', TRUE, 200.00, 1),
    ('2026-10-27', 0.00, 'PIX', TRUE, 300.00, 2);


-- 9) Outras consultas (sem conta: ela só nasce quando a consulta é finalizada) -----------------
-- Consultas de hoje, para a tela inicial. Os médicos 1 e 2 atendem todos os dias.
INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala) VALUES
    (CURRENT_DATE + TIME '09:00', 'CONFIRMADA', 4, 1, 1),
    (CURRENT_DATE + TIME '14:00', 'AGENDADA',   1, 1, 1),
    (CURRENT_DATE + TIME '16:00', 'CANCELADA',  7, 1, 1),
    (CURRENT_DATE + TIME '09:30', 'AGENDADA',   2, 2, 2);

-- Consultas na semana que vem (segunda e terça), em dias e horários em que cada médico atende.
INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala) VALUES
    (date_trunc('week', CURRENT_DATE::timestamp) + INTERVAL '7 days 8 hours 30 minutes',  'AGENDADA', 5, 3, 3),  -- segunda
    (date_trunc('week', CURRENT_DATE::timestamp) + INTERVAL '8 days 14 hours 30 minutes', 'AGENDADA', 7, 4, 4);  -- terça

-- Consulta passada ainda como agendada (serve para testar o botão Aplicar com o status REALIZADA).
INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala) VALUES
    ('2026-11-05 11:00', 'AGENDADA', 7, 1, 1);
