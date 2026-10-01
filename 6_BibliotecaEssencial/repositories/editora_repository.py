# ============================================
# repositories/editora_repository.py
# CRUD da tabela Editoras.
# Os métodos insert/update recebem um dict, no padrão
# usado pela tela CRUD genérica (views/crud_view.py).
# ============================================
from database import Database


class EditoraRepository:
    @staticmethod
    def list_all():
        return Database.query(
            "SELECT codigo, editora, data_cadastro "
            "FROM Editoras WHERE ISNULL(deletado, '') = '' ORDER BY editora"
        )

    @staticmethod
    def get_by_id(codigo):
        return Database.query("SELECT * FROM Editoras WHERE codigo = ?", (codigo,))

    @staticmethod
    def insert(dados: dict):
        return Database.execute(
            "INSERT INTO Editoras (editora, data_cadastro) VALUES (?, GETDATE())",
            (dados["editora"],),
        )

    @staticmethod
    def update(codigo, dados: dict):
        return Database.execute(
            "UPDATE Editoras SET editora = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (dados["editora"], codigo),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Editoras SET deletado = 'S', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )
