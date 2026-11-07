"""Camada de dados: acesso às tabelas (DAOs). Só SQL, sem regras de negócio."""
from .conexao import transacao, ErroBanco


def _tuplas(linhas):
    """Converte linhas dict em tuplas (formato que a interface antiga espera)."""
    return [tuple(l.values()) for l in linhas]

# Total já pago de uma conta (paciente + convênio); usar com GROUP BY ct.id_conta.
SOMA_PAGA = "COALESCE(sum(COALESCE(pg.valor_pago, 0) + COALESCE(pg.valor_convenio, 0)), 0)"


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
        """Agenda a consulta (sem conta: ela só é gerada quando a consulta é finalizada)."""
        with transacao() as cur:
            cur.execute(
                "INSERT INTO consulta (data_hora_marcado, status, id_paciente, id_medico, id_sala) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id_consulta AS id",
                (c.data_hora, c.status, c.id_paciente, c.id_medico, c.id_sala))
            return cur.fetchone()["id"]

    def atualizar_status(self, id_consulta, status):
        with transacao() as cur:
            cur.execute("SELECT status FROM consulta WHERE id_consulta = %s FOR UPDATE", (id_consulta,))
            atual = cur.fetchone()
            if atual is None:
                raise ErroBanco("Consulta não encontrada.")
            if atual["status"] == "REALIZADA":
                raise ErroBanco("Esta consulta já foi realizada e a conta já foi gerada: "
                                "o status não pode mais ser alterado.")
            cur.execute("UPDATE consulta SET status = %s WHERE id_consulta = %s", (status, id_consulta))

    def listar(self):
        with transacao() as cur:
            cur.execute(
                "SELECT c.id_consulta, to_char(c.data_hora_marcado,'DD/MM/YYYY HH24:MI') AS data_hora, p.nome, "
                "m.nome_medico, s.descricao, c.status, ct.valor_total "
                "FROM consulta c JOIN paciente p USING (id_paciente) JOIN medico m USING (id_medico) "
                "LEFT JOIN sala s USING (id_sala) LEFT JOIN conta ct USING (id_conta) "
                "ORDER BY c.data_hora_marcado DESC")
            return _tuplas(cur.fetchall())

class ContaDAO:
    def procedimentos(self):
        with transacao() as cur:
            cur.execute("SELECT id_procedimento, descricao, valor FROM procedimento ORDER BY descricao")
            return cur.fetchall()

    def finalizar_consulta(self, id_consulta, valor_consulta, sintomas, diagnostico, prescricao, itens):
        """Numa única transação: gera a conta, liga à consulta, marca REALIZADA e grava os procedimentos.
        O gatilho fn_atualiza_valor_procedimento_conta recalcula conta.valor_procedimento sozinho,
        por isso a consulta precisa estar ligada à conta ANTES de inserir os procedimentos."""
        with transacao() as cur:
            cur.execute("SELECT status, id_conta FROM consulta WHERE id_consulta = %s FOR UPDATE",
                        (id_consulta,))
            consulta = cur.fetchone()
            if consulta is None:
                raise ErroBanco("Consulta não encontrada.")
            if consulta["status"] == "REALIZADA":
                raise ErroBanco("Esta consulta já foi realizada e a conta já foi gerada.")

            id_conta = consulta["id_conta"]
            if id_conta is None:
                cur.execute("INSERT INTO conta (valor_procedimento, valor_consulta) VALUES (0, %s) "
                            "RETURNING id_conta AS id", (valor_consulta,))
                id_conta = cur.fetchone()["id"]
            else:  # consulta antiga, que já tinha conta criada no agendamento
                cur.execute("UPDATE conta SET valor_consulta = %s WHERE id_conta = %s",
                            (valor_consulta, id_conta))

            cur.execute(
                "UPDATE consulta SET status = 'REALIZADA', data_hora_realizado = now(), "
                "sintomas = %s, diagnostico = %s, prescricao = %s, id_conta = %s "
                "WHERE id_consulta = %s",
                (sintomas, diagnostico, prescricao, id_conta, id_consulta))

            for id_procedimento, quantidade in itens:
                # valor_unitario guarda o preço da época: mudar o cadastro depois não altera contas antigas
                cur.execute(
                    "INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario) "
                    "SELECT %s, id_procedimento, %s, valor FROM procedimento WHERE id_procedimento = %s",
                    (id_consulta, quantidade, id_procedimento))
                if cur.rowcount == 0:
                    raise ErroBanco("Procedimento não encontrado no cadastro.")
            return id_conta

    def listar(self, situacao=None):
        """Todas as contas com consulta, paciente, médico, total pago, saldo e situação."""
        filtro = "WHERE t.situacao = %s" if situacao else ""
        sql = f"""
            SELECT * FROM (
                SELECT ct.id_conta AS conta, c.id_consulta AS consulta,
                    to_char(c.data_hora_realizado, 'DD/MM/YYYY HH24:MI') AS realizada_em,
                    p.nome AS paciente, m.nome_medico AS medico,
                    ct.valor_consulta AS v_consulta, ct.valor_procedimento AS v_procedimentos,
                    COALESCE(ct.valor_total, 0) AS total,
                    {SOMA_PAGA} AS pago,
                    COALESCE(ct.valor_total, 0) - {SOMA_PAGA} AS saldo,
                    CASE WHEN {SOMA_PAGA} >= COALESCE(ct.valor_total, 0) THEN 'Quitada'
                         WHEN {SOMA_PAGA} > 0 THEN 'Parcial'
                         ELSE 'Em aberto' END AS situacao
                FROM conta ct
                LEFT JOIN consulta c ON c.id_conta = ct.id_conta
                LEFT JOIN paciente p ON p.id_paciente = c.id_paciente
                LEFT JOIN medico m ON m.id_medico = c.id_medico
                LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta
                GROUP BY ct.id_conta, c.id_consulta, p.id_paciente, m.id_medico
            ) t
            {filtro}
            ORDER BY t.conta DESC
        """
        with transacao() as cur:
            cur.execute(sql, (situacao,) if situacao else None)
            return _tuplas(cur.fetchall())


