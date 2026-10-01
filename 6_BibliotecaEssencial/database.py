# ============================================
# database.py
# Gerenciador de conexão com o SQL Server.
# Usa o padrão singleton: uma única conexão reutilizada
# por todo o aplicativo.
# ============================================
import pyodbc
from config import Config


class Database:
    # Guarda a conexão ativa (None = ainda não conectou)
    _connection = None

    @classmethod
    def get_connection(cls) -> pyodbc.Connection:
        """Retorna a conexão, criando-a se ainda não existir."""
        if cls._connection is None:
            cls._connection = pyodbc.connect(Config.connection_string())
        return cls._connection

    @classmethod
    def close(cls) -> None:
        """Fecha a conexão com o banco."""
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None

    @classmethod
    def query(cls, sql: str, params: tuple = ()) -> list:
        """Executa um SELECT e retorna as linhas encontradas."""
        cursor = cls.get_connection().cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    @classmethod
    def execute(cls, sql: str, params: tuple = ()) -> None:
        """Executa INSERT/UPDATE/DELETE e confirma a alteração."""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()  # grava a alteração no banco
        cursor.close()
