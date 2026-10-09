"""Cadastro de módulos (CRUD completo, com renomeação sem perder vínculos)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QInputDialog,
)
from PySide6.QtCore import Qt
from database.models import ModuloRepositorio


class ModulosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Módulos")
        self.resize(420, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Módulos cadastrados:"))

        self.tabela = QTableWidget(0, 2)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 50)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        # Duplo clique também renomeia
        self.tabela.cellDoubleClicked.connect(self._abrir_renomear_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo")
        btn_renomear = QPushButton("Renomear")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo)
        btn_renomear.clicked.connect(self.renomear)
        btn_excluir.clicked.connect(self.excluir)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_renomear)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)

        self.carregar()

    def carregar(self):
        modulos = ModuloRepositorio.listar()
        self.tabela.setRowCount(len(modulos))
        for i, m in enumerate(modulos):
            id_item = QTableWidgetItem(str(m["id"]))
            id_item.setData(Qt.UserRole, m["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(m["nome"]))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_renomear_linha(self, linha, coluna):
        self.renomear()

    def novo(self):
        nome, ok = QInputDialog.getText(self, "Novo Módulo", "Nome do módulo:")
        if ok and nome.strip():
            novo_id, erro = ModuloRepositorio.inserir(nome)
            if erro:
                QMessageBox.warning(self, "Erro", erro)
            else:
                self.carregar()

    def renomear(self):
        """Renomeia o módulo (atualiza casos e melhorias vinculados)."""
        modulo_id = self._selecionado()
        if not modulo_id:
            QMessageBox.information(self, "Aviso", "Selecione um módulo.")
            return
        linha = self.tabela.currentRow()
        nome_atual = self.tabela.item(linha, 1).text()
        novo_nome, ok = QInputDialog.getText(
            self, "Renomear Módulo", "Novo nome:", text=nome_atual)
        if ok and novo_nome.strip():
            ok_ren, msg = ModuloRepositorio.atualizar(modulo_id, novo_nome)
            if ok_ren:
                QMessageBox.information(self, "Sucesso", msg)
                self.carregar()
            else:
                QMessageBox.warning(self, "Atenção", msg)

    def excluir(self):
        modulo_id = self._selecionado()
        if not modulo_id:
            QMessageBox.information(self, "Aviso", "Selecione um módulo.")
            return
        resp = QMessageBox.question(self, "Confirmar", "Excluir este módulo?")
        if resp == QMessageBox.Yes:
            if ModuloRepositorio.excluir(modulo_id):
                self.carregar()
            else:
                QMessageBox.information(
                    self, "Não é possível",
                    "Este módulo está em uso por casos de teste.\n"
                    "Use 'Renomear' em vez de excluir — assim os casos são atualizados.")
