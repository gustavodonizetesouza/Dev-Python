from database import Database


class BibliotecaRepository:
    @staticmethod
    def list_all():
        return Database.query(
            """
            SELECT b.codigo, b.nome_livro, g.genero, a.nome_autor, e.editora,
                   b.quantidade_paginas, b.situacao, b.data_cadastro
            FROM Biblioteca b
            LEFT JOIN Generos g ON g.codigo = b.genero
            LEFT JOIN Autores a ON a.codigo = b.autor
            LEFT JOIN Editoras e ON e.codigo = b.editora
            WHERE ISNULL(b.deletado, '') = ''
            ORDER BY b.nome_livro
            """
        )

    @staticmethod
    def get_by_id(codigo):
        return Database.query("SELECT * FROM Biblioteca WHERE codigo = ?", (codigo,))

    @staticmethod
    def insert(dados: dict):
        return Database.execute(
            """
            INSERT INTO Biblioteca
                (nome_livro, genero, sub_titulo, codigo_barras, codigo_isbn,
                 quantidade_paginas, autor, editora, edicao, data_compra,
                 data_cadastro, data_inicio_leitura, data_fim_leitura, situacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?)
            """,
            (
                dados["nome_livro"], dados["genero"], dados["sub_titulo"],
                dados["codigo_barras"], dados["codigo_isbn"],
                dados["quantidade_paginas"], dados["autor"], dados["editora"],
                dados["edicao"], dados["data_compra"],
                dados["data_inicio_leitura"], dados["data_fim_leitura"],
                dados["situacao"],
            ),
        )

    @staticmethod
    def update(codigo, dados: dict):
        return Database.execute(
            """
            UPDATE Biblioteca SET
                nome_livro = ?, genero = ?, sub_titulo = ?, codigo_barras = ?,
                codigo_isbn = ?, quantidade_paginas = ?, autor = ?, editora = ?,
                edicao = ?, data_compra = ?, data_alteracao = GETDATE(),
                data_inicio_leitura = ?, data_fim_leitura = ?, situacao = ?
            WHERE codigo = ?
            """,
            (
                dados["nome_livro"], dados["genero"], dados["sub_titulo"],
                dados["codigo_barras"], dados["codigo_isbn"],
                dados["quantidade_paginas"], dados["autor"], dados["editora"],
                dados["edicao"], dados["data_compra"],
                dados["data_inicio_leitura"], dados["data_fim_leitura"],
                dados["situacao"], codigo,
            ),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Biblioteca SET deletado = 'S', data_exclusao = GETDATE() WHERE codigo = ?",
            (codigo,),
        )
