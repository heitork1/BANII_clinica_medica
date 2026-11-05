"""Camada de negócio: validações e conversões de entrada."""
import re
from datetime import datetime

from negocio import ErroNegocio

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAMANHO_MINIMO_SENHA = 3

PERFIS = {
    "ADMIN": "Administrador",
    "RECEPCAO": "Recepção",
    "MEDICO": "Médico",
}

def somente_digitos(texto):
    return re.sub(r"\D", "", texto or "")

def cpf_valido(cpf):
    d = somente_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tam in (9, 10):
        soma = sum(int(d[i]) * (tam + 1 - i) for i in range(tam))
        if int(d[tam]) != (soma * 10 % 11) % 10:
            return False
    return True


def parse_data(texto):
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ErroNegocio("Data inválida. Use DD/MM/AAAA.")


def parse_data_hora(texto):
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y %H:%M")
    except ValueError:
        raise ErroNegocio("Data e hora inválidas. Use DD/MM/AAAA HH:MM.")


def parse_numero(texto, campo):
    try:
        return float(texto.strip().replace(",", "."))
    except ValueError:
        raise ErroNegocio(f"{campo} inválido.")

def checa_senha(senha_banco, senha_digitada):
    resultado_verificacao = senha_banco == senha_digitada
    print(f"Resultado da verificação {resultado_verificacao}")
    return resultado_verificacao

def dados_da_sessao(usuario):
    """O que fica guardado na sessão do Flask enquanto o usuário está logado."""
    return {
        "id_usuario": usuario["id_usuario"],
        "nome": usuario["nome"],
        "perfil": usuario["perfil"],
        "id_medico": usuario["id_medico"],
    }

def validar_nova_senha(senha, confirmacao, erros, campo="senha", campo_confirmacao="confirmacao_senha"):
    """Confere tamanho e confirmação; os problemas vão para o dicionário `erros`."""
    if len(senha or "") < TAMANHO_MINIMO_SENHA:
        erros[campo] = f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
    elif senha != confirmacao:
        erros[campo_confirmacao] = "As senhas não conferem."
