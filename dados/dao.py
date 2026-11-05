"""Camada de dados: acesso às tabelas (DAOs). Só SQL, sem regras de negócio."""
from .conexao import transacao


def _tuplas(linhas):
    """Converte linhas dict em tuplas (formato que a interface antiga espera)."""
    return [tuple(l.values()) for l in linhas]


class PacienteDAO:
    def inserir(self, p):
        with transacao() as cur:
            cur.execute(
                'INSERT INTO paciente (nome, data_nasc, cpf, rg, sexo, endereco, "e-mail") '
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id_paciente AS id",
                (p.nome, p.data_nasc, p.cpf, p.rg, p.sexo, p.endereco, p.email))
            id_paciente = cur.fetchone()["id"]
            for tel in p.telefones:
                cur.execute("INSERT INTO telefone_paciente (numero_telefone, id_paciente) VALUES (%s,%s)",
                            (tel, id_paciente))
            return id_paciente

    def listar(self, filtro=""):
        with transacao() as cur:
            cur.execute(
                'SELECT p.id_paciente, p.nome, p.cpf, p.data_nasc, p."e-mail", '
                "COALESCE((SELECT string_agg(t.numero_telefone, ', ') FROM telefone_paciente t "
                "WHERE t.id_paciente = p.id_paciente), '') AS telefones "
                "FROM paciente p WHERE p.nome ILIKE %s OR p.cpf LIKE %s ORDER BY p.nome",
                (f"%{filtro}%", f"%{filtro}%"))
            return _tuplas(cur.fetchall())

    def existe_cpf(self, cpf):
        with transacao() as cur:
            cur.execute("SELECT 1 FROM paciente WHERE cpf = %s", (cpf,))
            return cur.fetchone() is not None

    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_paciente, nome FROM paciente ORDER BY nome")
            return _tuplas(cur.fetchall())


class MedicoDAO:
    def inserir(self, m):
        with transacao() as cur:
            cur.execute("INSERT INTO medico (nome_medico, percentual_honorario, crm) "
                        "VALUES (%s,%s,%s) RETURNING id_medico AS id",
                        (m.nome, m.percentual, m.crm))
            id_medico = cur.fetchone()["id"]
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
                "JOIN especialidade e USING (id_especialidade) WHERE me.id_medico = m.id_medico), '') AS especialidades, "
                "COALESCE((SELECT string_agg(h.dia_semana || ' ' || to_char(h.hora_inicio,'HH24:MI') || '-' || "
                "to_char(h.hora_fim,'HH24:MI'), '; ' ORDER BY h.id_horario) FROM horario_medico hm "
                "JOIN horario h USING (id_horario) WHERE hm.id_medico = m.id_medico), '') AS horarios "
                "FROM medico m ORDER BY m.nome_medico")
            return _tuplas(cur.fetchall())

    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_medico, nome_medico FROM medico ORDER BY nome_medico")
            return _tuplas(cur.fetchall())

    def especialidades(self):
        with transacao() as cur:
            cur.execute("SELECT id_especialidade, nome_especialidade FROM especialidade ORDER BY 2")
            return _tuplas(cur.fetchall())

    def horarios(self):
        with transacao() as cur:
            cur.execute("SELECT id_horario, dia_semana || ' ' || to_char(hora_inicio,'HH24:MI') || '-' || "
                        "to_char(hora_fim,'HH24:MI') AS descricao FROM horario ORDER BY id_horario")
            return _tuplas(cur.fetchall())


class SalaDAO:
    def opcoes(self):
        with transacao() as cur:
            cur.execute("SELECT id_sala, descricao FROM sala ORDER BY id_sala")
            return _tuplas(cur.fetchall())


class ConsultaDAO:
    def inserir(self, c):
        """Cria a conta e a consulta na mesma transação: se um gatilho recusar, nada é gravado."""
        with transacao() as cur:
            cur.execute("INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (0, %s) "
                        "RETURNING id_conta AS id", (c.valor,))
            id_conta = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala, id_conta) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id_consulta AS id",
                (c.data_hora, c.status, c.id_paciente, c.id_medico, c.id_sala, id_conta))
            return cur.fetchone()["id"]

    def atualizar_status(self, id_consulta, status):
        with transacao() as cur:
            cur.execute("UPDATE consulta SET status = %s, "
                        "data_hora_realizado = CASE WHEN %s = 'REALIZADA' THEN now() ELSE data_hora_realizado END "
                        "WHERE id_consulta = %s", (status, status, id_consulta))

    def listar(self):
        with transacao() as cur:
            cur.execute(
                "SELECT c.id_consulta, to_char(c.data_hora_marcado,'DD/MM/YYYY HH24:MI') AS data_hora, p.nome, "
                "m.nome_medico, s.descricao, c.status, ct.valor_total "
                "FROM consulta c JOIN paciente p USING (id_paciente) JOIN medico m USING (id_medico) "
                "LEFT JOIN sala s USING (id_sala) LEFT JOIN conta ct USING (id_conta) "
                "ORDER BY c.data_hora_marcado DESC")
            return _tuplas(cur.fetchall())

COLUNAS = "id_usuario, nome, email, perfil, ativo, id_medico"

class UsuarioDAO:
    def listar(self):
        with transacao() as cur:
            cur.execute(f"SELECT {COLUNAS} FROM usuario ORDER BY ativo DESC, nome")
            return cur.fetchall()
        
    def buscar_por_id(self, id_usuario):
        with transacao() as cur:
            cur.execute(f"SELECT {COLUNAS} FROM usuario WHERE id_usuario = %s", (id_usuario,))
            return cur.fetchone()

    def buscar_para_login(self, email):
        with transacao() as cur:
            cur.execute(
                f"SELECT {COLUNAS}, senha_hash FROM usuario WHERE lower(email) = lower(%s)",
                (email,),
            )
            return cur.fetchone()

    def buscar_senha_hash(self, id_usuario):
        with transacao() as cur:
            cur.execute("SELECT senha_hash FROM usuario WHERE id_usuario = %s", (id_usuario,))
            linha = cur.fetchone()
            return linha["senha_hash"] if linha else None

    def inserir(self, dados):
        with transacao() as cur:
            cur.execute(
                """
                INSERT INTO usuario (nome, email, senha_hash, perfil, id_medico)
                VALUES (%(nome)s, %(email)s, %(senha_hash)s, %(perfil)s, %(id_medico)s)
                RETURNING id_usuario
                """,
                dados,
            )
            return cur.fetchone()["id_usuario"]

    def atualizar(self, id_usuario, dados):
        with transacao() as cur:
            cur.execute(
                """
                UPDATE usuario
                   SET nome = %(nome)s, email = %(email)s, perfil = %(perfil)s, id_medico = %(id_medico)s
                 WHERE id_usuario = %(id_usuario)s
                """,
                {**dados, "id_usuario": id_usuario},
            )

    def alterar_senha(self, id_usuario, senha_hash):
        with transacao() as cur:
            cur.execute(
                "UPDATE usuario SET senha_hash = %s WHERE id_usuario = %s",
                (senha_hash, id_usuario),
            )

    def definir_ativo(self, id_usuario, ativo):
        with transacao() as cur:
            cur.execute(
                "UPDATE usuario SET ativo = %s WHERE id_usuario = %s",
                (ativo, id_usuario),
            )
