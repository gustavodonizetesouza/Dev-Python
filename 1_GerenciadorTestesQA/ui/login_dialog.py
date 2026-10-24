"""Tela de Login — autentica o usuário do sistema (Fase 1).

O login é exibido antes da janela principal. Sem autenticação, o app não abre.

SEGURANÇA: a tela NUNCA exibe credenciais (nem dicas de usuário/senha padrão) —
credential disclosure na tela de login é vetor de ataque. O primeiro acesso
(admin com senha padrão) fica documentado apenas no manual técnico, e o
administrador deve trocar a senha imediatamente após o primeiro login.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout,
    QLabel, QMessageBox, QCheckBox,
)
from database.acessos import UsuarioSistemaRepositorio


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.usuario = None
        self.setWindowTitle("Login — Gerenciador de Testes QA")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Acesso ao Gerenciador de Testes QA</b>"))

        form = QFormLayout()
        self.ed_login = QLineEdit()
        self.ed_login.setPlaceholderText("seu.login")
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.Password)
        self.ed_senha.setPlaceholderText("senha")
        form.addRow("Usuário:", self.ed_login)
        form.addRow("Senha:", self.ed_senha)
        layout.addLayout(form)

        self.cb_mostrar = QCheckBox("Mostrar senha")
        self.cb_mostrar.toggled.connect(self._mostrar_senha)
        layout.addWidget(self.cb_mostrar)

        botoes = QHBoxLayout()
        btn_entrar = QPushButton("Entrar")
        btn_entrar.setDefault(True)
        btn_sair = QPushButton("Sair")
        btn_entrar.clicked.connect(self._entrar)
        btn_sair.clicked.connect(self.reject)
        botoes.addStretch()
        botoes.addWidget(btn_entrar)
        botoes.addWidget(btn_sair)
        layout.addLayout(botoes)

        self.ed_login.returnPressed.connect(self._entrar)
        self.ed_senha.returnPressed.connect(self._entrar)

    def _mostrar_senha(self, marcado):
        self.ed_senha.setEchoMode(QLineEdit.Normal if marcado else QLineEdit.Password)

    def _entrar(self):
        login = self.ed_login.text().strip()
        senha = self.ed_senha.text()
        if not login or not senha:
            QMessageBox.warning(self, "Login", "Informe usuário e senha.")
            return
        try:
            usuario = UsuarioSistemaRepositorio.autenticar(login, senha)
        except Exception:
            import os
            import traceback
            try:
                with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                          "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc())
                    f.write("\n" + "=" * 60 + "\n")
            except Exception:
                pass
            traceback.print_exc()
            QMessageBox.critical(self, "Erro", "Falha ao autenticar. Veja erros.log")
            return
        if not usuario:
            # Mensagem genérica de propósito: não revela se o login existe
            # (evita user enumeration — atacante não distingue usuário
            # inexistente de senha errada)
            QMessageBox.warning(self, "Login", "Usuário ou senha inválidos.")
            self.ed_senha.clear()
            self.ed_senha.setFocus()
            return
        self.usuario = usuario
        self.accept()