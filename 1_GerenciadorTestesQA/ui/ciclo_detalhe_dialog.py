"""Detalhes do Ciclo: Etapas, Rotinas, Horas, Custos e Resumo (KPIs)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialogButtonBox, QHeaderView, QTabWidget, QWidget,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGridLayout, QDateEdit,
)
from PySide6.QtCore import Qt, QDate
from database.models import CicloDetalheRepositorio, CicloRepositorio, UsuarioRepositorio


def fmt_moeda(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        v = 0
    return f"R$ {v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _data_editada():
    ed = QDateEdit()
    ed.setCalendarPopup(True)
    ed.setDisplayFormat("yyyy-MM-dd")
    ed.setSpecialValueText(" ")
    ed.setMinimumDate(QDate(1900, 1, 1))
    ed.setDate(QDate(2000, 1, 1))
    return ed


def _valor_data(ed):
    if ed.date().toString("yyyy-MM-dd") == "2000-01-01":
        return ""
    return ed.date().toString("yyyy-MM-dd")


def _usuarios_combo(combo):
    combo.clear()
    combo.addItem("")
    combo.addItems([u["nome"] for u in UsuarioRepositorio.listar()])


class EtapaDialog(QDialog):
    def __init__(self, parent=None, etapa=None):
        super().__init__(parent)
        self.etapa = etapa
        self.setWindowTitle("Nova Etapa" if not etapa else "Editar Etapa")
        self.setMinimumWidth(480)
        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(60)
        self.cb_responsavel = QComboBox()
        _usuarios_combo(self.cb_responsavel)
        self.cb_status = QComboBox()
        self.cb_status.addItems(CicloDetalheRepositorio.STATUS_ETAPA_OPCOES)
        self.sp_percentual = QSpinBox()
        self.sp_percentual.setRange(0, 100)
        self.cb_status.currentTextChanged.connect(self._ajustar_percentual)
        self.sp_orcado = QDoubleSpinBox()
        self.sp_orcado.setRange(0, 999999999)
        self.sp_orcado.setDecimals(2)
        self.ed_inicio_prev = _data_editada()
        self.ed_fim_prev = _data_editada()

        form.addRow("Nome:", self.ed_nome)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Responsável:", self.cb_responsavel)
        form.addRow("Status:", self.cb_status)
        form.addRow("Percentual (%):", self.sp_percentual)
        form.addRow("Orçamento da etapa (R$):", self.sp_orcado)
        form.addRow("Início previsto:", self.ed_inicio_prev)
        form.addRow("Fim previsto:", self.ed_fim_prev)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)
        if etapa:
            self._preencher(etapa)

    def _ajustar_percentual(self, status):
        if status == "Concluída":
            self.sp_percentual.setValue(100)

    def _preencher(self, etapa):
        self.ed_nome.setText(etapa["nome"])
        self.ed_descricao.setPlainText(etapa.get("descricao") or "")
        idx = self.cb_responsavel.findText(etapa.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        idx = self.cb_status.findText(etapa.get("status") or "Não iniciada")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        self.sp_percentual.setValue(int(etapa.get("percentual") or 0))
        self.sp_orcado.setValue(float(etapa.get("custo_orcado") or 0))
        if etapa.get("data_prevista_inicio"):
            d = QDate.fromString(etapa["data_prevista_inicio"], "yyyy-MM-dd")
            if d.isValid():
                self.ed_inicio_prev.setDate(d)
        if etapa.get("data_prevista_fim"):
            d = QDate.fromString(etapa["data_prevista_fim"], "yyyy-MM-dd")
            if d.isValid():
                self.ed_fim_prev.setDate(d)

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome da etapa.")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "responsavel": self.cb_responsavel.currentText(),
            "status": self.cb_status.currentText(),
            "percentual": self.sp_percentual.value(),
            "custo_orcado": self.sp_orcado.value(),
            "data_prevista_inicio": _valor_data(self.ed_inicio_prev),
            "data_prevista_fim": _valor_data(self.ed_fim_prev),
        }


class RotinaDialog(QDialog):
    def __init__(self, parent=None, rotina=None, etapas=None):
        super().__init__(parent)
        self.rotina = rotina
        self.setWindowTitle("Nova Rotina" if not rotina else "Editar Rotina")
        self.setMinimumWidth(480)
        form = QFormLayout()
        self.cb_etapa = QComboBox()
        self.cb_etapa.addItem("", None)
        for e in (etapas or []):
            self.cb_etapa.addItem(e["nome"], e["id"])
        self.ed_nome = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(60)
        self.cb_status = QComboBox()
        self.cb_status.addItems(CicloDetalheRepositorio.STATUS_ROTINA_OPCOES)
        self.cb_responsavel = QComboBox()
        _usuarios_combo(self.cb_responsavel)
        self.sp_horas = QDoubleSpinBox()
        self.sp_horas.setRange(0, 99999)
        self.sp_horas.setDecimals(2)

        form.addRow("Etapa:", self.cb_etapa)
        form.addRow("Nome:", self.ed_nome)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Status:", self.cb_status)
        form.addRow("Responsável:", self.cb_responsavel)
        form.addRow("Horas estimadas:", self.sp_horas)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)
        if rotina:
            self._preencher(rotina)

    def _preencher(self, rotina):
        if rotina.get("etapa_id"):
            idx = self.cb_etapa.findData(rotina["etapa_id"])
            if idx >= 0:
                self.cb_etapa.setCurrentIndex(idx)
        self.ed_nome.setText(rotina["nome"])
        self.ed_descricao.setPlainText(rotina.get("descricao") or "")
        idx = self.cb_status.findText(rotina.get("status") or "Pendente")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(rotina.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.sp_horas.setValue(float(rotina.get("horas_estimadas") or 0))

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome da rotina.")
            return
        self.accept()

    def dados(self):
        return {
            "etapa_id": self.cb_etapa.currentData(),
            "nome": self.ed_nome.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "status": self.cb_status.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "horas_estimadas": self.sp_horas.value(),
        }


class HoraDialog(QDialog):
    def __init__(self, parent=None, etapas=None, rotinas=None):
        super().__init__(parent)
        self.setWindowTitle("Lançar Horas")
        self.setMinimumWidth(480)
        form = QFormLayout()
        self.cb_etapa = QComboBox()
        self.cb_etapa.addItem("", None)
        for e in (etapas or []):
            self.cb_etapa.addItem(e["nome"], e["id"])
        self.cb_rotina = QComboBox()
        self.cb_rotina.addItem("", None)
        for r in (rotinas or []):
            self.cb_rotina.addItem(f"{r['codigo']} — {r['nome']}", r["id"])
        self.cb_lancado = QComboBox()
        _usuarios_combo(self.cb_lancado)
        self.ed_data = _data_editada()
        self.sp_horas = QDoubleSpinBox()
        self.sp_horas.setRange(0, 99999)
        self.sp_horas.setDecimals(2)
        self.sp_custo_hora = QDoubleSpinBox()
        self.sp_custo_hora.setRange(0, 999999999)
        self.sp_custo_hora.setDecimals(2)
        self.ed_descricao = QLineEdit()

        form.addRow("Etapa:", self.cb_etapa)
        form.addRow("Rotina:", self.cb_rotina)
        form.addRow("Quem lançou:", self.cb_lancado)
        form.addRow("Data:", self.ed_data)
        form.addRow("Horas:", self.sp_horas)
        form.addRow("Custo por hora (R$):", self.sp_custo_hora)
        form.addRow("Descrição:", self.ed_descricao)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

    def _validar(self):
        if not self.cb_lancado.currentText():
            QMessageBox.warning(self, "Validação",
                                "Informe quem lançou as horas.")
            return
        if self.sp_horas.value() <= 0:
            QMessageBox.warning(
                self, "Validação", "Informe uma quantidade de horas maior que zero.")
            return
        self.accept()

    def dados(self):
        return {
            "etapa_id": self.cb_etapa.currentData(),
            "rotina_id": self.cb_rotina.currentData(),
            "lancado_por": self.cb_lancado.currentText(),
            "data": _valor_data(self.ed_data),
            "horas": self.sp_horas.value(),
            "custo_hora": self.sp_custo_hora.value(),
            "descricao": self.ed_descricao.text().strip(),
        }


class CustoDialog(QDialog):
    def __init__(self, parent=None, etapas=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Custo Adicional")
        self.setMinimumWidth(460)
        form = QFormLayout()
        self.ed_descricao = QLineEdit()
        self.cb_categoria = QComboBox()
        self.cb_categoria.addItems(CicloDetalheRepositorio.CATEGORIAS_CUSTO)
        self.sp_valor = QDoubleSpinBox()
        self.sp_valor.setRange(0, 999999999)
        self.sp_valor.setDecimals(2)
        self.cb_etapa = QComboBox()
        self.cb_etapa.addItem("", None)
        for e in (etapas or []):
            self.cb_etapa.addItem(e["nome"], e["id"])
        self.ed_data = _data_editada()

        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Categoria:", self.cb_categoria)
        form.addRow("Valor (R$):", self.sp_valor)
        form.addRow("Etapa (opcional):", self.cb_etapa)
        form.addRow("Data:", self.ed_data)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

    def _validar(self):
        if not self.ed_descricao.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe a descrição do custo.")
            return
        if self.sp_valor.value() <= 0:
            QMessageBox.warning(self, "Validação",
                                "Informe um valor maior que zero.")
            return
        self.accept()

    def dados(self):
        return {
            "descricao": self.ed_descricao.text().strip(),
            "categoria": self.cb_categoria.currentText(),
            "valor": self.sp_valor.value(),
            "etapa_id": self.cb_etapa.currentData(),
            "data": _valor_data(self.ed_data),
        }


class CicloDetalheDialog(QDialog):
    def __init__(self, parent=None, ciclo_id=None):
        super().__init__(parent)
        self.ciclo_id = ciclo_id
        self.ciclo = CicloRepositorio.obter(ciclo_id)
        nome = self.ciclo["nome"] if self.ciclo else "Ciclo"
        self.setWindowTitle(f"Ciclo: {nome}")
        self.resize(900, 560)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._aba_etapas(), "Etapas")
        self.tabs.addTab(self._aba_rotinas(), "Rotinas")
        self.tabs.addTab(self._aba_horas(), "Horas")
        self.tabs.addTab(self._aba_custos(), "Custos")
        self.tabs.addTab(self._aba_resumo(), "Resumo")

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(btn_fechar, alignment=Qt.AlignRight)

        self.tabs.currentChanged.connect(self._on_aba)
        self.carregar_etapas()
        self.carregar_rotinas()
        self.carregar_horas()
        self.carregar_custos()
        self.carregar_resumo()

    # ---------- Aba Etapas ----------
    def _aba_etapas(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_etapas = QTableWidget(0, 8)
        self.tabela_etapas.setHorizontalHeaderLabels(
            ["ID", "Nome", "Status", "%", "Responsável", "Orç. Etapa", "Horas", "Custo Horas"])
        self.tabela_etapas.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela_etapas.setColumnWidth(0, 40)
        self.tabela_etapas.setColumnWidth(2, 100)
        self.tabela_etapas.setColumnWidth(3, 60)
        self.tabela_etapas.setColumnWidth(6, 70)
        self.tabela_etapas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_etapas.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_etapas.cellDoubleClicked.connect(self._editar_etapa_linha)
        layout.addWidget(self.tabela_etapas)
        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova Etapa")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.nova_etapa)
        btn_editar.clicked.connect(self.editar_etapa)
        btn_excluir.clicked.connect(self.excluir_etapa)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)
        return w

    def _etapa_selecionada(self):
        linha = self.tabela_etapas.currentRow()
        if linha < 0:
            return None
        return self.tabela_etapas.item(linha, 0).data(Qt.UserRole)

    def _editar_etapa_linha(self, linha, coluna):
        self.tabela_etapas.setCurrentCell(linha, 0)
        self.editar_etapa()

    def carregar_etapas(self):
        etapas = CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
        self.tabela_etapas.setRowCount(len(etapas))
        for i, e in enumerate(etapas):
            id_item = QTableWidgetItem(str(e["id"]))
            id_item.setData(Qt.UserRole, e["id"])
            self.tabela_etapas.setItem(i, 0, id_item)
            self.tabela_etapas.setItem(i, 1, QTableWidgetItem(e["nome"]))
            self.tabela_etapas.setItem(
                i, 2, QTableWidgetItem(e.get("status") or ""))
            self.tabela_etapas.setItem(
                i, 3, QTableWidgetItem(str(e.get("percentual") or 0)))
            self.tabela_etapas.setItem(
                i, 4, QTableWidgetItem(e.get("responsavel") or ""))
            self.tabela_etapas.setItem(i, 5, QTableWidgetItem(
                fmt_moeda(e.get("custo_orcado"))))
            self.tabela_etapas.setItem(
                i, 6, QTableWidgetItem(str(e.get("horas_reais") or 0)))
            self.tabela_etapas.setItem(
                i, 7, QTableWidgetItem(fmt_moeda(e.get("custo_horas"))))

    def nova_etapa(self):
        dlg = EtapaDialog(self)
        if dlg.exec():
            CicloDetalheRepositorio.inserir_etapa(self.ciclo_id, dlg.dados())
            self.carregar_etapas()
            self.carregar_resumo()

    def editar_etapa(self):
        etapa_id = self._etapa_selecionada()
        if not etapa_id:
            QMessageBox.information(self, "Aviso", "Selecione uma etapa.")
            return
        etapa = next((e for e in CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
                      if e["id"] == etapa_id), None)
        dlg = EtapaDialog(self, etapa)
        if dlg.exec():
            CicloDetalheRepositorio.atualizar_etapa(etapa_id, dlg.dados())
            self.carregar_etapas()
            self.carregar_resumo()

    def excluir_etapa(self):
        etapa_id = self._etapa_selecionada()
        if not etapa_id:
            QMessageBox.information(self, "Aviso", "Selecione uma etapa.")
            return
        if QMessageBox.question(self, "Confirmar",
                                "Excluir esta etapa?\nRotinas, lançamentos e custos dela serão mantidos (sem etapa).") == QMessageBox.Yes:
            CicloDetalheRepositorio.excluir_etapa(etapa_id)
            self.carregar_etapas()
            self.carregar_rotinas()
            self.carregar_resumo()

    # ---------- Aba Rotinas ----------
    def _aba_rotinas(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_rotinas = QTableWidget(0, 7)
        self.tabela_rotinas.setHorizontalHeaderLabels(
            ["ID", "Código", "Nome", "Etapa", "Status", "Hrs Est.", "Caso Gerado"])
        self.tabela_rotinas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela_rotinas.setColumnWidth(0, 40)
        self.tabela_rotinas.setColumnWidth(1, 90)
        self.tabela_rotinas.setColumnWidth(4, 100)
        self.tabela_rotinas.setColumnWidth(6, 120)
        self.tabela_rotinas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_rotinas.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_rotinas)
        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova Rotina")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_gerar = QPushButton("Gerar Caso de Teste")
        btn_novo.clicked.connect(self.nova_rotina)
        btn_editar.clicked.connect(self.editar_rotina)
        btn_excluir.clicked.connect(self.excluir_rotina)
        btn_gerar.clicked.connect(self.gerar_caso_rotina)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_gerar)
        botoes.addStretch()
        layout.addLayout(botoes)
        return w

    def _rotina_selecionada(self):
        linha = self.tabela_rotinas.currentRow()
        if linha < 0:
            return None
        return self.tabela_rotinas.item(linha, 0).data(Qt.UserRole)

    def carregar_rotinas(self):
        rotinas = CicloDetalheRepositorio.listar_rotinas(self.ciclo_id)
        self.tabela_rotinas.setRowCount(len(rotinas))
        for i, r in enumerate(rotinas):
            id_item = QTableWidgetItem(str(r["id"]))
            id_item.setData(Qt.UserRole, r["id"])
            self.tabela_rotinas.setItem(i, 0, id_item)
            self.tabela_rotinas.setItem(i, 1, QTableWidgetItem(r["codigo"]))
            self.tabela_rotinas.setItem(i, 2, QTableWidgetItem(r["nome"]))
            self.tabela_rotinas.setItem(
                i, 3, QTableWidgetItem(r.get("etapa_nome") or ""))
            self.tabela_rotinas.setItem(
                i, 4, QTableWidgetItem(r.get("status") or ""))
            self.tabela_rotinas.setItem(i, 5, QTableWidgetItem(
                str(r.get("horas_estimadas") or 0)))
            self.tabela_rotinas.setItem(
                i, 6, QTableWidgetItem(r.get("caso_codigo") or ""))

    def nova_rotina(self):
        etapas = CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
        dlg = RotinaDialog(self, None, etapas)
        if dlg.exec():
            CicloDetalheRepositorio.inserir_rotina(self.ciclo_id, dlg.dados())
            self.carregar_rotinas()
            self.carregar_resumo()

    def editar_rotina(self):
        rotina_id = self._rotina_selecionada()
        if not rotina_id:
            QMessageBox.information(self, "Aviso", "Selecione uma rotina.")
            return
        rotina = next((r for r in CicloDetalheRepositorio.listar_rotinas(self.ciclo_id)
                       if r["id"] == rotina_id), None)
        etapas = CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
        dlg = RotinaDialog(self, rotina, etapas)
        if dlg.exec():
            CicloDetalheRepositorio.atualizar_rotina(rotina_id, dlg.dados())
            self.carregar_rotinas()
            self.carregar_resumo()

    def excluir_rotina(self):
        rotina_id = self._rotina_selecionada()
        if not rotina_id:
            QMessageBox.information(self, "Aviso", "Selecione uma rotina.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir esta rotina?") == QMessageBox.Yes:
            CicloDetalheRepositorio.excluir_rotina(rotina_id)
            self.carregar_rotinas()
            self.carregar_resumo()

    def gerar_caso_rotina(self):
        rotina_id = self._rotina_selecionada()
        if not rotina_id:
            QMessageBox.information(self, "Aviso", "Selecione uma rotina.")
            return
        ok, msg, caso_id = CicloDetalheRepositorio.gerar_caso_teste(rotina_id)
        if ok:
            QMessageBox.information(self, "Sucesso", f"✓ {msg}")
        else:
            QMessageBox.warning(self, "Atenção", msg)
        self.carregar_rotinas()

    # ---------- Aba Horas ----------
    def _aba_horas(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_horas = QTableWidget(0, 8)
        self.tabela_horas.setHorizontalHeaderLabels(
            ["ID", "Data", "Quem", "Etapa", "Rotina", "Horas", "Custo/h", "Total"])
        self.tabela_horas.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela_horas.setColumnWidth(0, 40)
        self.tabela_horas.setColumnWidth(1, 90)
        self.tabela_horas.setColumnWidth(5, 60)
        self.tabela_horas.setColumnWidth(6, 80)
        self.tabela_horas.setColumnWidth(7, 90)
        self.tabela_horas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_horas.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_horas)
        botoes = QHBoxLayout()
        btn_lancar = QPushButton("Lançar Horas")
        btn_excluir = QPushButton("Excluir Lançamento")
        btn_lancar.clicked.connect(self.lancar_hora)
        btn_excluir.clicked.connect(self.excluir_hora)
        botoes.addWidget(btn_lancar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)
        return w

    def carregar_horas(self):
        horas = CicloDetalheRepositorio.listar_horas(self.ciclo_id)
        self.tabela_horas.setRowCount(len(horas))
        for i, h in enumerate(horas):
            id_item = QTableWidgetItem(str(h["id"]))
            id_item.setData(Qt.UserRole, h["id"])
            self.tabela_horas.setItem(i, 0, id_item)
            self.tabela_horas.setItem(
                i, 1, QTableWidgetItem(h.get("data") or ""))
            self.tabela_horas.setItem(
                i, 2, QTableWidgetItem(h.get("lancado_por") or ""))
            self.tabela_horas.setItem(
                i, 3, QTableWidgetItem(h.get("etapa_nome") or ""))
            self.tabela_horas.setItem(
                i, 4, QTableWidgetItem(h.get("rotina_nome") or ""))
            self.tabela_horas.setItem(
                i, 5, QTableWidgetItem(str(h.get("horas") or 0)))
            self.tabela_horas.setItem(
                i, 6, QTableWidgetItem(fmt_moeda(h.get("custo_hora"))))
            self.tabela_horas.setItem(i, 7, QTableWidgetItem(
                fmt_moeda((h.get("horas") or 0) * (h.get("custo_hora") or 0))))

    def lancar_hora(self):
        etapas = CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
        rotinas = CicloDetalheRepositorio.listar_rotinas(self.ciclo_id)
        dlg = HoraDialog(self, etapas, rotinas)
        if dlg.exec():
            CicloDetalheRepositorio.inserir_hora(self.ciclo_id, dlg.dados())
            self.carregar_horas()
            self.carregar_etapas()
            self.carregar_resumo()

    def excluir_hora(self):
        linha = self.tabela_horas.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Aviso", "Selecione um lançamento.")
            return
        hora_id = self.tabela_horas.item(linha, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Confirmar", "Excluir este lançamento?") == QMessageBox.Yes:
            CicloDetalheRepositorio.excluir_hora(hora_id)
            self.carregar_horas()
            self.carregar_etapas()
            self.carregar_resumo()

    # ---------- Aba Custos ----------
    def _aba_custos(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_custos = QTableWidget(0, 6)
        self.tabela_custos.setHorizontalHeaderLabels(
            ["ID", "Data", "Descrição", "Categoria", "Etapa", "Valor"])
        self.tabela_custos.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela_custos.setColumnWidth(0, 40)
        self.tabela_custos.setColumnWidth(1, 90)
        self.tabela_custos.setColumnWidth(3, 100)
        self.tabela_custos.setColumnWidth(5, 110)
        self.tabela_custos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_custos.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_custos)
        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Custo")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo_custo)
        btn_excluir.clicked.connect(self.excluir_custo)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)
        return w

    def carregar_custos(self):
        custos = CicloDetalheRepositorio.listar_custos(self.ciclo_id)
        self.tabela_custos.setRowCount(len(custos))
        for i, c in enumerate(custos):
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.UserRole, c["id"])
            self.tabela_custos.setItem(i, 0, id_item)
            self.tabela_custos.setItem(
                i, 1, QTableWidgetItem(c.get("data") or ""))
            self.tabela_custos.setItem(i, 2, QTableWidgetItem(c["descricao"]))
            self.tabela_custos.setItem(
                i, 3, QTableWidgetItem(c.get("categoria") or ""))
            self.tabela_custos.setItem(
                i, 4, QTableWidgetItem(c.get("etapa_nome") or ""))
            self.tabela_custos.setItem(
                i, 5, QTableWidgetItem(fmt_moeda(c.get("valor"))))

    def novo_custo(self):
        etapas = CicloDetalheRepositorio.listar_etapas(self.ciclo_id)
        dlg = CustoDialog(self, etapas)
        if dlg.exec():
            CicloDetalheRepositorio.inserir_custo(self.ciclo_id, dlg.dados())
            self.carregar_custos()
            self.carregar_resumo()

    def excluir_custo(self):
        linha = self.tabela_custos.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Aviso", "Selecione um custo.")
            return
        custo_id = self.tabela_custos.item(linha, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Confirmar", "Excluir este custo?") == QMessageBox.Yes:
            CicloDetalheRepositorio.excluir_custo(custo_id)
            self.carregar_custos()
            self.carregar_resumo()

    # ---------- Aba Resumo ----------
    def _aba_resumo(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.progresso = QProgressBar()
        self.progresso.setRange(0, 100)
        self.progresso.setValue(0)
        self.progresso.setFormat("%p%")
        layout.addWidget(QLabel("Andamento do Ciclo (média das etapas):"))
        layout.addWidget(self.progresso)

        self.lbl_exec = QLabel("")
        layout.addWidget(self.lbl_exec)

        self.grid = QGridLayout()
        layout.addLayout(self.grid)
        layout.addStretch()
        return w

    def carregar_resumo(self):
        k = CicloDetalheRepositorio.kpis_gestao(self.ciclo_id)
        ek = CicloRepositorio.kpis(self.ciclo_id)
        self.progresso.setValue(int(k["andamento"]))
        self.lbl_exec.setText(
            f"Execução: {ek['total']} casos | {ek['perc_execucao']}% executados | "
            f"{ek['perc_aprovacao']}% aprovados | {ek['defeitos']} defeitos | "
            f"progresso médio {ek['perc_medio']}%")

        linhas = [
            ("Etapas concluídas:",
             f"{k['etapas_concluidas']} / {k['etapas_total']}"),
            ("Rotinas concluídas:",
             f"{k['rotinas_concluidas']} / {k['rotinas_total']}"),
            ("Horas estimadas:", f"{k['horas_estimadas']:.2f} h"),
            ("Horas lançadas:", f"{k['horas_reais']:.2f} h"),
            ("Custo orçado:", fmt_moeda(k["custo_orcado"])),
            ("Custo horas:", fmt_moeda(k["custo_horas"])),
            ("Custos adicionais:", fmt_moeda(k["custo_adicionais"])),
            ("Custo real total:", fmt_moeda(k["custo_real"])),
            ("Variação (orçado - real):", fmt_moeda(k["variacao"])),
            ("% do orçamento usado:", f"{k['perc_orcado_usado']:.1f}%"),
        ]
        while self.grid.count():
            item = self.grid.takeAt(0)
            wdg = item.widget()
            if wdg:
                wdg.deleteLater()
        for i, (rotulo, valor) in enumerate(linhas):
            self.grid.addWidget(QLabel(f"<b>{rotulo}</b>"), i, 0)
            self.grid.addWidget(QLabel(valor), i, 1)

    def _on_aba(self, index):
        if index == 4:
            self.carregar_resumo()
