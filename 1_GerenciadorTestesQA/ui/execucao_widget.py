"""Widget de Execução — execução dos casos de teste do ciclo selecionado.

A aba SEMPRE acompanha o ciclo selecionado na aba Ciclos:
- definir_ciclo(ciclo_id) recebe o ciclo selecionado (conectado ao sinal
  cicloMudou da aba Ciclos);
- recarrega os casos e KPIs a cada mudança de ciclo E a cada vez que a aba
  fica visível (showEvent) — nunca mais fica "preso" num ciclo antigo.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QTextEdit, QFormLayout, QMessageBox,
    QDialog, QDialogButtonBox, QHeaderView, QDoubleSpinBox, QSpinBox,
)
from PySide6.QtCore import Qt
from database.models import CasoRepositorio, CicloRepositorio, UsuarioRepositorio
from .usuarios_dialog import UsuariosDialog

STATUS_EXEC = ["Nao iniciado", "Em andamento", "Aprovado",
               "Reprovado", "Bloqueado", "Concluido"]


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


class ExecucaoDialog(QDialog):
    """Diálogo para atualizar a execução de um caso (status, %, horas, evidência)."""

    def __init__(self, parent=None, caso=None):
        super().__init__(parent)
        self.caso = caso
        self.setWindowTitle("Atualizar Execução" if caso else "Execução")
        self.setMinimumWidth(500)

        form = QFormLayout()

        self.lbl_caso = QLabel("")
        form.addRow("Caso:", self.lbl_caso)

        self.cb_status = QComboBox()
        self.cb_status.addItems(STATUS_EXEC)
        self.cb_status.currentIndexChanged.connect(self._status_mudou)
        form.addRow("Status:", self.cb_status)

        self.sp_percentual = QSpinBox()
        self.sp_percentual.setRange(0, 100)
        self.sp_percentual.setSuffix(" %")
        form.addRow("Percentual:", self.sp_percentual)

        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"] for u in UsuarioRepositorio.listar()])
        form.addRow("Responsável:", self.cb_responsavel)

        self.sp_horas = QDoubleSpinBox()
        self.sp_horas.setRange(0, 99999)
        self.sp_horas.setDecimals(2)
        self.sp_horas.setSuffix(" h")
        form.addRow("Horas reais:", self.sp_horas)

        self.ed_evidencia = QTextEdit()
        self.ed_evidencia.setFixedHeight(60)
        form.addRow("Evidência:", self.ed_evidencia)

        self.ed_observacoes = QTextEdit()
        self.ed_observacoes.setFixedHeight(60)
        form.addRow("Observações:", self.ed_observacoes)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if caso:
            self._preencher(caso)

    def _status_mudou(self, _idx):
        status = self.cb_status.currentText()
        if status in ("Aprovado", "Concluido"):
            self.sp_percentual.setValue(100)
        elif status == "Nao iniciado":
            self.sp_percentual.setValue(0)

    def _preencher(self, caso):
        self.lbl_caso.setText(
            f"{caso.get('codigo') or ''} — {caso.get('tarefa') or caso.get('descricao') or ''}".strip())
        idx = self.cb_status.findText(caso.get("status_exec") or "Nao iniciado")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        self.sp_percentual.setValue(int(caso.get("percentual") or 0))
        resp = caso.get("responsavel") or ""
        idx = self.cb_responsavel.findText(resp)
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        elif resp:
            self.cb_responsavel.addItem(resp)
            self.cb_responsavel.setCurrentIndex(self.cb_responsavel.count() - 1)
        self.sp_horas.setValue(float(caso.get("horas_reais") or 0))
        self.ed_evidencia.setPlainText(caso.get("evidencia") or "")
        self.ed_observacoes.setPlainText(caso.get("observacoes") or "")

    def dados(self):
        return {
            "status_exec": self.cb_status.currentText(),
            "percentual": self.sp_percentual.value(),
            "responsavel": self.cb_responsavel.currentText(),
            "horas_reais": self.sp_horas.value(),
            "evidencia": self.ed_evidencia.toPlainText().strip(),
            "observacoes": self.ed_observacoes.toPlainText().strip(),
        }


class ExecucaoWidget(QWidget):
    """Aba Execução — casos do ciclo selecionado + KPIs de execução."""

    def __init__(self):
        super().__init__()
        self.ciclo_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_ciclo = QLabel("Selecione um ciclo na aba 'Ciclos' para executar os testes.")
        layout.addWidget(self.lbl_ciclo)

        # KPIs do ciclo
        self.lbl_kpis = QLabel("")
        self.lbl_kpis.setStyleSheet("font-weight: bold; color: #1f5c8b;")
        layout.addWidget(self.lbl_kpis)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Status:"))
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItem("Todos")
        self.cb_filtro.addItems(STATUS_EXEC)
        self.cb_filtro.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Tarefa", "Módulo", "Status", "%", "Responsável", "Horas Reais"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 110)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 110)
        self.tabela.setColumnWidth(5, 50)
        self.tabela.setColumnWidth(6, 110)
        self.tabela.setColumnWidth(7, 90)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_execucao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_exec = QPushButton("Atualizar Execução")
        btn_refresh = QPushButton("Atualizar Lista")
        btn_exec.clicked.connect(self.executar)
        btn_refresh.clicked.connect(self.carregar)
        botoes.addWidget(btn_exec)
        botoes.addWidget(btn_refresh)
        botoes.addStretch()
        layout.addLayout(botoes)

    def showEvent(self, event):
        """Toda vez que a aba fica visível, recarrega — nunca fica em ciclo antigo."""
        super().showEvent(event)
        self.carregar()

    def definir_ciclo(self, ciclo_id):
        """Chamado pelo sinal cicloMudou da aba Ciclos (e ao abrir o app)."""
        self.ciclo_id = ciclo_id
        if ciclo_id:
            try:
                ciclo = CicloRepositorio.obter(ciclo_id)
            except Exception:
                ciclo = None
            nome = ciclo["nome"] if ciclo else "?"
            self.lbl_ciclo.setText(f"Ciclo: {nome} — execução dos casos abaixo.")
        else:
            self.lbl_ciclo.setText("Selecione um ciclo na aba 'Ciclos' para executar os testes.")
            self.tabela.setRowCount(0)
            self.lbl_kpis.setText("")
        self.carregar()

    def _todos_casos(self):
        if not self.ciclo_id:
            return []
        try:
            return CasoRepositorio.listar(self.ciclo_id)
        except Exception:
            _log_erro()
            return []

    def carregar(self):
        if not self.ciclo_id:
            self.tabela.setRowCount(0)
            self.lbl_kpis.setText("")
            return

        casos = self._todos_casos()

        # Filtro por status
        filtro = self.cb_filtro.currentText()
        if filtro != "Todos":
            casos = [c for c in casos if c.get("status_exec") == filtro]

        self.tabela.setRowCount(len(casos))
        for i, c in enumerate(casos):
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.UserRole, c["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(c.get("codigo") or ""))
            self.tabela.setItem(i, 2, QTableWidgetItem(c.get("tarefa") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(c.get("modulo") or ""))
            self.tabela.setItem(i, 4, QTableWidgetItem(c.get("status_exec") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(str(c.get("percentual") or 0)))
            self.tabela.setItem(i, 6, QTableWidgetItem(c.get("responsavel") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(str(c.get("horas_reais") or 0)))

        # KPIs do ciclo
        try:
            k = CicloRepositorio.kpis(self.ciclo_id)
            self.lbl_kpis.setText(
                f"Total: {k['total']}  |  Executados: {k['executados']} "
                f"({k['perc_execucao']}%)  |  Aprovados: {k['aprovados']}  |  "
                f"Defeitos: {k['defeitos']}  |  % médio: {k['perc_medio']}%")
        except Exception:
            _log_erro()
            self.lbl_kpis.setText("")

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_execucao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.executar()

    def executar(self):
        if not self.ciclo_id:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo na aba 'Ciclos' primeiro.")
            return
        caso_id = self._selecionado()
        if not caso_id:
            QMessageBox.information(self, "Aviso", "Selecione um caso na lista.")
            return
        caso = CasoRepositorio.obter(caso_id)
        if not caso:
            QMessageBox.information(self, "Aviso", "Caso não encontrado.")
            return
        dlg = ExecucaoDialog(self, caso)
        if dlg.exec():
            try:
                d = dlg.dados()
                CicloRepositorio.atualizar_execucao(
                    caso_id, d["status_exec"], d["percentual"], d["responsavel"],
                    d["horas_reais"], d["evidencia"], d["observacoes"])
                self.carregar()
                QMessageBox.information(
                    self, "Sucesso",
                    f"Execução atualizada: {caso.get('codigo') or ''} "
                    f"→ {d['status_exec']} ({d['percentual']}%).")
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Não foi possível atualizar a execução. Veja erros.log")