"""Camada de negócio: serviços de pacientes e médicos."""
from dados.dao import PacienteDAO, MedicoDAO, SalaDAO, UsuarioDAO, PagamentoDAO, ContaDAO, AtendimentoDAO
from .modelos import Paciente, Medico
from .validacao import ErroNegocio, checa_senha, cpf_valido, dados_da_sessao, parse_data, parse_numero, somente_digitos

DIAS_DA_SEMANA = ("SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO")


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

    def horarios_do_medico(self, id_medico):
        """Texto com os horários do médico, uma linha por dia: 'SEGUNDA: 08:00-12:00, 14:00-18:00'."""
        if not id_medico:
            return "Selecione um médico para ver os horários."
        # Junta as faixas de cada dia: {"SEGUNDA": ["08:00-12:00", "14:00-18:00"], ...}
        faixas_por_dia = {}
        for dia, faixa in self.dao.horarios_do_medico(id_medico):
            faixas_por_dia.setdefault(dia.upper(), []).append(faixa)
        if not faixas_por_dia:
            return "Este médico não tem horários cadastrados."
        linhas = ["Horários de atendimento:"]
        for dia in DIAS_DA_SEMANA:  # percorre na ordem da semana
            if dia in faixas_por_dia:
                linhas.append(f"{dia}: " + ", ".join(faixas_por_dia[dia]))
        return "\n".join(linhas)

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


class AtendimentoService:
    """Atendimento de uma consulta já realizada: prontuário e procedimentos realizados."""

    def __init__(self):
        self.dao = AtendimentoDAO()

    def buscar(self, id_consulta):
        """Devolve a consulta (dict) com a lista 'procedimentos' dentro dela."""
        consulta = self.dao.buscar(id_consulta)
        if consulta is None:
            raise ErroNegocio("Consulta não encontrada.")
        consulta["procedimentos"] = self.dao.procedimentos(id_consulta)
        return consulta

    def salvar(self, id_consulta, sintomas, diagnostico, prescricao, itens):
        """itens: lista de (id_procedimento, quantidade, valor_unitario)."""
        for _, quantidade, _ in itens:
            if quantidade < 1:
                raise ErroNegocio("A quantidade de cada procedimento deve ser pelo menos 1.")
        # Texto vazio vira None (NULL no banco).
        self.dao.salvar(id_consulta, sintomas.strip() or None, diagnostico.strip() or None,
                        prescricao.strip() or None, itens)


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
