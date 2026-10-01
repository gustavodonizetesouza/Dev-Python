from views.crud_view import CrudView
from repositories.biblioteca_repository import BibliotecaRepository
from repositories.genero_repository import GeneroRepository
from repositories.autor_repository import AutorRepository
from repositories.editora_repository import EditoraRepository


def _opcoes_generos():
    return [(r[0], r[1]) for r in GeneroRepository.list_all()]


def _opcoes_autores():
    return [(r[0], r[1]) for r in AutorRepository.list_all()]


def _opcoes_editoras():
    return [(r[0], r[1]) for r in EditoraRepository.list_all()]


SITUACOES = ["Disponível", "Emprestado", "Lendo", "Reservado", "Indisponível"]


class BibliotecaView(CrudView):
    def __init__(self, master):
        super().__init__(
            master,
            repository=BibliotecaRepository,
            title="Biblioteca (Acervo)",
            fields=[
                {"name": "nome_livro", "label": "Nome do Livro", "type": "text"},
                {"name": "genero", "label": "Gênero", "type": "select",
                 "options_loader": _opcoes_generos},
                {"name": "sub_titulo", "label": "Subtítulo", "type": "text"},
                {"name": "codigo_barras", "label": "Código de Barras", "type": "text"},
                {"name": "codigo_isbn", "label": "ISBN", "type": "text"},
                {"name": "quantidade_paginas",
                    "label": "Qtd. Páginas", "type": "int"},
                {"name": "autor", "label": "Autor", "type": "select",
                 "options_loader": _opcoes_autores},
                {"name": "editora", "label": "Editora", "type": "select",
                 "options_loader": _opcoes_editoras},
                {"name": "edicao", "label": "Edição", "type": "text"},
                {"name": "situacao", "label": "Situação", "type": "select",
                 "options_loader": lambda: [(i, s) for i, s in enumerate(SITUACOES)]},
            ],
            display_columns=[
                ("codigo", "Código"),
                ("nome_livro", "Livro"),
                ("genero", "Gênero"),
                ("nome_autor", "Autor"),
                ("editora", "Editora"),
                ("quantidade_paginas", "Páginas"),
                ("situacao", "Situação"),
            ],
        )
