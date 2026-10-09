"""Cadastro de tipos de ciclo (renomear sem perder vínculos)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QInputDialog,
)
from PySide6.QtCore import Qt
from database.models import TipoCicloRepositorio


class TiposCicloDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tipos de Ciclo")
        self.resize(420, 380)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("Tipos de ciclo cadastrados (usados na aba Ciclos):"))

        self.tabela = QTableWidget(0, 2)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 50)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
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
        tipos = TipoCicloRepositorio.listar()
        self.tabela.setRowCount(len(tipos))
        for i, t in enumerate(tipos):
            id_item = QTableWidgetItem(str(t["id"]))
            id_item.setData(Qt.UserRole, t["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(t["nome"]))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_renomear_linha(self, linha, coluna):
        self.renomear()

    def novo(self):
        nome, ok = QInputDialog.getText(self, "Novo Tipo", "Nome do tipo:")
        if ok and nome.strip():
            novo_id, erro = TipoCicloRepositorio.inserir(nome)
            if erro:
                QMessageBox.warning(self, "Erro", erro)
            else:
                self.carregar()

    def renomear(self):
        tipo_id = self._selecionado()
        if not tipo_id:
            QMessageBox.information(self, "Aviso", "Selecione um tipo.")
            return
        linha = self.tabela.currentRow()
        nome_atual = self.tabela.item(linha, 1).text()
        novo_nome, ok = QInputDialog.getText(
            self, "Renomear Tipo", "Novo nome:", text=nome_atual)
        if ok and novo_nome.strip():
            ok_ren, msg = TipoCicloRepositorio.atualizar(tipo_id, novo_nome)
            if ok_ren:
                QMessageBox.information(self, "Sucesso", msg)
                self.carregar()
            else:
                QMessageBox.warning(self, "Atenção", msg)

    def excluir(self):
        tipo_id = self._selecionado()
        if not tipo_id:
            QMessageBox.information(self, "Aviso", "Selecione um tipo.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir este tipo?") == QMessageBox.Yes:
            if TipoCicloRepositorio.excluir(tipo_id):
                self.carregar()
            else:
                QMessageBox.information(
                    self, "Não é possível",
                    "Este tipo está em uso por ciclos.\n"
                    "Use 'Renomear' em vez de excluir — os ciclos são atualizados.")
