# ============================================
# repositories/autor_repository.py
# CRUD da tabela Autores.
# Schema: codigo, nome_autor, data_cadastro, ...
# Os métodos insert/update recebem um dict, no padrão
# usado pela tela CRUD genérica (views/crud_view.py).
#
# Exclusão LÓGICA: preenche a coluna 'deletado' com '*'
# (padrão do ASP.NET), ocultando o registro das listagens.
# ============================================
from database import Database


class AutorRepository:
    @staticmethod
    def list_all():
        return Database.query(
            "SELECT codigo, nome_autor, data_cadastro "
            "FROM Autores WHERE ISNULL(deletado, '') = '' ORDER BY nome_autor"
        )

    @staticmethod
    def get_by_id(codigo):
        return Database.query("SELECT * FROM Autores WHERE codigo = ?", (codigo,))

    @staticmethod
    def insert(dados: dict):
        return Database.execute(
            "INSERT INTO Autores (nome_autor, data_cadastro) VALUES (?, GETDATE())",
            (dados["nome_autor"],),
        )

    @staticmethod
    def update(codigo, dados: dict):
        return Database.execute(
            "UPDATE Autores SET nome_autor = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (dados["nome_autor"], codigo),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Autores SET deletado = '*', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )
