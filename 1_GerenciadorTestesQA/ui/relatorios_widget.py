"""Widget de relatórios e exportação."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFileDialog, QMessageBox,
)
from pathlib import Path
from database.models import CicloRepositorio
from reports.gerador import GeradorRelatorios


class RelatoriosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Ciclo:"))
        self.cb_ciclo = QComboBox()
        topo.addWidget(self.cb_ciclo)
        topo.addStretch()
        layout.addLayout(topo)

        self.lbl_kpis = QLabel("")
        layout.addWidget(self.lbl_kpis)

        botoes = QHBoxLayout()
        btn_excel = QPushButton("Exportar Excel")
        btn_pdf = QPushButton("Exportar PDF")
        btn_excel.clicked.connect(self.exportar_excel)
        btn_pdf.clicked.connect(self.exportar_pdf)
        botoes.addWidget(btn_excel)
        botoes.addWidget(btn_pdf)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar_ciclos(self):
        ciclos = CicloRepositorio.listar()
        self.cb_ciclo.clear()
        for c in ciclos:
            self.cb_ciclo.addItem(
                f"{c['nome']} ({c.get('versao') or ''})", c["id"])
        if ciclos:
            self.atualizar_kpis()

    def atualizar_kpis(self):
        idx = self.cb_ciclo.currentIndex()
        if idx < 0:
            self.lbl_kpis.setText("")
            return
        ciclo_id = self.cb_ciclo.itemData(idx)
        k = CicloRepositorio.kpis(ciclo_id)
        self.lbl_kpis.setText(
            f"Total: {k['total']} | Execução: {k['perc_execucao']}% | "
            f"Aprovação: {k['perc_aprovacao']}% | Defeitos: {k['defeitos']}")
        self.cb_ciclo.currentIndexChanged.connect(
            lambda _: self.atualizar_kpis())

    def _ciclo_atual(self):
        idx = self.cb_ciclo.currentIndex()
        if idx < 0:
            return None
        ciclo_id = self.cb_ciclo.itemData(idx)
        ciclos = CicloRepositorio.listar()
        ciclo = next((c for c in ciclos if c["id"] == ciclo_id), None)
        casos = CicloRepositorio.casos_do_ciclo(ciclo_id)
        kpis = CicloRepositorio.kpis(ciclo_id)
        return ciclo, casos, kpis

    def exportar_excel(self):
        dados = self._ciclo_atual()
        if not dados:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        ciclo, casos, _ = dados
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar Excel", f"relatorio_{ciclo['nome']}.xlsx", "Excel (*.xlsx)")
        if caminho:
            GeradorRelatorios.excel(casos, caminho)
            QMessageBox.information(
                self, "Sucesso", f"Excel gerado em:\n{caminho}")

    def exportar_pdf(self):
        dados = self._ciclo_atual()
        if not dados:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        ciclo, casos, kpis = dados
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar PDF", f"relatorio_{ciclo['nome']}.pdf", "PDF (*.pdf)")
        if caminho:
            GeradorRelatorios.pdf(casos, kpis, ciclo["nome"], caminho)
            QMessageBox.information(
                self, "Sucesso", f"PDF gerado em:\n{caminho}")
