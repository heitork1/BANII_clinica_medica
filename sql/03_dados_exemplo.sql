--dados para testar o login

INSERT INTO medico (nome_medico, percentual_honorario, crm)
VALUES ('MédicoA', 25, '12345678');

INSERT INTO usuario values ('1','admin', 'admin@admin.com', '123456', 'ADMIN', 'TRUE')

INSERT INTO usuario values ('2', 'medico', 'medico@medico.com', '123456', 'MEDICO', 'TRUE', 1)


-- Dados de apoio para testar a aplicação (executar por último).
INSERT INTO sala (descricao) VALUES ('Sala 1 - Clínica Geral'), ('Sala 2 - Procedimentos'), ('Sala 3 - Pediatria');
INSERT INTO especialidade (nome_especialidade) VALUES ('Clínica Geral'), ('Cardiologia'), ('Pediatria'), ('Dermatologia');
INSERT INTO convenio (nome) VALUES ('Unimed'), ('Bradesco Saúde');
INSERT INTO procedimento (descricao, valor) VALUES ('Eletrocardiograma', 80.00), ('Curativo', 30.00);
-- dia_semana em maiúsculas e sem acento (exigência do gatilho de horário)
INSERT INTO horario (hora_inicio, hora_fim, dia_semana)
SELECT h.i, h.f, d FROM (VALUES ('08:00'::time,'12:00'::time), ('14:00'::time,'18:00'::time)) AS h(i,f),
     unnest(ARRAY['SEGUNDA','TERCA','QUARTA','QUINTA','SEXTA']) AS d;
