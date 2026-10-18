"""Widget de Execução — execução dos casos de teste do ciclo selecionado.

EXECUÇÃO POR ETAPAS: casos com etapas de validação são executados etapa a
etapa (status, % e horas de cada etapa) e o caso é TOTALIZADO automaticamente
(status consolidado, % médio, soma das horas). Casos sem etapas seguem o modo
manual. A aba SEMPRE acompanha o ciclo selecionado na aba Ciclos.

CORES ADAPTATIVAS: KPIs do topo e linha de totalização usam cor de destaque
ajustada ao tema (claro/escuro) — legível em ambos.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QTextEdit, QFormLayout, QMessageBox,
    QDialog, QDialogButtonBox, QHeaderView, QDoubleSpinBox, QSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from database.models import (
    CasoRepositorio, CicloRepositorio, UsuarioRepositorio,
    CasoEtapaRepositorio,
)
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


def _tema_escuro(widget):
    """Detecta tema escuro pela luminância da cor de fundo da paleta."""
    try:
        cor = widget.palette().color(QPalette.Window)
        return cor.lightness() < 128
    except Exception:
        return False


def _cor_destaque(widget):
    """Azul de destaque legível no tema atual (escuro no claro, claro no escuro)."""
    if _tema_escuro(widget):
        return "#7cb8e8"
    return "#1f5c8b"


class ExecucaoDialog(QDialog):
    """Execução de um caso: por etapas (com totalização) ou manual."""

    def __init__(self, parent=None, caso=None):
        super().__init__(parent)
        self.caso = caso
        self.setWindowTitle("Atualizar Execução" if caso else "Execução")
        self.setMinimumWidth(680)

        etapas = []
        if caso and caso.get("id"):
            try:
                etapas = CasoEtapaRepositorio.listar(caso["id"])
            except Exception:
                _log_erro()
                etapas = []
        self._tem_etapas = bool(etapas)

        layout = QVBoxLayout(self)

        self.lbl_caso = QLabel("")
        layout.addWidget(self.lbl_caso)

        if self._tem_etapas:
            layout.addWidget(QLabel(
                "<b>Execução por etapa</b> — informe status, % e horas de cada "
                "etapa; o caso é totalizado automaticamente:"))
            self.grade = QTableWidget(0, 6)
            self.grade.setHorizontalHeaderLabels(
                ["Ordem", "Etapa (validação)", "Rotina vinculada", "Status", "%", "Horas"])
            self.grade.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.grade.setColumnWidth(0, 50)
            self.grade.setColumnWidth(2, 170)
            self.grade.setColumnWidth(3, 115)
            self.grade.setColumnWidth(4, 70)
            self.grade.setColumnWidth(5, 75)
            self.grade.setSelectionBehavior(QTableWidget.SelectRows)
            self.grade.setEditTriggers(QTableWidget.NoEditTriggers)
            self.grade.setFixedHeight(min(120 + len(etapas) * 32, 340))
            layout.addWidget(self.grade)
            self._montar_grade(etapas)

            self.lbl_total = QLabel("")
            self.lbl_total.setStyleSheet(
                f"font-weight: bold; color:{_cor_destaque(self)};")
            layout.addWidget(self.lbl_total)
            self._recalcular_total()
        else:
            layout.addWidget(QLabel(
                "Este caso não tem etapas de validação — informe a execução "
                "direto abaixo. Para executar por etapas, use 'Etapas do "
                "Ciclo...' na aba Casos do Ciclo."))

        form = QFormLayout()
        if not self._tem_etapas:
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
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        form.addRow("Responsável:", self.cb_responsavel)

        if not self._tem_etapas:
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

        layout.addLayout(form)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        if caso:
            self._preencher(caso)

    # ---------- Grade de etapas (modo com etapas) ----------
    def _montar_grade(self, etapas):
        self.grade.setRowCount(len(etapas))
        for i, e in enumerate(etapas):
            id_item = QTableWidgetItem(str(e.get("ordem") or i + 1))
            id_item.setData(Qt.UserRole, e["id"])
            self.grade.setItem(i, 0, id_item)
            self.grade.setItem(i, 1, QTableWidgetItem(e.get("nome") or ""))
            rot = ""
            if e.get("rotina_id"):
                rot = (f"{e.get('rotina_codigo') or ''} — "
                       f"{e.get('rotina_nome') or ''}").strip()
            self.grade.setItem(i, 2, QTableWidgetItem(rot))

            cmb = QComboBox()
            cmb.addItems(CasoEtapaRepositorio.STATUS_OPCOES)
            idx = cmb.findText(e.get("status") or "Nao iniciada")
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.currentIndexChanged.connect(
                lambda _idx, row=i: self._status_etapa_mudou(row))
            self.grade.setCellWidget(i, 3, cmb)

            sp_pct = QSpinBox()
            sp_pct.setRange(0, 100)
            sp_pct.setSuffix(" %")
            sp_pct.setValue(int(e.get("percentual") or 0))
            sp_pct.valueChanged.connect(self._recalcular_total)
            self.grade.setCellWidget(i, 4, sp_pct)

            sp_horas = QDoubleSpinBox()
            sp_horas.setRange(0, 99999)
            sp_horas.setDecimals(2)
            sp_horas.setSuffix(" h")
            sp_horas.setValue(float(e.get("horas_reais") or 0))
            sp_horas.valueChanged.connect(self._recalcular_total)
            self.grade.setCellWidget(i, 5, sp_horas)

    def _status_etapa_mudou(self, row):
        cmb = self.grade.cellWidget(row, 3)
        sp_pct = self.grade.cellWidget(row, 4)
        if cmb and sp_pct:
            if cmb.currentText() == "Passou":
                sp_pct.setValue(100)
            elif cmb.currentText() == "Nao iniciada":
                sp_pct.setValue(0)
        self._recalcular_total()

    def _recalcular_total(self):
        if not getattr(self, "_tem_etapas", False):
            return
        statuses, pcts, horas = [], [], 0.0
        for i in range(self.grade.rowCount()):
            cmb = self.grade.cellWidget(i, 3)
            sp_pct = self.grade.cellWidget(i, 4)
            sp_h = self.grade.cellWidget(i, 5)
            if cmb:
                statuses.append(cmb.currentText())
            if sp_pct:
                pcts.append(sp_pct.value())
            if sp_h:
                horas += sp_h.value()
        if not statuses:
            return
        if "Falhou" in statuses:
            st = "Reprovado"
        elif all(s == "Passou" for s in statuses):
            st = "Aprovado"
        elif any(s in ("Passou", "Em andamento") for s in statuses):
            st = "Em andamento"
        else:
            st = "Nao iniciado"
        pct = round(sum(pcts) / len(pcts)) if pcts else 0
        self.lbl_total.setText(
            f"Totalização do caso → Status: {st}  |  % médio: {pct}%  |  "
            f"Horas: {round(horas, 2)} h")

    # ---------- Modo manual (sem etapas) ----------
    def _status_mudou(self, _idx):
        status = self.cb_status.currentText()
        if status in ("Aprovado", "Concluido"):
            self.sp_percentual.setValue(100)
        elif status == "Nao iniciado":
            self.sp_percentual.setValue(0)

    # ---------- Preencher / dados ----------
    def _preencher(self, caso):
        self.lbl_caso.setText(
            f"{caso.get('codigo') or ''} — "
            f"{caso.get('tarefa') or caso.get('descricao') or ''}".strip())
        if not self._tem_etapas:
            idx = self.cb_status.findText(
                caso.get("status_exec") or "Nao iniciado")
            if idx >= 0:
                self.cb_status.setCurrentIndex(idx)
            self.sp_percentual.setValue(int(caso.get("percentual") or 0))
            self.sp_horas.setValue(float(caso.get("horas_reais") or 0))
        resp = caso.get("responsavel") or ""
        idx = self.cb_responsavel.findText(resp)
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        elif resp:
            self.cb_responsavel.addItem(resp)
            self.cb_responsavel.setCurrentIndex(
                self.cb_responsavel.count() - 1)
        self.ed_evidencia.setPlainText(caso.get("evidencia") or "")
        self.ed_observacoes.setPlainText(caso.get("observacoes") or "")

    def dados(self):
        d = {
            "responsavel": self.cb_responsavel.currentText(),
            "evidencia": self.ed_evidencia.toPlainText().strip(),
            "observacoes": self.ed_observacoes.toPlainText().strip(),
        }
        if not self._tem_etapas:
            d["status_exec"] = self.cb_status.currentText()
            d["percentual"] = self.sp_percentual.value()
            d["horas_reais"] = self.sp_horas.value()
        return d

    def dados_etapas(self):
        """[(etapa_id, status, percentual, horas)] lido da grade (modo com etapas)."""
        if not self._tem_etapas:
            return []
        out = []
        for i in range(self.grade.rowCount()):
            item = self.grade.item(i, 0)
            etapa_id = item.data(Qt.UserRole) if item else None
            cmb = self.grade.cellWidget(i, 3)
            sp_pct = self.grade.cellWidget(i, 4)
            sp_h = self.grade.cellWidget(i, 5)
            if etapa_id and cmb:
                out.append((etapa_id, cmb.currentText(),
                            sp_pct.value() if sp_pct else 0,
                            sp_h.value() if sp_h else 0.0))
        return out


class ExecucaoWidget(QWidget):
    """Aba Execução — casos do ciclo selecionado + KPIs de execução."""

    def __init__(self):
        super().__init__()
        self.ciclo_id = None
        self._build_ui()
        self._aplicar_estilos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_ciclo = QLabel(
            "Selecione um ciclo na aba 'Ciclos' para executar os testes.")
        layout.addWidget(self.lbl_ciclo)

        # KPIs do ciclo (estilo aplicado em _aplicar_estilos)
        self.lbl_kpis = QLabel("")
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

    def _aplicar_estilos(self):
        """Aplica cores adaptativas ao tema atual (chamado no __init__ e showEvent)."""
        self.lbl_kpis.setStyleSheet(
            f"font-weight: bold; color:{_cor_destaque(self)};")

    def showEvent(self, event):
        """Toda vez que a aba fica visível: reaplica estilos e recarrega."""
        super().showEvent(event)
        self._aplicar_estilos()
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
            self.lbl_ciclo.setText(
                f"Ciclo: {nome} — execução dos casos abaixo.")
        else:
            self.lbl_ciclo.setText(
                "Selecione um ciclo na aba 'Ciclos' para executar os testes.")
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
            self.tabela.setItem(i, 4, QTableWidgetItem(
                c.get("status_exec") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(
                str(c.get("percentual") or 0)))
            self.tabela.setItem(i, 6, QTableWidgetItem(
                c.get("responsavel") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(
                str(c.get("horas_reais") or 0)))

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
            QMessageBox.information(
                self, "Aviso", "Selecione um ciclo na aba 'Ciclos' primeiro.")
            return
        caso_id = self._selecionado()
        if not caso_id:
            QMessageBox.information(
                self, "Aviso", "Selecione um caso na lista.")
            return
        caso = CasoRepositorio.obter(caso_id)
        if not caso:
            QMessageBox.information(self, "Aviso", "Caso não encontrado.")
            return
        dlg = ExecucaoDialog(self, caso)
        if dlg.exec():
            try:
                d = dlg.dados()
                etapas = dlg.dados_etapas()
                if etapas:
                    # 1) grava a execução de cada etapa
                    for etapa_id, status, pct, horas in etapas:
                        CasoEtapaRepositorio.atualizar_execucao(
                            etapa_id, status, pct, horas)
                    # 2) totaliza e grava no caso
                    tot = CasoEtapaRepositorio.totalizar_caso(caso_id)
                    CicloRepositorio.atualizar_execucao(
                        caso_id, tot["status_exec"], tot["percentual"],
                        d["responsavel"], tot["horas_reais"],
                        d["evidencia"], d["observacoes"])
                    msg = (f"Execução totalizada: {caso.get('codigo') or ''} "
                           f"→ {tot['status_exec']} ({tot['percentual']}%, "
                           f"{tot['horas_reais']} h).")
                else:
                    CicloRepositorio.atualizar_execucao(
                        caso_id, d["status_exec"], d["percentual"], d["responsavel"],
                        d["horas_reais"], d["evidencia"], d["observacoes"])
                    msg = (f"Execução atualizada: {caso.get('codigo') or ''} "
                           f"→ {d['status_exec']} ({d['percentual']}%).")
                self.carregar()
                QMessageBox.information(self, "Sucesso", msg)
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Não foi possível atualizar a execução. Veja erros.log")
