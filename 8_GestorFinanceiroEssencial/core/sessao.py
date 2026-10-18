"""Sessão do usuário logado — objeto leve em memória, por execução do app.

A sessão é populada pela janela de login e consumida pela janela principal
(para o título da lateral e para liberar a página Usuários aos admins).
"""


class Sessao:
    def __init__(self):
        self.usuario = None

    @property
    def logado(self) -> bool:
        return self.usuario is not None

    @property
    def eh_admin(self) -> bool:
        return bool(self.usuario and self.usuario.papel == "admin")

    @property
    def usuario_id(self):
        return self.usuario.id if self.usuario else None

    def iniciar(self, usuario):
        self.usuario = usuario

    def encerrar(self):
        self.usuario = None
