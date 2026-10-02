# ============================================
# repositories/biblioteca_repository.py
# CRUD da tabela Biblioteca (Acervo).
# Schema real: codigo, nome_livro, sub_titulo, codigo_barras,
# quantidade_paginas, autor, editora, data_compra, data_cadastro,
# data_alteracao, data_exclusao, situacao, deletado, genero,
# codigo_isbn, edicao, foto, data_fim_leitura, data_inicio_leitura
#
# Os métodos insert/update recebem um dict.
# Exclusão LÓGICA: preenche a coluna 'deletado' com '*'
# (padrão do ASP.NET), ocultando o registro das listagens.
# ============================================
from database import Database


class BibliotecaRepository:
    @staticmethod
    def list_all():
        """Lista os livros com os NOMES de autor/editora/gênero (JOIN)."""
        return Database.query(
            "SELECT b.codigo, b.nome_livro, a.nome_autor, e.editora, g.genero, b.situacao "
            "FROM Biblioteca b "
            "LEFT JOIN Autores a ON b.autor = a.codigo "
            "LEFT JOIN Editoras e ON b.editora = e.codigo "
            "LEFT JOIN Generos g ON b.genero = g.codigo "
            "WHERE ISNULL(b.deletado, '') = '' "
            "ORDER BY b.nome_livro"
        )

    @staticmethod
    def get_by_id(codigo):
        return Database.query("SELECT * FROM Biblioteca WHERE codigo = ?", (codigo,))

    @staticmethod
    def insert(dados: dict):
        return Database.execute(
            "INSERT INTO Biblioteca ("
            "nome_livro, sub_titulo, codigo_barras, quantidade_paginas, "
            "autor, editora, data_compra, data_cadastro, situacao, genero, "
            "codigo_isbn, edicao, data_fim_leitura, data_inicio_leitura"
            ") VALUES (?,?,?,?,?,?,?, GETDATE(), ?, ?, ?, ?, ?, ?)",
            (
                dados.get("nome_livro"),
                dados.get("sub_titulo"),
                dados.get("codigo_barras"),
                dados.get("quantidade_paginas"),
                dados.get("autor"),          # FK Autores
                dados.get("editora"),        # FK Editoras
                dados.get("data_compra"),
                dados.get("situacao"),       # int 1/2/3
                dados.get("genero"),         # FK Generos
                dados.get("codigo_isbn"),
                dados.get("edicao"),
                dados.get("data_fim_leitura"),
                dados.get("data_inicio_leitura"),
            ),
        )

    @staticmethod
    def update(codigo, dados: dict):
        return Database.execute(
            "UPDATE Biblioteca SET "
            "nome_livro = ?, sub_titulo = ?, codigo_barras = ?, quantidade_paginas = ?, "
            "autor = ?, editora = ?, data_compra = ?, situacao = ?, genero = ?, "
            "codigo_isbn = ?, edicao = ?, data_fim_leitura = ?, data_inicio_leitura = ?, "
            "data_alteracao = GETDATE() "
            "WHERE codigo = ?",
            (
                dados.get("nome_livro"),
                dados.get("sub_titulo"),
                dados.get("codigo_barras"),
                dados.get("quantidade_paginas"),
                dados.get("autor"),
                dados.get("editora"),
                dados.get("data_compra"),
                dados.get("situacao"),
                dados.get("genero"),
                dados.get("codigo_isbn"),
                dados.get("edicao"),
                dados.get("data_fim_leitura"),
                dados.get("data_inicio_leitura"),
                codigo,
            ),
        )

    @staticmethod
    def delete(codigo):
        return Database.execute(
            "UPDATE Biblioteca SET deletado = '*', data_exclusao = GETDATE() "
            "WHERE codigo = ?",
            (codigo,),
        )
