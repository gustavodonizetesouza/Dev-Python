"""Autenticação: janelas de login e de cadastro self-service.

Fluxo: main.py abre JanelaLogin → "Entrar" autentica e povoa a sessão →
accept(). "Criar conta" abre JanelaCadastro; ao concluir, o usuário já
entra logado. O primeiro usuário cadastrado no banco torna-se admin.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QVBoxLayout)

from core.seguranca import validar_senha_forte
from dominio.repositorio import ErroRegraNegocio, RepositorioUsuarios


class JanelaLogin(QDialog):
    """Login por e-mail + senha. Em caso de sucesso, povoa a sessão."""

    def __init__(self, repo_usuarios: RepositorioUsuarios, sessao, parent=None):
        super().__init__(parent)
        self.repo = repo_usuarios
        self.sessao = sessao
        self.setWindowTitle("Gestor Financeiro — Entrar")
        self.setMinimumWidth(420)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 20)
        raiz.setSpacing(12)

        titulo = QLabel("Gestor Financeiro")
        titulo.setObjectName("tituloApp")
        subtitulo = QLabel("Acesse sua conta para gerenciar suas finanças.")
        subtitulo.setObjectName("tituloCard")
        subtitulo.setWordWrap(True)
        raiz.addWidget(titulo)
        raiz.addWidget(subtitulo)
        raiz.addSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.ed_email = QLineEdit()
        self.ed_email.setPlaceholderText("seu@email.com")
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_senha.setPlaceholderText("Sua senha")
        form.addRow("E-mail", self.ed_email)
        form.addRow("Senha", self.ed_senha)
        raiz.addLayout(form)

        self.aviso = QLabel("")
        self.aviso.setObjectName("aviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        raiz.addWidget(self.aviso)

        linha_botoes = QHBoxLayout()
        bt_criar = QPushButton("Criar conta")
        bt_entrar = QPushButton("Entrar")
        bt_entrar.setProperty("variacao", "primaria")
        bt_entrar.setDefault(True)
        linha_botoes.addWidget(bt_criar)
        linha_botoes.addStretch()
        linha_botoes.addWidget(bt_entrar)
        raiz.addLayout(linha_botoes)

        bt_entrar.clicked.connect(self._entrar)
        bt_criar.clicked.connect(self._abrir_cadastro)
        self.ed_email.returnPressed.connect(self.ed_senha.setFocus)
        self.ed_senha.returnPressed.connect(self._entrar)

    def _mostrar_aviso(self, msg: str):
        self.aviso.setText(msg)
        self.aviso.show()

    def _entrar(self):
        email = self.ed_email.text().strip().lower()
        senha = self.ed_senha.text()
        if not email or not senha:
            self._mostrar_aviso("Informe e-mail e senha.")
            return
        try:
            usuario = self.repo.autenticar(email, senha)
        except ErroRegraNegocio as e:
            self._mostrar_aviso(str(e))
            return
        if usuario is None:
            # Mensagem genérica de propósito: não revelar se o e-mail existe.
            self._mostrar_aviso("E-mail ou senha inválidos.")
            return
        self.sessao.iniciar(usuario)
        self.accept()

    def _abrir_cadastro(self):
        dlg = JanelaCadastro(self.repo, self.sessao, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and self.sessao.logado:
            self.accept()


class JanelaCadastro(QDialog):
    """Cadastro self-service: nome, e-mail, senha e confirmação."""

    def __init__(self, repo_usuarios: RepositorioUsuarios, sessao, parent=None):
        super().__init__(parent)
        self.repo = repo_usuarios
        self.sessao = sessao
        self.setWindowTitle("Gestor Financeiro — Criar conta")
        self.setMinimumWidth(420)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 20)
        raiz.setSpacing(12)

        titulo = QLabel("Criar sua conta")
        titulo.setObjectName("tituloApp")
        raiz.addWidget(titulo)

        if self.repo.contar_usuarios() == 0:
            nota = QLabel("Primeiro cadastro do sistema — este usuário "
                          "será automaticamente o administrador.")
            nota.setObjectName("tituloCard")
            nota.setWordWrap(True)
            raiz.addWidget(nota)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.ed_nome = QLineEdit()
        self.ed_nome.setMaxLength(120)
        self.ed_email = QLineEdit()
        self.ed_email.setPlaceholderText("seu@email.com")
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_confirma = QLineEdit()
        self.ed_confirma.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Nome*", self.ed_nome)
        form.addRow("E-mail*", self.ed_email)
        form.addRow("Senha*", self.ed_senha)
        form.addRow("Confirmar*", self.ed_confirma)
        raiz.addLayout(form)

        self.aviso = QLabel("")
        self.aviso.setObjectName("aviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        raiz.addWidget(self.aviso)

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        botoes.button(QDialogButtonBox.StandardButton.Save).setText(
            "Criar conta")
        botoes.button(QDialogButtonBox.StandardButton.Cancel).setText("Voltar")
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        raiz.addWidget(botoes)

    def _mostrar_aviso(self, msg: str):
        self.aviso.setText(msg)
        self.aviso.show()

    @staticmethod
    def _email_valido(email: str) -> bool:
        return "@" in (email or "") and "." in email.split("@")[-1]

    def _salvar(self):
        nome = self.ed_nome.text().strip()
        email = self.ed_email.text().strip().lower()
        senha = self.ed_senha.text()
        confirma = self.ed_confirma.text()

        if not nome:
            self._mostrar_aviso("Informe seu nome.")
            return
        if not self._email_valido(email):
            self._mostrar_aviso("Informe um e-mail válido.")
            return
        if senha != confirma:
            self._mostrar_aviso("As senhas não conferem.")
            return
        erro = validar_senha_forte(senha)
        if erro:
            self._mostrar_aviso(erro)
            return

        try:
            usuario = self.repo.criar_usuario(nome, email, senha)
        except ErroRegraNegocio as e:
            self._mostrar_aviso(str(e))
            return

        self.sessao.iniciar(usuario)
        QMessageBox.information(
            self, "Conta criada",
            f"Bem-vindo(a), {usuario.nome}!\n\nSuas 11 categorias padrão já foram "
            "criadas. Cadastre uma conta e comece a usar o sistema.")
        self.accept()
