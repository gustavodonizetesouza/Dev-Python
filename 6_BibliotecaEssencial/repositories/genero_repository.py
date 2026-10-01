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
    def insert(genero):
        return Database.execute(
            "INSERT INTO Generos (genero, data_cadastro) VALUES (?, GETDATE())",
            (genero,),
        )

    @staticmethod
    def update(codigo, genero):
        return Database.execute(
            "UPDATE Generos SET genero = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (genero, codigo),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Generos SET deletado = 'S', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )