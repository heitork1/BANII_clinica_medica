from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


class ErroBanco(Exception):
    pass


def _config():
    return dict(
        host="localhost",
        port="5432",
        dbname="clinicaMedica",
        user="postgres",
        password="admin",
    )


@contextmanager
def transacao():
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
        msg = e.diag.message_primary or str(e)
        raise ErroBanco(msg) from e
    finally:
        conn.close()
