import flet as ft

from api_client import ApiError, api


def main(page: ft.Page) -> None:
    page.title = "Gestão Familiar"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 420
    page.window.height = 720
    page.window.center()

    # ---------- estado ----------
    listas: list[dict] = []
    lista_atual: dict | None = None
    campo_item = ft.TextField(label="Item", expand=True)
    campo_qtd = ft.TextField(label="Qtd", width=70,
                             value="1", keyboard_type=ft.KeyboardType.NUMBER)
    campo_preco = ft.TextField(
        label="Preço est. (R$)", width=110, keyboard_type=ft.KeyboardType.NUMBER)
    lista_view = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
    total_label = ft.Text("Total estimado: R$ 0,00",
                          size=18, weight=ft.FontWeight.BOLD)

    # ---------- helpers ----------
    def mostrar_erro(e: Exception) -> None:
        msg = e.mensagem if isinstance(e, ApiError) else str(e)
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=ft.Colors.RED_400)
        page.snack_bar.open = True
        page.update()

    def formatar(valor: float | None) -> str:
        return f"{valor:.2f}".replace(".", ",") if valor is not None else "—"

    def recarregar_listas() -> None:
        nonlocal listas
        listas = api.listar_listas()
        if listas:
            abrir_lista(listas[0]["id"])

    def abrir_lista(lista_id: int) -> None:
        nonlocal lista_atual
        lista_atual = next((l for l in listas if l["id"] == lista_id), None)
        if not lista_atual:
            return
        lista_view.controls.clear()
        for item in lista_atual["itens"]:
            lista_view.controls.append(
                ft.Checkbox(
                    label=f"{item['descricao']}  x{item['quantidade']:.0f}  "
                    f"({formatar(item['preco_estimado'])})",
                    value=item["marcado"],
                    on_change=lambda e, i=item: marcar(i, e.control.value),
                )
            )
        atualizar_total()
        page.update()

    def atualizar_total() -> None:
        total = lista_atual["total_estimado"] if lista_atual else 0
        total_label.value = f"Total estimado: R$ {formatar(total)}"

    def marcar(item: dict, valor: bool) -> None:
        api.marcar_item(item["id"], valor)
        item["marcado"] = valor

    # ---------- ações ----------
    def ao_login(e: ft.ControlEvent) -> None:
        try:
            api.login(campo_email.value, campo_senha.value)
            recarregar_listas()
            page.views.clear()
            page.views.append(tela_principal())
            page.update()
        except Exception as err:
            mostrar_erro(err)

    def ao_registrar(e: ft.ControlEvent) -> None:
        try:
            api.registrar(campo_nome.value, campo_email.value,
                          campo_senha.value)
            ao_login(e)
        except Exception as err:
            mostrar_erro(err)

    def ao_criar_lista(e: ft.ControlEvent) -> None:
        nome = campo_nova_lista.value.strip()
        if not nome:
            return
        api.criar_lista(nome)
        campo_nova_lista.value = ""
        recarregar_listas()
        page.update()

    def ao_adicionar_item(e: ft.ControlEvent) -> None:
        descricao = campo_item.value.strip()
        if not descricao or not lista_atual:
            return
        try:
            qtd = float(campo_qtd.value.replace(",", ".") or 1)
        except ValueError:
            qtd = 1
        try:
            preco = float(campo_preco.value.replace(",", ".")
                          ) if campo_preco.value else None
        except ValueError:
            preco = None
        api.adicionar_item(lista_atual["id"], descricao, qtd, preco)
        campo_item.value = ""
        campo_preco.value = ""
        recarregar_listas()
        page.update()

    def ao_selecionar_lista(e: ft.ControlEvent) -> None:
        abrir_lista(int(e.control.value))

    # ---------- telas ----------
    def tela_login() -> ft.View:
        return ft.View(
            route="/login",
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=16,
                        controls=[
                            ft.Icon(ft.Icons.FAMILY_RESTROOM, size=64,
                                    color=ft.Colors.BLUE_600),
                            ft.Text("Gestão Familiar", size=28,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Organize finanças, patrimônio e compras da família", size=13),
                            ft.Container(height=12),
                            campo_email,
                            campo_senha,
                            ft.FilledButton("Entrar", width=280,
                                            on_click=ao_login),
                            ft.TextButton(
                                "Criar conta", on_click=lambda e: ir_para("/registro")),
                        ],
                    ),
                )
            ],
        )

    def tela_registro() -> ft.View:
        return ft.View(
            route="/registro",
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.center,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=16,
                        controls=[
                            ft.Icon(ft.Icons.PERSON_ADD, size=64,
                                    color=ft.Colors.BLUE_600),
                            ft.Text("Criar conta", size=24,
                                    weight=ft.FontWeight.BOLD),
                            campo_nome,
                            campo_email,
                            campo_senha,
                            ft.FilledButton(
                                "Cadastrar", width=280, on_click=ao_registrar),
                            ft.TextButton("Já tenho conta",
                                          on_click=lambda e: ir_para("/login")),
                        ],
                    ),
                )
            ],
        )

    def tela_principal() -> ft.View:
        campo_nova_lista = ft.TextField(
            label="Nova lista de compras", expand=True)
        campo_nova_lista.on_submit = ao_criar_lista

        dropdown = ft.Dropdown(
            label="Lista",
            options=[ft.dropdown.Option(str(l["id"]), l["nome"])
                     for l in listas],
            on_change=ao_selecionar_lista,
        )

        return ft.View(
            route="/principal",
            controls=[
                ft.AppBar(
                    title=ft.Text("Lista de Compras"),
                    actions=[
                        ft.IconButton(ft.Icons.LOGOUT,
                                      tooltip="Sair", on_click=ao_sair),
                    ],
                ),
                ft.Column(
                    expand=True,
                    controls=[
                        ft.Row([campo_nova_lista, ft.IconButton(
                            ft.Icons.ADD, on_click=ao_criar_lista)]),
                        dropdown,
                        ft.Divider(),
                        lista_view,
                        ft.Divider(),
                        total_label,
                        ft.Row(
                            [
                                campo_item,
                                campo_qtd,
                                campo_preco,
                                ft.IconButton(
                                    ft.Icons.ADD_CIRCLE, icon_size=32, on_click=ao_adicionar_item),
                            ]
                        ),
                    ],
                ),
            ],
        )

    def ir_para(rota: str) -> None:
        page.views.clear()
        page.views.append(tela_login() if rota ==
                          "/login" else tela_registro())
        page.update()

    def ao_sair(e: ft.ControlEvent) -> None:
        api.token = None
        ir_para("/login")

    # ---------- campos globais (usados em várias telas) ----------
    campo_nome = ft.TextField(label="Nome", width=280)
    campo_email = ft.TextField(
        label="E-mail", width=280, keyboard_type=ft.KeyboardType.EMAIL)
    campo_senha = ft.TextField(
        label="Senha", width=280, password=True, can_reveal_password=True)

    page.views.append(tela_login())
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
