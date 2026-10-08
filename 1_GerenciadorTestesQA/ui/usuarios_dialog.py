"""Diálogo de cadastro de usuários."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView, QFormLayout,
    QDialogButtonBox, QCheckBox,
)
from PySide6.QtCore import Qt
from database.models import UsuarioRepositorio


class UsuarioDialog(QDialog):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle(
            "Novo Usuário" if not usuario else "Editar Usuário")
        self.setMinimumWidth(400)

        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_cargo = QLineEdit()
        self.chk_ativo = QCheckBox("Usuário ativo")
        self.chk_ativo.setChecked(True)

        form.addRow("Nome:", self.ed_nome)
        form.addRow("E-mail:", self.ed_email)
        form.addRow("Cargo:", self.ed_cargo)
        form.addRow("", self.chk_ativo)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if usuario:
            self._preencher(usuario)

    def _preencher(self, usuario):
        self.ed_nome.setText(usuario["nome"])
        self.ed_email.setText(usuario.get("email") or "")
        self.ed_cargo.setText(usuario.get("cargo") or "")
        self.chk_ativo.setChecked(bool(usuario.get("ativo", 1)))

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o nome do usuário.")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "email": self.ed_email.text().strip(),
            "cargo": self.ed_cargo.text().strip(),
            "ativo": 1 if self.chk_ativo.isChecked() else 0,
        }


class UsuariosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastro de Usuários")
        self.resize(520, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Usuários disponíveis para vincular aos testes:"))

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Nome", "E-mail", "Cargo"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)

        self.carregar()

    def carregar(self):
        usuarios = UsuarioRepositorio.listar(apenas_ativos=False)
        self.tabela.setRowCount(len(usuarios))
        for i, u in enumerate(usuarios):
            id_item = QTableWidgetItem(str(u["id"]))
            id_item.setData(Qt.UserRole, u["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(u["nome"]))
            self.tabela.setItem(i, 2, QTableWidgetItem(u.get("email") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(u.get("cargo") or ""))

    def _usuario_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def novo(self):
        dlg = UsuarioDialog(self)
        if dlg.exec():
            UsuarioRepositorio.inserir(dlg.dados())
            self.carregar()

    def editar(self):
        usuario_id = self._usuario_selecionado()
        if not usuario_id:
            QMessageBox.information(self, "Aviso", "Selecione um usuário.")
            return
        usuarios = UsuarioRepositorio.listar(apenas_ativos=False)
        usuario = next((u for u in usuarios if u["id"] == usuario_id), None)
        dlg = UsuarioDialog(self, usuario)
        if dlg.exec():
            UsuarioRepositorio.atualizar(usuario_id, dlg.dados())
            self.carregar()

    def excluir(self):
        usuario_id = self._usuario_selecionado()
        if not usuario_id:
            QMessageBox.information(self, "Aviso", "Selecione um usuário.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir este usuário?") == QMessageBox.Yes:
            UsuarioRepositorio.excluir(usuario_id)
            self.carregar()
