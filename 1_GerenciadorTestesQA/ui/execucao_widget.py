"""Widget de execução dos testes de um ciclo."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QLineEdit, QTextEdit,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QFileDialog,
)
from PySide6.QtCore import Qt
from database.models import CicloRepositorio
from utils.helpers import STATUS_OPCOES


class ExecucaoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Seletor de ciclo
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Ciclo:"))
        self.cb_ciclo = QComboBox()
        self.cb_ciclo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_ciclo)
        topo.addStretch()
        layout.addLayout(topo)

        # KPIs
        self.lbl_kpis = QLabel("Selecione um ciclo para ver os KPIs.")
        layout.addWidget(self.lbl_kpis)

        # Tabela
        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Módulo", "Descrição", "Status", "%", "Responsável", "Evidência"])
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_executar = QPushButton("Registrar Execução")
        btn_executar.clicked.connect(self.registrar)
        botoes.addWidget(btn_executar)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar_ciclos(self):
        ciclos = CicloRepositorio.listar()
        self.cb_ciclo.blockSignals(True)
        self.cb_ciclo.clear()
        for c in ciclos:
            self.cb_ciclo.addItem(
                f"{c['nome']} ({c.get('versao') or 'sem versão'})", c["id"])
        self.cb_ciclo.blockSignals(False)
        if ciclos:
            self.carregar()

    def carregar(self):
        idx = self.cb_ciclo.currentIndex()
        if idx < 0:
            return
        ciclo_id = self.cb_ciclo.itemData(idx)
        casos = CicloRepositorio.casos_do_ciclo(ciclo_id)
        kpis = CicloRepositorio.kpis(ciclo_id)

        self.lbl_kpis.setText(
            f"Total: {kpis['total']} | Execução: {kpis['perc_execucao']}% | "
            f"Aprovação: {kpis['perc_aprovacao']}% | Defeitos: {kpis['defeitos']} | "
            f"Progresso médio: {kpis['perc_medio']}%"
        )

        self.tabela.setRowCount(len(casos))
        for i, c in enumerate(casos):
            valores = [str(c["id"]), c["codigo"], c["modulo"], c["descricao"],
                       c["status"], str(c["percentual"]), c.get(
                           "responsavel") or "",
                       c.get("evidencia") or ""]
            for j, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setData(Qt.UserRole, c["id"])
                self.tabela.setItem(i, j, item)

    def registrar(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(
                self, "Aviso", "Selecione um teste para registrar execução.")
            return
        cc_id = self.tabela.item(linha, 0).data(Qt.UserRole)

        dlg = QDialog(self)
        dlg.setWindowTitle("Registrar Execução")
        dlg.setMinimumWidth(460)
        layout = QVBoxLayout(dlg)

        form = QHBoxLayout()
        form.addWidget(QLabel("Status:"))
        cb_status = QComboBox()
        cb_status.addItems(STATUS_OPCOES)
        form.addWidget(cb_status)
        form.addWidget(QLabel("%:"))
        sp_perc = QSpinBox()
        sp_perc.setRange(0, 100)
        form.addWidget(sp_perc)
        layout.addLayout(form)

        form2 = QHBoxLayout()
        form2.addWidget(QLabel("Responsável:"))
        ed_resp = QLineEdit()
        form2.addWidget(ed_resp)
        form2.addWidget(QLabel("Horas:"))
        sp_horas = QSpinBox()
        sp_horas.setRange(0, 1000)
        form2.addWidget(sp_horas)
        layout.addLayout(form2)

        layout.addWidget(QLabel("Evidência (caminho do arquivo/print):"))
        ed_evidencia = QLineEdit()
        btn_anexar = QPushButton("Anexar...")
        linha_ev = QHBoxLayout()
        linha_ev.addWidget(ed_evidencia)
        linha_ev.addWidget(btn_anexar)
        layout.addLayout(linha_ev)

        def anexar():
            arquivo, _ = QFileDialog.getOpenFileName(
                dlg, "Selecionar evidência")
            if arquivo:
                ed_evidencia.setText(arquivo)
        btn_anexar.clicked.connect(anexar)

        layout.addWidget(QLabel("Observações:"))
        ed_obs = QTextEdit()
        ed_obs.setFixedHeight(80)
        layout.addWidget(ed_obs)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(botoes)

        def salvar():
            CicloRepositorio.atualizar_execucao(
                cc_id, cb_status.currentText(), sp_perc.value(),
                ed_resp.text().strip(), sp_horas.value(),
                ed_evidencia.text().strip(), ed_obs.toPlainText().strip())
            dlg.accept()
            self.carregar()

        botoes.accepted.connect(salvar)
        botoes.rejected.connect(dlg.reject)
        dlg.exec()
