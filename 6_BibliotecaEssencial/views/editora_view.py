from views.crud_view import CrudView
from repositories.editora_repository import EditoraRepository


class EditoraView(CrudView):
    def __init__(self, master):
        super().__init__(
            master,
            repository=EditoraRepository,
            title="Editoras",
            fields=[
                {"name": "editora", "label": "Nome da Editora", "type": "text"},
            ],
            display_columns=[
                ("codigo", "Código"),
                ("editora", "Editora"),
                ("data_cadastro", "Cadastro"),
            ],
            column_widths={
                "codigo": 60,          # bem estreita, como pedido
                "editora": 320,
                "data_cadastro": 130,
            },
        )
