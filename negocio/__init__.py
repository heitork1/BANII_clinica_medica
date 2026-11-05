import logging
from psycopg2 import errorcodes

log = logging.getLogger(__name__)

class ErroNegocio(Exception):
    """Erro com mensagem pronta para mostrar ao usuário.

    Os serviços lançam este erro quando uma regra é violada ou quando o banco
    recusa a operação (ex.: mensagem de um gatilho). As rotas capturam e exibem
    a mensagem com flash().
    """



class ErroValidacao(ErroNegocio):
    """Erros de preenchimento, um por campo: {"email": "Informe um e-mail válido."}.

    A rota exibe a mensagem geral com flash() e passa `erros` ao template,
    que marca cada campo com a sua mensagem.
    """

    def __init__(self, erros, mensagem="Corrija os campos destacados."):
        super().__init__(mensagem)
        self.erros = erros


def erro_do_banco(erro, mensagens=None):
    """Converte um psycopg2.Error em ErroNegocio.

    mensagens: textos para códigos SQLSTATE conhecidos, por exemplo
    {errorcodes.FOREIGN_KEY_VIOLATION: "Registro em uso."}.
    Mensagens levantadas por gatilhos (RAISE EXCEPTION) passam direto.
    """
    mensagens = mensagens or {}
    if erro.pgcode in mensagens:
        return ErroNegocio(mensagens[erro.pgcode])
    if erro.pgcode == errorcodes.RAISE_EXCEPTION and erro.diag.message_primary:
        return ErroNegocio(erro.diag.message_primary)

    log.exception("Erro não tratado do banco de dados")
    return ErroNegocio("Não foi possível concluir a operação no banco de dados.")
