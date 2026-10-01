from views.crud_view import CrudView
from repositories.autor_repository import AutorRepository


class AutorView(CrudView):
    def __init__(self, master):
        super().__init__(
            master,
            repository=AutorRepository,
            title="Autores",
            fields=[
                {"name": "nome_autor", "label": "Nome do Autor", "type": "text"},
            ],
            display_columns=[
                ("codigo", "Código"),
                ("nome_autor", "Autor"),
                ("data_cadastro", "Cadastro"),
            ],
        )
