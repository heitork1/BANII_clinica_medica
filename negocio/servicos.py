"""Camada de negócio: serviços de pacientes e médicos."""
from dados.dao import PacienteDAO, MedicoDAO, SalaDAO
from .modelos import Paciente, Medico
from .validacao import ErroNegocio, cpf_valido, parse_data, parse_numero, somente_digitos


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

    class ServicoAutenticacao:
        def __init__(self):
            self.usuario_dao = 
