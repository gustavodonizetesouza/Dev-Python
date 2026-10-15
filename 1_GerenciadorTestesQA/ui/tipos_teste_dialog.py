"""Cadastro de Tipos de Teste — Configurações → Tipos de Teste.

Os tipos aparecem no combo 'Tipo' da aba Casos do Ciclo.
Renomear propaga nos casos vinculados; excluir só quando nenhum caso usa.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QInputDialog,
)
from PySide6.QtCore import Qt
from database.models import TipoTesteRepositorio


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


class TiposTesteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tipos de Teste")
        self.resize(480, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Tipos disponíveis no campo 'Tipo' da tela de Casos do Ciclo.\n"
            "Renomear propaga nos casos vinculados; excluir só é permitido "
            "quando nenhum caso usar o tipo."))

        self.tabela = QTableWidget(0, 2)
        self.tabela.setHorizontalHeaderLabels(["ID", "Tipo de Teste"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 50)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.doubleClicked.connect(self._renomear)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo")
        btn_renomear = QPushButton("Renomear")
        btn_excluir = QPushButton("Excluir")
        btn_fechar = QPushButton("Fechar")
        btn_novo.clicked.connect(self._novo)
        btn_renomear.clicked.connect(self._renomear)
        btn_excluir.clicked.connect(self._excluir)
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_renomear)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

        self.carregar()

    def carregar(self):
        try:
            tipos = TipoTesteRepositorio.listar()
        except Exception:
            _log_erro()
            tipos = []
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
        item = self.tabela.item(linha, 0)
        return item.data(Qt.UserRole) if item else None

    def _novo(self):
        nome, ok = QInputDialog.getText(self, "Novo Tipo de Teste", "Nome do tipo:")
        if not ok or not nome.strip():
            return
        try:
            novo_id, erro = TipoTesteRepositorio.inserir(nome)
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro", "Não foi possível salvar. Veja erros.log")
            return
        if novo_id is None:
            QMessageBox.warning(self, "Atenção", erro or "Não foi possível salvar.")
            return
        self.carregar()
        for i in range(self.tabela.rowCount()):
            if self.tabela.item(i, 0).data(Qt.UserRole) == novo_id:
                self.tabela.selectRow(i)
                break

    def _renomear(self):
        tipo_id = self._selecionado()
        if not tipo_id:
            QMessageBox.information(self, "Aviso", "Selecione um tipo.")
            return
        nome_atual = self.tabela.item(self.tabela.currentRow(), 1).text()
        novo_nome, ok = QInputDialog.getText(
            self, "Renomear Tipo de Teste", "Novo nome:", text=nome_atual)
        if not ok or not novo_nome.strip():
            return
        try:
            sucesso, msg = TipoTesteRepositorio.atualizar(tipo_id, novo_nome)
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro", "Não foi possível renomear. Veja erros.log")
            return
        if sucesso:
            self.carregar()
        else:
            QMessageBox.warning(self, "Atenção", msg)

    def _excluir(self):
        tipo_id = self._selecionado()
        if not tipo_id:
            QMessageBox.information(self, "Aviso", "Selecione um tipo.")
            return
        nome = self.tabela.item(self.tabela.currentRow(), 1).text()
        if QMessageBox.question(self, "Confirmar",
                                f"Excluir o tipo '{nome}'?") != QMessageBox.Yes:
            return
        try:
            ok = TipoTesteRepositorio.excluir(tipo_id)
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro", "Não foi possível excluir. Veja erros.log")
            return
        if ok:
            self.carregar()
        else:
            QMessageBox.warning(
                self, "Atenção",
                f"O tipo '{nome}' está em uso por casos. Use Renomear para mantê-los.")