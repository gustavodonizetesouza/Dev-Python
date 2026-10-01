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
    def insert(nome_autor):
        return Database.execute(
            "INSERT INTO Autores (nome_autor, data_cadastro) VALUES (?, GETDATE())",
            (nome_autor,),
        )

    @staticmethod
    def update(codigo, nome_autor):
        return Database.execute(
            "UPDATE Autores SET nome_autor = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (nome_autor, codigo),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Autores SET deletado = 'S', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )
