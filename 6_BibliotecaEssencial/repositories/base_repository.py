# ============================================
# repositories/base_repository.py
# Classe genérica de CRUD (Create, Read, Update, Delete).
# Reutilizada por qualquer entidade do sistema,
# evitando repetição de código.
# ============================================
from database import Database


class BaseRepository:
    def __init__(self, table: str, columns: list, pk: str):
        # Nome da tabela no banco
        self.table = table
        # Lista de colunas que serão manipuladas (ex.: ["nome_autor"])
        self.columns = columns
        # Nome da coluna chave primária (ex.: "codigo")
        self.pk = pk

    def list_all(self) -> list:
        """Lista todos os registros da tabela."""
        cols = ", ".join(self.columns)
        return Database.query(f"SELECT {cols} FROM {self.table}")

    def get_by_id(self, pk_value) -> list:
        """Busca um registro pela chave primária."""
        cols = ", ".join(self.columns)
        return Database.query(
            f"SELECT {cols} FROM {self.table} WHERE {self.pk} = ?",
            (pk_value,),
        )

    def insert(self, values: tuple) -> None:
        """Insere um novo registro."""
        placeholders = ", ".join(["?"] * len(self.columns))
        cols = ", ".join(self.columns)
        Database.execute(
            f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders})",
            values,
        )

    def update(self, pk_value, values: tuple) -> None:
        """Atualiza um registro existente."""
        sets = ", ".join([f"{col} = ?" for col in self.columns])
        Database.execute(
            f"UPDATE {self.table} SET {sets} WHERE {self.pk} = ?",
            values + (pk_value,),
        )

    def delete(self, pk_value) -> None:
        """Exclui um registro pela chave primária."""
        Database.execute(
            f"DELETE FROM {self.table} WHERE {self.pk} = ?",
            (pk_value,),
        )
