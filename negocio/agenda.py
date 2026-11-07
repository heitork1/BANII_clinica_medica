"""Camada de negócio: agendamento de consultas.
Conflitos de agenda e horário do médico são validados pelos gatilhos do banco;
aqui validamos o formato e as regras simples antes de gravar."""
from datetime import timedelta

from dados.dao import ConsultaDAO
from .modelos import Consulta
from .validacao import ErroNegocio, parse_data_hora

DURACAO_CONSULTA = timedelta(minutes=30)  # mesmo valor de fn_duracao_consulta() no banco
STATUS = ("AGENDADA", "CONFIRMADA", "REALIZADA", "CANCELADA", "FALTOU")


class AgendaService:
    def __init__(self):
        self.dao = ConsultaDAO()

    def agendar(self, id_paciente, id_medico, id_sala, data, hora):
        """data no formato DD/MM/AAAA e hora no formato HH:MM (campos separados na tela)."""
        if not (id_paciente and id_medico and id_sala):
            raise ErroNegocio("Selecione paciente, médico e sala.")
        # Junta os dois textos ("10/11/2026" + "14:30") e converte de uma vez.
        dh = parse_data_hora(f"{data.strip()} {hora.strip()}")
        # A conta NÃO é criada aqui: ela nasce quando a consulta é finalizada (ContaService).
        return self.dao.inserir(Consulta(id_paciente, id_medico, id_sala, dh))

    def mudar_status(self, id_consulta, status):
        if status not in STATUS:
            raise ErroNegocio("Status inválido.")
        if status == "REALIZADA":
            raise ErroNegocio("Para marcar como REALIZADA é preciso informar os dados da conta.")
        self.dao.atualizar_status(id_consulta, status)

    def listar(self):
        return self.dao.listar()
