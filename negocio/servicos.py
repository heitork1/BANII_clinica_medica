"""Camada de negócio: serviços de pacientes e médicos."""
import psycopg2

from dados.dao import PacienteDAO, MedicoDAO, SalaDAO, UsuarioDAO
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
        self.usuario_dao = UsuarioDAO()

    def entrar(self, email, senha):
        """Confere as credenciais e devolve os dados para a sessão."""
        usuario = self.usuario_dao.buscar_para_login((email or "").strip())
        print(f"O usuario é: {usuario}")
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