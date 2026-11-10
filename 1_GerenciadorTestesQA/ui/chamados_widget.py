"""Aba Chamados — lista, filtros, KPIs, abertura e edição manual."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QMessageBox, QHeaderView,
    QGridLayout, QApplication,
)
from PySide6.QtCore import Qt, Signal

from database.models_chamados import ChamadoRepositorio
from .chamado_dialog import ChamadoDialog
from .chamado_detalhe_dialog import ChamadoDetalheDialog
from .sla_config_dialog import SlaConfigDialog


class ChamadosWidget(QWidget):
    chamadoMudou = Signal(object)

    def __init__(self, usuario_logado=None):
        super().__init__()
        self.usuario_logado = usuario_logado or {}
        self._build_ui()
        self.carregar()

    # ---------- UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.grid_kpi = QGridLayout()
        self.lbl_kpis = {}
        rotulos = [
            ("total", "Total"), ("abertos", "Abertos"),
            ("atendimento", "Em atend."), ("aguardando", "Aguard."),
            ("resolvidos", "Resolvidos"), ("encerrados", "Encerrados"),
            ("sla_atrasado", "SLA atrasado"),
        ]
        for i, (chave, rotulo) in enumerate(rotulos):
            self.grid_kpi.addWidget(QLabel(f"<b>{rotulo}</b>"), 0, i)
            lbl = QLabel("0")
            lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
            self.lbl_kpis[chave] = lbl
            self.grid_kpi.addWidget(lbl, 1, i)
        layout.addLayout(self.grid_kpi)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Status:"))
        self.cb_filtro_status = QComboBox()
        self.cb_filtro_status.addItem("Todos", None)
        for s in ChamadoRepositorio.STATUS_OPCOES:
            self.cb_filtro_status.addItem(s, s)
        self.cb_filtro_status.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro_status)

        topo.addWidget(QLabel("Tipo:"))
        self.cb_filtro_tipo = QComboBox()
        self.cb_filtro_tipo.addItem("Todos", None)
        for t in ChamadoRepositorio.TIPO_OPCOES:
            self.cb_filtro_tipo.addItem(t, t)
        self.cb_filtro_tipo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro_tipo)

        topo.addWidget(QLabel("Busca:"))
        self.ed_busca = QLineEdit()
        self.ed_busca.setPlaceholderText("Título, descrição ou código")
        self.ed_busca.textChanged.connect(self.carregar)
        topo.addWidget(self.ed_busca, 1)
        layout.addLayout(topo)

        # Grid — Solicitante incluído (melhoria 3)
        self.tabela = QTableWidget(0, 11)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Título", "Tipo", "Prioridade", "Status",
             "Responsável", "Solicitante", "SLA", "Tarefas", "Aberto em"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 90)
        self.tabela.setColumnWidth(3, 85)
        self.tabela.setColumnWidth(4, 82)
        self.tabela.setColumnWidth(5, 125)
        self.tabela.setColumnWidth(6, 115)
        self.tabela.setColumnWidth(7, 130)
        self.tabela.setColumnWidth(8, 78)
        self.tabela.setColumnWidth(9, 72)
        self.tabela.setColumnWidth(10, 135)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_detalhe_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Chamado")
        btn_editar = QPushButton("Editar")           # melhoria 1
        btn_abrir = QPushButton("Abrir")
        btn_excluir = QPushButton("Excluir")
        btn_config_sla = QPushButton("Configurar SLA...")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_abrir.clicked.connect(self.abrir_detalhe)
        btn_excluir.clicked.connect(self.excluir)
        btn_config_sla.clicked.connect(self.configurar_sla)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_abrir)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        botoes.addWidget(btn_config_sla)
        layout.addLayout(botoes)

    def _atualizar_kpis(self):
        try:
            k = ChamadoRepositorio.kpis()
        except Exception:
            k = {}
        for chave, lbl in self.lbl_kpis.items():
            lbl.setText(str(k.get(chave, 0)))
        if k.get("sla_atrasado", 0) > 0:
            self.lbl_kpis["sla_atrasado"].setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #C62828;")
        else:
            self.lbl_kpis["sla_atrasado"].setStyleSheet(
                "font-size: 16px; font-weight: bold;")

    def carregar(self):
        try:
            self.tabela.setUpdatesEnabled(False)
            self._atualizar_kpis()
            chamados = ChamadoRepositorio.listar(
                filtro_status=self.cb_filtro_status.currentData(),
                filtro_tipo=self.cb_filtro_tipo.currentData(),
                busca=self.ed_busca.text().strip() or None)
            self.tabela.setRowCount(len(chamados))
            for i, c in enumerate(chamados):
                id_item = QTableWidgetItem(str(c["id"]))
                id_item.setData(Qt.UserRole, c["id"])
                self.tabela.setItem(i, 0, id_item)
                self.tabela.setItem(i, 1, QTableWidgetItem(c["codigo"]))
                self.tabela.setItem(i, 2, QTableWidgetItem(c["titulo"]))
                self.tabela.setItem(i, 3, QTableWidgetItem(c.get("tipo") or ""))
                self.tabela.setItem(i, 4, QTableWidgetItem(c.get("prioridade") or ""))
                self.tabela.setItem(i, 5, QTableWidgetItem(c.get("status") or ""))
                self.tabela.setItem(i, 6, QTableWidgetItem(c.get("responsavel") or ""))
                self.tabela.setItem(i, 7, QTableWidgetItem(c.get("solicitante") or ""))
                sla_item = QTableWidgetItem(
                    "⚠ ATRASADO" if c.get("sla_atrasado") else "OK")
                if c.get("sla_atrasado"):
                    sla_item.setForeground(Qt.red)
                self.tabela.setItem(i, 8, sla_item)
                tt = c.get("tarefas_total") or 0
                to = c.get("tarefas_ok") or 0
                self.tabela.setItem(i, 9, QTableWidgetItem(f"{to}/{tt}"))
                self.tabela.setItem(i, 10, QTableWidgetItem(c.get("aberto_em") or ""))
        except Exception as e:
            QMessageBox.critical(self, "Erro ao carregar chamados",
                                 f"Não foi possível carregar os chamados:\n{e}")
            return
        finally:
            self.tabela.setUpdatesEnabled(True)
            self.tabela.viewport().update()
            QApplication.processEvents()

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_detalhe_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.abrir_detalhe()

    def novo(self):
        dlg = ChamadoDialog(self, usuario_logado=self.usuario_logado)
        if not dlg.exec():
            return
        novo_id = None
        try:
            novo_id, codigo = ChamadoRepositorio.inserir(
                dlg.dados(), autor_login=self.usuario_logado.get("login"))
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar chamado",
                                 f"Não foi possível gravar o chamado:\n{e}")
        finally:
            self.carregar()
        if novo_id is not None:
            self._selecionar_por_id(novo_id)
            self._abrir_detalhe_id(novo_id)
            self.carregar()
            self._selecionar_por_id(novo_id)

    def editar(self):
        """Melhoria 1 — edita o cabeçalho do chamado selecionado."""
        chamado_id = self._selecionado()
        if not chamado_id:
            QMessageBox.information(self, "Aviso", "Selecione um chamado.")
            return
        chamado = ChamadoRepositorio.obter(chamado_id)
        if not chamado:
            QMessageBox.warning(self, "Aviso", "Chamado não encontrado.")
            self.carregar()
            return
        dlg = ChamadoDialog(self, chamado=chamado,
                            usuario_logado=self.usuario_logado)
        if not dlg.exec():
            return
        try:
            ok, msg = ChamadoRepositorio.atualizar(
                chamado_id, dlg.dados(),
                autor_login=self.usuario_logado.get("login"))
        except Exception as e:
            QMessageBox.critical(self, "Erro ao atualizar chamado",
                                 f"Não foi possível atualizar:\n{e}")
            self.carregar()
            return
        if not ok:
            QMessageBox.warning(self, "Atenção", msg)
        self.carregar()
        self._selecionar_por_id(chamado_id)

    def _selecionar_por_id(self, chamado_id):
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, 0)
            if item and item.data(Qt.UserRole) == chamado_id:
                self.tabela.setCurrentCell(linha, 0)
                self.tabela.scrollToItem(item)
                return

    def abrir_detalhe(self):
        chamado_id = self._selecionado()
        if not chamado_id:
            QMessageBox.information(self, "Aviso", "Selecione um chamado.")
            return
        self._abrir_detalhe_id(chamado_id)

    def _abrir_detalhe_id(self, chamado_id):
        dlg = ChamadoDetalheDialog(self, chamado_id=chamado_id,
                                   usuario_logado=self.usuario_logado)
        dlg.exec()
        self.carregar()
        self._selecionar_por_id(chamado_id)

    def excluir(self):
        chamado_id = self._selecionado()
        if not chamado_id:
            QMessageBox.information(self, "Aviso", "Selecione um chamado.")
            return
        resp = QMessageBox.question(
            self, "Confirmar",
            "Excluir este chamado?\n"
            "Subtarefas e histórico dele TAMBÉM serão excluídos.")
        if resp != QMessageBox.Yes:
            return
        try:
            ChamadoRepositorio.excluir(chamado_id)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao excluir chamado",
                                 f"Não foi possível excluir:\n{e}")
            return
        self.carregar()

    def configurar_sla(self):
        dlg = SlaConfigDialog(self)
        dlg.exec()
        self.carregar()