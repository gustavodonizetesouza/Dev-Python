from views.crud_view import CrudView
from repositories.genero_repository import GeneroRepository


class GeneroView(CrudView):
    def __init__(self, master):
        super().__init__(
            master,
            repository=GeneroRepository,
            title="Gêneros",
            fields=[
                {"name": "genero", "label": "Nome do Gênero", "type": "text"},
            ],
            display_columns=[
                ("codigo", "Código"),
                ("genero", "Gênero"),
                ("data_cadastro", "Cadastro"),
            ],
        )
