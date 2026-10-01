# ============================================
# database.py
# Gerenciador de conexão com o SQL Server.
# Usa o padrão singleton: uma única conexão reutilizada
# por todo o aplicativo.
#
# Ajuste desta versão:
#   - Normalização de parâmetros: se o chamador passar
#     uma string/valor solto, transforma automaticamente
#     em tupla válida para o pyodbc (evita o erro
#     "A TVP's rows must be Sequence objects" na edição).
# ============================================
import pyodbc
from config import Config


class Database:
    # Guarda a conexão ativa (None = ainda não conectou)
    _connection = None

    @classmethod
    def get_connection(cls):
        """Retorna a conexão, criando-a se ainda não existir."""
        if cls._connection is None:
            cls._connection = pyodbc.connect(Config.connection_string())
        return cls._connection

    @classmethod
    def close(cls):
        """Fecha a conexão com o banco."""
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None

    @staticmethod
    def _normalizar_params(params):
        """Garante que os parâmetros sejam aceitos pelo pyodbc.

        - None                -> ()      (sem parâmetros)
        - dict                -> dict    (parâmetros nomeados)
        - tupla / lista       -> tupla   (evita interpretação como TVP)
        - string / número     -> (valor,) (um único parâmetro)
        """
        if params is None:
            return ()
        if isinstance(params, dict):
            return params
        if isinstance(params, (tuple, list)):
            return tuple(params)
        return (params,)

    @classmethod
    def query(cls, sql, params=None):
        """Executa um SELECT e retorna as linhas encontradas."""
        cursor = cls.get_connection().cursor()
        cursor.execute(sql, cls._normalizar_params(params))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    @classmethod
    def execute(cls, sql, params=None):
        """Executa INSERT/UPDATE/DELETE e confirma a alteração."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, cls._normalizar_params(params))
        conn.commit()
        cursor.close()
