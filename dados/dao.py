"""Camada de dados: acesso às tabelas (DAOs). Só SQL, sem regras de negócio."""
from .conexao import transacao


class PacienteDAO:
    def inserir(self, p):
        with transacao() as cur:
            cur.execute(
                'INSERT INTO paciente (nome, data_nasc, cpf, rg, sexo, endereco, "e-mail") '
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_paciente",
                (p.nome, p.data_nasc, p.cpf, p.rg, p.sexo, p.endereco, p.email))
            id_paciente = cur.fetchone()[0]
            for tel in p.telefones:
                cur.execute("INSERT INTO telefone_paciente (numero_telefone, id_paciente) VALUES (%s,%s)",
                            (tel, id_paciente))
            return id_paciente

    def listar(self, filtro=""):
        with transacao() as cur:
            cur.execute(
                'SELECT p.id_paciente, p.nome, p.cpf, p.data_nasc, p."e-mail", '
                "COALESCE((SELECT string_agg(t.numero_telefone, ', ') FROM telefone_paciente t "
                "WHERE t.id_paciente = p.id_paciente), '') "
                "FROM paciente p WHERE p.nome ILIKE %s OR p.cpf LIKE %s ORDER BY p.nome",
                (f"%{filtro}%", f"%{filtro}%"))
            return cur.fetchall()

    def existe_cpf(self, cpf):
        with transacao() as cur:
            cur.execute("SELECT 1 FROM paciente WHERE cpf = %s", (cpf,))
            return cur.fetchone() is not None

    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_paciente, nome FROM paciente ORDER BY nome")
            return cur.fetchall()


class MedicoDAO:
    def inserir(self, m):
        with transacao() as cur:
            cur.execute("INSERT INTO medico (nome_medico, percentual_honorario, crm) "
                        "VALUES (%s,%s,%s) RETURNING id_medico",
                        (m.nome, m.percentual, m.crm))
            id_medico = cur.fetchone()[0]
            if m.telefone:
                cur.execute("INSERT INTO telefone_medico (numero_telefone, id_medico) VALUES (%s,%s)",
                            (m.telefone, id_medico))
            for esp in m.especialidades:
                cur.execute("INSERT INTO medico_especialidade (id_medico, id_especialidade) VALUES (%s,%s)",
                            (id_medico, esp))
            for hor in m.horarios:
                cur.execute("INSERT INTO horario_medico (id_medico, id_horario) VALUES (%s,%s)",
                            (id_medico, hor))
            return id_medico

    def listar(self):
        with transacao() as cur:
            cur.execute(
                "SELECT m.id_medico, m.nome_medico, m.crm, m.percentual_honorario, "
                "COALESCE((SELECT string_agg(e.nome_especialidade, ', ') FROM medico_especialidade me "
                "JOIN especialidade e USING (id_especialidade) WHERE me.id_medico = m.id_medico), ''), "
                "COALESCE((SELECT string_agg(h.dia_semana || ' ' || to_char(h.hora_inicio,'HH24:MI') || '-' || "
                "to_char(h.hora_fim,'HH24:MI'), '; ' ORDER BY h.id_horario) FROM horario_medico hm "
                "JOIN horario h USING (id_horario) WHERE hm.id_medico = m.id_medico), '') "
                "FROM medico m ORDER BY m.nome_medico")
            return cur.fetchall()

    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_medico, nome_medico FROM medico ORDER BY nome_medico")
            return cur.fetchall()

    def especialidades(self):
        with transacao() as cur:
            cur.execute("SELECT id_especialidade, nome_especialidade FROM especialidade ORDER BY 2")
            return cur.fetchall()

    def horarios(self):
        with transacao() as cur:
            cur.execute("SELECT id_horario, dia_semana || ' ' || to_char(hora_inicio,'HH24:MI') || '-' || "
                        "to_char(hora_fim,'HH24:MI') FROM horario ORDER BY id_horario")
            return cur.fetchall()


class SalaDAO:
    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_sala, descricao FROM sala ORDER BY id_sala")
            return cur.fetchall()


class ConsultaDAO:
    def inserir(self, c):
        """Cria a conta e a consulta na mesma transação: se um gatilho recusar, nada é gravado."""
        with transacao() as cur:
            cur.execute("INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (0, %s) "
                        "RETURNING id_conta", (c.valor,))
            id_conta = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala, id_conta) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id_consulta",
                (c.data_hora, c.status, c.id_paciente, c.id_medico, c.id_sala, id_conta))
            return cur.fetchone()[0]

    def atualizar_status(self, id_consulta, status):
        with transacao() as cur:
            cur.execute("UPDATE consulta SET status = %s, "
                        "data_hora_realizado = CASE WHEN %s = 'REALIZADA' THEN now() ELSE data_hora_realizado END "
                        "WHERE id_consulta = %s", (status, status, id_consulta))

    def listar(self):
        with transacao() as cur:
            cur.execute(
                "SELECT c.id_consulta, to_char(c.data_hora_marcado,'DD/MM/YYYY HH24:MI'), p.nome, "
                "m.nome_medico, s.descricao, c.status, ct.valor_total "
                "FROM consulta c JOIN paciente p USING (id_paciente) JOIN medico m USING (id_medico) "
                "LEFT JOIN sala s USING (id_sala) LEFT JOIN conta ct USING (id_conta) "
                "ORDER BY c.data_hora_marcado DESC")
            return cur.fetchall()

COLUNAS = "id_usuario, nome, email, perfil, ativo, id_medico"

class usuarioDAO:
    def listar(self):
        with transacao() as cur:
            cur.execute(f"SELECT {COLUNAS} FROM usuario ORDER BY ativo DESC, nome")
            return cur.fetchall()
