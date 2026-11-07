class ErroNegocio(Exception):
    """Erro com mensagem pronta para mostrar ao usuário.

    Os serviços lançam este erro quando uma regra é violada ou quando o banco
    recusa a operação (ex.: mensagem de um gatilho). A tela captura o erro
    (função executar, em janela.py) e mostra a mensagem numa caixa.
    """
