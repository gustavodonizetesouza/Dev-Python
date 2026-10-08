"""Diálogo de cadastro de módulos."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView,
)
from PySide6.QtCore import Qt
from database.models import ModuloRepositorio


class ModulosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastro de Módulos")
        self.resize(420, 420)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Módulos disponíveis para os casos de teste:"))

        self.tabela = QTableWidget(0, 2)
        self.tabela.setHorizontalHeaderLabels(["ID", "Módulo"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 50)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        linha_novo = QHBoxLayout()
        self.ed_nome = QLineEdit()
        self.ed_nome.setPlaceholderText("Ex.: SIGAINT")
        btn_adicionar = QPushButton("Adicionar")
        btn_adicionar.clicked.connect(self.adicionar)
        linha_novo.addWidget(self.ed_nome)
        linha_novo.addWidget(btn_adicionar)
        layout.addLayout(linha_novo)

        linha_botoes = QHBoxLayout()
        btn_excluir = QPushButton("Excluir Selecionado")
        btn_excluir.clicked.connect(self.excluir)
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        linha_botoes.addWidget(btn_excluir)
        linha_botoes.addStretch()
        linha_botoes.addWidget(btn_fechar)
        layout.addLayout(linha_botoes)

        self.carregar()

    def carregar(self):
        modulos = ModuloRepositorio.listar()
        self.tabela.setRowCount(len(modulos))
        for i, m in enumerate(modulos):
            id_item = QTableWidgetItem(str(m["id"]))
            id_item.setData(Qt.UserRole, m["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(m["nome"]))

    def adicionar(self):
        nome = self.ed_nome.text().strip()
        if not nome:
            QMessageBox.information(self, "Aviso", "Informe o nome do módulo.")
            return
        _, erro = ModuloRepositorio.inserir(nome)
        if erro:
            QMessageBox.warning(
                self, "Erro", f"Não foi possível adicionar:\n{erro}")
            return
        self.ed_nome.clear()
        self.carregar()

    def excluir(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Aviso", "Selecione um módulo.")
            return
        modulo_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        if not ModuloRepositorio.excluir(modulo_id):
            QMessageBox.warning(
                self, "Módulo em uso",
                "Este módulo está vinculado a casos de teste. Exclua ou reatribua os casos primeiro.")
            return
        self.carregar()
