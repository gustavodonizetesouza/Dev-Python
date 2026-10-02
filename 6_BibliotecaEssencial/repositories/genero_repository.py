# ============================================
# repositories/genero_repository.py
# CRUD da tabela Generos.
# Os métodos insert/update recebem um dict, no padrão
# usado pela tela CRUD genérica (views/crud_view.py).
#
# Exclusão LÓGICA: preenche a coluna 'deletado' com '*'
# (padrão do ASP.NET), ocultando o registro das listagens.
# ============================================
from database import Database


class GeneroRepository:
    @staticmethod
    def list_all():
        return Database.query(
            "SELECT codigo, genero, data_cadastro "
            "FROM Generos WHERE ISNULL(deletado, '') = '' ORDER BY genero"
        )

    @staticmethod
    def get_by_id(codigo):
        return Database.query("SELECT * FROM Generos WHERE codigo = ?", (codigo,))

    @staticmethod
    def insert(dados: dict):
        return Database.execute(
            "INSERT INTO Generos (genero, data_cadastro) VALUES (?, GETDATE())",
            (dados["genero"],),
        )

    @staticmethod
    def update(codigo, dados: dict):
        return Database.execute(
            "UPDATE Generos SET genero = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (dados["genero"], codigo),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Generos SET deletado = '*', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )
