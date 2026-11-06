"""Camada de negócio: serviços de pacientes e médicos."""
import psycopg2

from dados.dao import PacienteDAO, MedicoDAO, SalaDAO, UsuarioDAO, PagamentoDAO, ContaDAO
from negocio import ErroValidacao, erro_do_banco
from .modelos import Paciente, Medico
from .validacao import EMAIL_VALIDO, PERFIS, ErroNegocio, checa_senha, cpf_valido, dados_da_sessao, parse_data, parse_numero, somente_digitos, validar_nova_senha
from psycopg2 import errorcodes

class PacienteService:
    def __init__(self):
        self.dao = PacienteDAO()

    def cadastrar(self, nome, cpf, data_nasc, rg, sexo, endereco, email, telefones):
        nome = nome.strip()
        if not nome:
            raise ErroNegocio("Informe o nome do paciente.")
        if not cpf_valido(cpf):
            raise ErroNegocio("CPF inválido.")
        d = somente_digitos(cpf)
        cpf_fmt = f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        if email.strip() and "@" not in email:
            raise ErroNegocio("E-mail inválido.")
        nasc = parse_data(data_nasc) if data_nasc.strip() else None
        tels = [t.strip() for t in telefones.split(",") if t.strip()]
        if self.dao.existe_cpf(cpf_fmt):
            raise ErroNegocio("Já existe um paciente com esse CPF.")
        return self.dao.inserir(Paciente(nome, cpf_fmt, nasc, rg.strip(), sexo, endereco.strip(),
                                         email.strip(), tels))

    def listar(self, filtro=""):
        return self.dao.listar(filtro.strip())

    def opcoes(self):
        return self.dao.opcoes()


class MedicoService:
    def __init__(self):
        self.dao = MedicoDAO()
        self.salas = SalaDAO()

    def cadastrar(self, nome, crm, percentual, telefone, especialidades, horarios):
        if not nome.strip() or not crm.strip():
            raise ErroNegocio("Informe nome e CRM do médico.")
        pct = parse_numero(percentual, "Percentual")
        if not 0 <= pct <= 100:
            raise ErroNegocio("O percentual deve estar entre 0 e 100.")
        if not especialidades:
            raise ErroNegocio("Selecione ao menos uma especialidade.")
        if not horarios:
            raise ErroNegocio("Selecione ao menos um horário de atendimento.")
        return self.dao.inserir(Medico(nome.strip(), crm.strip(), pct, telefone.strip(),
                                       especialidades, horarios))

    def listar(self):
        return self.dao.listar()

    def opcoes(self):
        return self.dao.opcoes()

    def especialidades(self):
        return self.dao.especialidades()

    def horarios(self):
        return self.dao.horarios()

    def salas_opcoes(self):
        return self.salas.opcoes()

SITUACOES_CONTA = ("Em aberto", "Parcial", "Quitada")


class ContaService:
    def __init__(self):
        self.dao = ContaDAO()

    def procedimentos(self):
        """Procedimentos cadastrados no banco: lista de dicts (id_procedimento, descricao, valor)."""
        return self.dao.procedimentos()

    def finalizar_consulta(self, id_consulta, valor_consulta, sintomas, diagnostico, prescricao, itens):
        """Marca a consulta como REALIZADA e gera a conta dela, numa transação só.
        itens: lista de (id_procedimento, quantidade). Devolve o id da conta gerada."""
        if not id_consulta:
            raise ErroNegocio("Selecione a consulta.")
        valor = parse_numero(valor_consulta or "", "Valor da consulta")
        if valor < 0:
            raise ErroNegocio("O valor da consulta não pode ser negativo.")
        for _, qtd in itens:
            if qtd < 1:
                raise ErroNegocio("A quantidade de cada procedimento deve ser pelo menos 1.")
        return self.dao.finalizar_consulta(id_consulta, valor, sintomas.strip() or None,
                                           diagnostico.strip() or None, prescricao.strip() or None, itens)

    def listar(self, situacao=""):
        """Contas com o quanto já foi pago. situacao: vazio (todas), 'Em aberto', 'Parcial' ou 'Quitada'."""
        if situacao and situacao not in SITUACOES_CONTA:
            raise ErroNegocio("Situação inválida.")
        return self.dao.listar(situacao or None)

    @staticmethod
    def totais(linhas):
        """Soma Total (col. 7), Pago (col. 8) e Saldo (col. 9) das linhas exibidas."""
        return tuple(sum(float(l[i] or 0) for l in linhas) for i in (7, 8, 9))


FORMAS_PAGAMENTO = ("CARTAO", "PIX", "DINHEIRO")


class PagamentoService:
    def __init__(self):
        self.dao = PagamentoDAO()

    def listar(self, data_ini="", data_fim="", forma="", convenio="", id_paciente=None, id_medico=None):
        """Filtros vazios são ignorados. convenio: "Sim", "Não" ou vazio (todos)."""
        ini = parse_data(data_ini) if data_ini.strip() else None
        fim = parse_data(data_fim) if data_fim.strip() else None
        if ini and fim and ini > fim:
            raise ErroNegocio("A data inicial não pode ser maior que a data final.")
        if forma and forma not in FORMAS_PAGAMENTO:
            raise ErroNegocio("Forma de pagamento inválida.")
        conv = {"Sim": True, "Não": False}.get(convenio)
        return self.dao.listar(ini, fim, forma or None, conv, id_paciente, id_medico)

    @staticmethod
    def total_pago(linhas):
        """Soma a coluna 'Valor pago' (índice 7) das linhas exibidas."""
        return sum(float(l[7] or 0) for l in linhas)

    def contas_em_aberto(self):
        """Devolve [(id_conta, texto)] das contas que ainda têm saldo a pagar (para o combo do modal)."""
        opcoes = []
        for c in self.dao.contas_em_aberto(limite=100):
            data = c["data_hora_marcado"].strftime("%d/%m/%Y")
            saldo = f"{c['saldo']:.2f}".replace(".", ",")
            opcoes.append((c["id_conta"], f"{c['nome_paciente']} - {data} - saldo R$ {saldo}"))
        return opcoes

    def registrar(self, id_conta, data, forma, valor_pago, possui_convenio, valor_convenio):
        """Valida o que foi digitado e grava o pagamento. Devolve o id do pagamento."""
        if not id_conta:
            raise ErroNegocio("Selecione a conta.")
        if forma not in FORMAS_PAGAMENTO:
            raise ErroNegocio("Selecione a forma de pagamento.")
        data_pagamento = parse_data(data)
        # Campo vazio vale 0 (ex.: o convênio pagou tudo e o paciente não pagou nada).
        pago = parse_numero(valor_pago, "Valor pago") if valor_pago.strip() else 0
        convenio = 0
        if possui_convenio and valor_convenio.strip():
            convenio = parse_numero(valor_convenio, "Valor do convênio")
        # As regras de saldo e carteirinha são conferidas pelo gatilho do banco.
        return self.dao.inserir({
            "data_pagamento": data_pagamento,
            "valor_pago": pago,
            "forma_pagamento": forma,
            "possui_convenio": possui_convenio,
            "valor_convenio": convenio,
            "id_conta": id_conta,
        })


class ServicoAutenticacao:
    def __init__(self):
        self.usuario_dao = UsuarioDAO()

    def entrar(self, email, senha):
        """Confere as credenciais e devolve os dados para a sessão."""
        usuario = self.usuario_dao.buscar_para_login((email or "").strip())
        if not usuario or not checa_senha(usuario["senha_hash"], senha or ""):            
            raise ErroNegocio("E-mail ou senha incorretos.")
        if not usuario["ativo"]:
            raise ErroNegocio("Este usuário está desativado. Procure o administrador do sistema.")

        return dados_da_sessao(usuario)

class UsuarioService:
    def __init__(self):
        self.usuario_dao = UsuarioDAO()
        self.medico_dao = MedicoDAO()

    def listar(self):
        """Retorna todos os usuários ordenados por status ativo e nome."""
        return self.usuario_dao.listar()

    def buscar(self, id_usuario):
        """Busca um usuário pelo seu ID."""
        return self.usuario_dao.buscar_por_id(id_usuario)

    # def medicos_para_vinculo(self, id_medico_atual=None):
    #     """Retorna opções de médicos que ainda não têm usuário no sistema.
    #     """
    #     return [
    #         (m["id_medico"], f"{m['nome_medico']} (CRM {m['crm']})")
    #         for m in self.medico_dao.listar_sem_usuario(id_medico_atual)
    #     ]

    def criar(self, formulario):
        dados = self._validar(formulario, novo=True)

        dados["senha_hash"] = formulario.get("senha")

        try:
            return self.usuario_dao.inserir(dados)
        except psycopg2.Error as erro:
            raise self._traduzir_erro_banco(erro)

    def editar(self, id_usuario, formulario, id_usuario_logado):
        atual = self.usuario_dao.buscar_por_id(id_usuario)
        if not atual:
            raise ErroNegocio("Usuário não encontrado.")

        dados = self._validar(formulario, novo=False, atual=atual)

        if id_usuario == id_usuario_logado and atual["perfil"] == "ADMIN" and dados["perfil"] != "ADMIN":
            raise ErroValidacao({"perfil": "Você não pode remover o seu próprio acesso de administrador."})

        try:
            self.usuario_dao.atualizar(id_usuario, dados)
            if formulario.get("senha"):
                self.usuario_dao.alterar_senha(id_usuario, formulario["senha"])
        except psycopg2.Error as erro:
            raise self._traduzir_erro_banco(erro)

    def alternar_ativo(self, id_usuario, id_usuario_logado):
        usuario = self.usuario_dao.buscar_por_id(id_usuario)
        if not usuario:
            raise ErroNegocio("Usuário não encontrado.")

        if id_usuario == id_usuario_logado:
            raise ErroNegocio("Você não pode desativar o seu próprio usuário.")

        novo_status = not usuario["ativo"]
        self.usuario_dao.definir_ativo(id_usuario, novo_status)
        usuario["ativo"] = novo_status
        return usuario

    def _validar(self, formulario, novo, atual=None):
        erros = {}
        nome = (formulario.get("nome") or "").strip()
        email = (formulario.get("email") or "").strip().lower()
        perfil = formulario.get("perfil") or ""
        senha = formulario.get("senha") or ""

        if not nome:
            erros["nome"] = "Informe o nome."
        elif len(nome) > 100:
            erros["nome"] = "Use no máximo 100 caracteres."
   
        if not EMAIL_VALIDO.match(email):
            erros["email"] = "Informe um e-mail válido."
        elif len(email) > 100:
            erros["email"] = "Use no máximo 100 caracteres."

 
        if perfil not in PERFIS:
            erros["perfil"] = "Escolha um perfil válido (ADMIN, RECEPCAO ou MEDICO)."

        id_medico = None
        if perfil == "MEDICO":
            try:
                id_medico = int(formulario.get("id_medico") or 0) or None
            except ValueError:
                id_medico = None

            if not id_medico:
                erros["id_medico"] = "Escolha o médico vinculado a este usuário."
            elif not self.medico_dao.buscar_por_id(id_medico):
                erros["id_medico"] = "Médico não encontrado no cadastro."

        if novo or senha:
            validar_nova_senha(senha, formulario.get("confirmacao_senha"), erros)

        if erros:
            raise ErroValidacao(erros)

        return {"nome": nome, "email": email, "perfil": perfil, "id_medico": id_medico}

    def _traduzir_erro_banco(self, erro):
        if erro.pgcode == errorcodes.UNIQUE_VIOLATION:
            if "id_medico" in (erro.diag.constraint_name or ""):
                return ErroNegocio({"id_medico": "Este médico já está vinculado a outro usuário."})
            return ErroNegocio({"email": "Já existe um usuário cadastrado com este e-mail."})
        return erro_do_banco(erro)