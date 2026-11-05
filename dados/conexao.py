"""Camada de dados: conexão e controle de transação com o PostgreSQL."""
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


class ErroBanco(Exception):
    """Erro vindo do banco (inclui as mensagens dos gatilhos)."""


def _config():
    return dict(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "clinica"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "Selv@123"), #essa é a senha do meu banco
    )


@contextmanager
def transacao():
    """Entrega um cursor (linhas como dict); confirma ao sair ou desfaz tudo se houver erro."""
    try:
        conn = psycopg2.connect(**_config())
    except psycopg2.Error as e:
        raise ErroBanco(f"Não foi possível conectar ao banco: {e}") from e
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
    except psycopg2.Error as e:
        if e.pgcode == "23505":
            raise ErroBanco("Registro duplicado (valor único já cadastrado).") from e
        msg = (e.diag.message_primary if e.diag and e.diag.message_primary else str(e))
        raise ErroBanco(msg) from e
    finally:
        conn.close()