class PagamentoDAO:
    def listar(self, data_ini=None, data_fim=None, forma=None, convenio=None,
               id_paciente=None, id_medico=None):
        """Lista pagamentos aplicando só os filtros informados (None = não filtra).
        Paciente e médico vêm da consulta que originou a conta."""
        where, params = [], []
        if data_ini:
            where.append("pg.data_pagamento >= %s"); 
            params.append(data_ini)
        if data_fim:
            where.append("pg.data_pagamento <= %s"); 
            params.append(data_fim)
        if forma:
            where.append("pg.forma_pagamento = %s"); 
            params.append(forma)
        if convenio is not None:
            where.append("COALESCE(pg.possui_convenio, FALSE) = %s"); 
            params.append(convenio)
        if id_paciente:
            where.append("c.id_paciente = %s"); 
            params.append(id_paciente)
        if id_medico:
            where.append("c.id_medico = %s"); 
            params.append(id_medico)
        sql = (
            "SELECT pg.id_pagamento, to_char(pg.data_pagamento,'DD/MM/YYYY') AS data, "
            "p.nome, m.nome_medico, pg.forma_pagamento, "
            "CASE WHEN pg.possui_convenio THEN 'Sim' ELSE 'Não' END AS convenio, "
            "pg.valor_convenio, pg.valor_pago, pg.id_conta "
            "FROM pagamento pg "
            "LEFT JOIN consulta c ON c.id_conta = pg.id_conta "
            "LEFT JOIN paciente p ON p.id_paciente = c.id_paciente "
            "LEFT JOIN medico m ON m.id_medico = c.id_medico "
            + ("WHERE " + " AND ".join(where) + " " if where else "")
            + "ORDER BY pg.data_pagamento DESC NULLS LAST, pg.id_pagamento DESC")
        with transacao() as cur:
            cur.execute(sql, params)
            return _tuplas(cur.fetchall())

    # ---- Operações sobre os pagamentos de UMA conta (base do futuro modal de pagamentos) ----

    def buscar_conta(self, id_conta):
        """Totais da conta: valor, quanto o paciente e o convênio já pagaram, e o saldo."""
        with transacao() as cur:
            cur.execute(
                f"""
                SELECT ct.id_conta, ct.valor_consulta, ct.valor_procedimento,
                    COALESCE(ct.valor_total, 0) AS valor_total,
                    COALESCE(sum(pg.valor_pago), 0) AS pago_paciente,
                    COALESCE(sum(pg.valor_convenio), 0) AS pago_convenio,
                    COALESCE(ct.valor_total, 0) - {SOMA_PAGA} AS saldo,
                    count(pg.id_pagamento) AS quantidade_pagamentos
                FROM conta ct
                LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta
                WHERE ct.id_conta = %s
                GROUP BY ct.id_conta
                """,
                (id_conta,))
            return cur.fetchone()

    def listar_por_conta(self, id_conta):
        """Pagamentos de uma conta, do mais antigo para o mais novo (linhas como dict)."""
        with transacao() as cur:
            cur.execute(
                """
                SELECT id_pagamento, data_pagamento, valor_pago, forma_pagamento,
                    possui_convenio, valor_convenio,
                    COALESCE(valor_pago, 0) + COALESCE(valor_convenio, 0) AS total
                FROM pagamento
                WHERE id_conta = %s
                ORDER BY data_pagamento, id_pagamento
                """,
                (id_conta,))
            return cur.fetchall()

    def inserir(self, dados):
        """dados: dict com data_pagamento, valor_pago, forma_pagamento, possui_convenio,
        valor_convenio e id_conta. O gatilho fn_valida_pagamento recusa dados inválidos."""
        with transacao() as cur:
            cur.execute(
                """
                INSERT INTO pagamento (data_pagamento, valor_pago, forma_pagamento,
                                       possui_convenio, valor_convenio, id_conta)
                VALUES (%(data_pagamento)s, %(valor_pago)s, %(forma_pagamento)s,
                        %(possui_convenio)s, %(valor_convenio)s, %(id_conta)s)
                RETURNING id_pagamento
                """,
                dados)
            return cur.fetchone()["id_pagamento"]

    def excluir(self, id_pagamento, id_conta):
        """Apaga o pagamento só se ele pertencer à conta informada. Devolve True se apagou."""
        with transacao() as cur:
            cur.execute("DELETE FROM pagamento WHERE id_pagamento = %s AND id_conta = %s",
                        (id_pagamento, id_conta))
            return cur.rowcount > 0

    def contas_em_aberto(self, limite=10):
        """Consultas realizadas cuja conta ainda tem saldo, das mais antigas para as mais novas."""
        with transacao() as cur:
            cur.execute(
                f"""
                SELECT ct.id_conta, c.id_consulta, c.data_hora_marcado, p.nome AS nome_paciente,
                    COALESCE(ct.valor_total, 0) - {SOMA_PAGA} AS saldo
                FROM consulta c
                JOIN paciente p ON p.id_paciente = c.id_paciente
                JOIN conta ct ON ct.id_conta = c.id_conta
                LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta
                WHERE c.status = 'REALIZADA'
                GROUP BY c.id_consulta, p.nome, ct.id_conta
                HAVING COALESCE(ct.valor_total, 0) - {SOMA_PAGA} > 0
                ORDER BY c.data_hora_marcado
                LIMIT %s
                """,
                (limite,))
            return cur.fetchall()


COLUNAS = "id_usuario, nome, email, perfil, ativo, id_medico"

class AtendimentoDAO:
    def procedimentos(self, id_consulta):
        with transacao() as cur:
            cur.execute(
                """
                SELECT cp.id_procedimento, p.descricao, cp.quantidade, cp.valor_unitario,
                       cp.quantidade * cp.valor_unitario AS subtotal
                  FROM consulta_procedimento cp
                  JOIN procedimento p ON p.id_procedimento = cp.id_procedimento
                 WHERE cp.id_consulta = %s
                 ORDER BY p.descricao
                """,
                (id_consulta,),
            )
            return cur.fetchall()

    def buscar(self, id_consulta):
        """Dados da consulta que a janela de atendimento mostra (devolve None se não existir)."""
        with transacao() as cur:
            cur.execute(
                "SELECT c.id_consulta, c.status, c.sintomas, c.diagnostico, c.prescricao, "
                "to_char(c.data_hora_marcado,'DD/MM/YYYY HH24:MI') AS data_hora, "
                "p.nome AS paciente, m.nome_medico AS medico "
                "FROM consulta c JOIN paciente p USING (id_paciente) JOIN medico m USING (id_medico) "
                "WHERE c.id_consulta = %s", (id_consulta,))
            return cur.fetchone()

    def salvar(self, id_consulta, sintomas, diagnostico, prescricao, itens):
        """Salva o prontuário e a lista de procedimentos de uma consulta REALIZADA, numa transação só.
        itens: lista de (id_procedimento, quantidade, valor_unitario).
        O gatilho fn_atualiza_valor_procedimento_conta recalcula conta.valor_procedimento sozinho."""
        with transacao() as cur:
            cur.execute("SELECT status, id_conta FROM consulta WHERE id_consulta = %s FOR UPDATE",
                        (id_consulta,))
            consulta = cur.fetchone()
            if consulta is None:
                raise ErroBanco("Consulta não encontrada.")
            if consulta["status"] != "REALIZADA":
                raise ErroBanco("Só dá para editar o atendimento de uma consulta realizada.")

            # 1) prontuário
            cur.execute("UPDATE consulta SET sintomas = %s, diagnostico = %s, prescricao = %s "
                        "WHERE id_consulta = %s", (sintomas, diagnostico, prescricao, id_consulta))

            # 2) procedimentos: apaga a lista antiga e grava a nova (é o jeito mais simples de editar)
            cur.execute("DELETE FROM consulta_procedimento WHERE id_consulta = %s", (id_consulta,))
            for id_procedimento, quantidade, valor_unitario in itens:
                cur.execute(
                    "INSERT INTO consulta_procedimento (id_consulta, id_procedimento, quantidade, valor_unitario) "
                    "VALUES (%s, %s, %s, %s)", (id_consulta, id_procedimento, quantidade, valor_unitario))

            # 3) o total novo da conta não pode ficar menor do que já foi pago.
            #    Se ficar, o erro desfaz tudo (prontuário e procedimentos).
            cur.execute(
                f"SELECT COALESCE(ct.valor_total, 0) AS total, {SOMA_PAGA} AS pago "
                "FROM conta ct LEFT JOIN pagamento pg ON pg.id_conta = ct.id_conta "
                "WHERE ct.id_conta = %s GROUP BY ct.id_conta", (consulta["id_conta"],))
            conta = cur.fetchone()
            if conta and conta["pago"] > conta["total"]:
                raise ErroBanco(f"Com essa lista de procedimentos o total da conta seria R$ {conta['total']:.2f}, "
                                f"menos do que já foi pago (R$ {conta['pago']:.2f}). Nada foi alterado.")

    

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
