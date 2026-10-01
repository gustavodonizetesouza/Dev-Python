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
    def insert(editora):
        return Database.execute(
            "INSERT INTO Editoras (editora, data_cadastro) VALUES (?, GETDATE())",
            (editora,),
        )

    @staticmethod
    def update(codigo, editora):
        return Database.execute(
            "UPDATE Editoras SET editora = ?, data_alteracao = GETDATE() WHERE codigo = ?",
            (editora, codigo),
        )

    @staticmethod
    def delete(codigo):
        # Soft delete: marca como excluído sem apagar o registro
        return Database.execute(
            "UPDATE Editoras SET deletado = 'S', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )