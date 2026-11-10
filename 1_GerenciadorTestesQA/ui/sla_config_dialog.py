"""Configuração de SLA por prioridade (horas de resposta e resolução).

O SLA é um SNAPSHOT: ao abrir um chamado, os prazos são calculados a partir
da configuração vigente e gravados na linha do chamado. Alterar a
configuração aqui NÃO altera chamados já abertos — apenas os novos.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QDoubleSpinBox,
)
from PySide6.QtCore import Qt

from database.models_chamados import SlaConfigRepositorio


class SlaConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração de SLA por prioridade")
        self.resize(560, 340)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<b>Prazos por prioridade</b> (em horas).<br>"
            "<small>A alteração vale apenas para chamados abertos "
            "a partir de agora.</small>"))

        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(
            ["Prioridade", "Horas p/ resposta", "Horas p/ resolução"])
        self.tabela.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.tabela.setColumnWidth(1, 160)
        self.tabela.setColumnWidth(2, 160)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabela, 1)

        botoes = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_fechar = QPushButton("Fechar")
        btn_salvar.clicked.connect(self._salvar)
        btn_fechar.clicked.connect(self.accept)
        botoes.addStretch()
        botoes.addWidget(btn_salvar)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

        self._carregar()

    def _carregar(self):
        try:
            linhas = SlaConfigRepositorio.listar()
        except Exception as e:
            QMessageBox.critical(self, "Erro",
                                 f"Não foi possível carregar o SLA:\n{e}")
            return
        self.tabela.setRowCount(len(linhas))
        for i, s in enumerate(linhas):
            item_prio = QTableWidgetItem(s["prioridade"])
            item_prio.setFlags(item_prio.flags() & ~Qt.ItemIsEditable)
            self.tabela.setItem(i, 0, item_prio)

            sp_resp = QDoubleSpinBox()
            sp_resp.setRange(0, 9999)
            sp_resp.setDecimals(1)
            sp_resp.setSuffix(" h")
            sp_resp.setValue(float(s.get("horas_resposta") or 0))
            self.tabela.setCellWidget(i, 1, sp_resp)

            sp_reso = QDoubleSpinBox()
            sp_reso.setRange(0, 9999)
            sp_reso.setDecimals(1)
            sp_reso.setSuffix(" h")
            sp_reso.setValue(float(s.get("horas_resolucao") or 0))
            self.tabela.setCellWidget(i, 2, sp_reso)

    def _salvar(self):
        try:
            for i in range(self.tabela.rowCount()):
                prioridade = self.tabela.item(i, 0).text()
                sp_resp = self.tabela.cellWidget(i, 1)
                sp_reso = self.tabela.cellWidget(i, 2)
                SlaConfigRepositorio.atualizar(
                    prioridade, sp_resp.value(), sp_reso.value())
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar",
                                 f"Não foi possível salvar o SLA:\n{e}")
            return
        QMessageBox.information(self, "Sucesso", "SLA atualizado.")
        self.accept()