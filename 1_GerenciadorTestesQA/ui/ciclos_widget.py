"""Widget de gestão de Ciclos — a unidade completa de trabalho do app."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QSpinBox,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt, Signal
from database.models import CicloRepositorio, UsuarioRepositorio
from database.connection import Database
from .tipos_ciclo_dialog import TiposCicloDialog
from .ciclo_detalhe_dialog import CicloDetalheDialog
from .usuarios_dialog import UsuariosDialog


def fmt_moeda(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        v = 0
    return f"R$ {v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


class CicloDialog(QDialog):
    def __init__(self, parent=None, ciclo=None):
        super().__init__(parent)
        self.ciclo = ciclo
        self.setWindowTitle("Novo Ciclo" if not ciclo else "Editar Ciclo")
        self.setMinimumWidth(520)

        form = QFormLayout()
        self.ed_nome = QLineEdit()

        linha_tipo = QHBoxLayout()
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(CicloRepositorio.listar_tipos())
        btn_tipos = QPushButton("+")
        btn_tipos.setToolTip("Gerenciar tipos de ciclo")
        btn_tipos.setMaximumWidth(32)
        btn_tipos.clicked.connect(self._gerenciar_tipos)
        linha_tipo.addWidget(self.cb_tipo, 1)
        linha_tipo.addWidget(btn_tipos)

        self.ed_versao = QLineEdit()
        self.sp_ano = QSpinBox()
        self.sp_ano.setRange(2000, 2100)
        self.sp_ano.setValue(2026)
        self.cb_status = QComboBox()
        self.cb_status.addItems(CicloRepositorio.STATUS_OPCOES)

        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        linha_resp = QHBoxLayout()
        linha_resp.addWidget(self.cb_responsavel, 1)
        btn_resp = QPushButton("+")
        btn_resp.setToolTip("Cadastrar usuário")
        btn_resp.setMaximumWidth(32)
        btn_resp.clicked.connect(self._gerenciar_usuarios)
        linha_resp.addWidget(btn_resp)

        self.ed_inicio = QLineEdit()
        self.ed_inicio.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.ed_fim = QLineEdit()
        self.ed_fim.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.sp_orcado = QDoubleSpinBox()
        self.sp_orcado.setRange(0, 999999999)
        self.sp_orcado.setDecimals(2)
        self.sp_orcado.setPrefix("R$ ")

        form.addRow("Nome:", self.ed_nome)
        form.addRow("Tipo:", linha_tipo)
        form.addRow("Versão:", self.ed_versao)
        form.addRow("Ano:", self.sp_ano)
        form.addRow("Status:", self.cb_status)
        form.addRow("Responsável:", linha_resp)
        form.addRow("Início:", self.ed_inicio)
        form.addRow("Fim:", self.ed_fim)
        form.addRow("Orçamento total:", self.sp_orcado)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if ciclo:
            self._preencher(ciclo)

    def _gerenciar_tipos(self):
        dlg = TiposCicloDialog(self)
        dlg.exec()
        atual = self.cb_tipo.currentText()
        self.cb_tipo.clear()
        self.cb_tipo.addItems(CicloRepositorio.listar_tipos())
        idx = self.cb_tipo.findText(atual)
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)

    def _gerenciar_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        atual = self.cb_responsavel.currentText()
        self.cb_responsavel.clear()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        idx = self.cb_responsavel.findText(atual)
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)

    def _preencher(self, ciclo):
        self.ed_nome.setText(ciclo["nome"])
        idx = self.cb_tipo.findText(ciclo.get("tipo") or "")
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)
        self.ed_versao.setText(ciclo.get("versao") or "")
        if ciclo.get("ano"):
            self.sp_ano.setValue(int(ciclo["ano"]))
        idx = self.cb_status.findText(ciclo.get("status") or "Planejado")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(ciclo.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_inicio.setText(ciclo.get("data_inicio") or "")
        self.ed_fim.setText(ciclo.get("data_fim") or "")
        self.sp_orcado.setValue(float(ciclo.get("custo_orcado") or 0))

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome do ciclo.")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "tipo": self.cb_tipo.currentText(),
            "versao": self.ed_versao.text().strip(),
            "ano": self.sp_ano.value(),
            "status": self.cb_status.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "data_inicio": self.ed_inicio.text().strip(),
            "data_fim": self.ed_fim.text().strip(),
            "custo_orcado": self.sp_orcado.value(),
        }


class CiclosWidget(QWidget):
    """Aba 1 — lista de ciclos; o ciclo selecionado alimenta a aba Casos."""

    cicloMudou = Signal(object)

    def __init__(self):
        super().__init__()
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Aviso quando não há cliente ativo (dados em memória = temporários)
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setStyleSheet("color: #b06a00; font-weight: bold;")
        self.lbl_aviso.setWordWrap(True)
        layout.addWidget(self.lbl_aviso)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Status:"))
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItem("Todos")
        self.cb_filtro.addItems(CicloRepositorio.STATUS_OPCOES)
        self.cb_filtro.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 10)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Nome", "Tipo", "Versão", "Status", "Responsável", "Início", "Fim", "Orçado", "Casos"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(2, 130)
        self.tabela.setColumnWidth(3, 70)
        self.tabela.setColumnWidth(4, 100)
        self.tabela.setColumnWidth(5, 110)
        self.tabela.setColumnWidth(9, 60)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        self.tabela.currentCellChanged.connect(self._emitir_selecao)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Ciclo")
        btn_editar = QPushButton("Editar")
        btn_copiar = QPushButton("Copiar Ciclo")
        btn_excluir = QPushButton("Excluir")
        btn_detalhes = QPushButton("Detalhes do Ciclo")
        btn_tipos = QPushButton("Tipos de Ciclo...")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_copiar.clicked.connect(self.copiar)
        btn_excluir.clicked.connect(self.excluir)
        btn_detalhes.clicked.connect(self.detalhes)
        btn_tipos.clicked.connect(self.gerenciar_tipos)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_copiar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_detalhes)
        botoes.addWidget(btn_tipos)
        botoes.addStretch()
        layout.addLayout(botoes)

    def _atualizar_aviso(self):
        try:
            cliente = Database._get_cliente_ativo()
            cfg = None
            if cliente.get("id"):
                cfg = Database._get_conexao_padrao_cliente(cliente["id"])
            if cliente.get("id") is None or cfg is None:
                self.lbl_aviso.setText(
                    "⚠ Nenhum cliente ativo: os dados ficam em MEMÓRIA (temporários). "
                    "Cadastre um cliente + conexão e selecione o cliente no rodapé "
                    "para salvar em arquivo de verdade.")
            else:
                self.lbl_aviso.setText("")
        except Exception:
            self.lbl_aviso.setText("")

    def ciclo_atual(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _emitir_selecao(self, *args):
        self.cicloMudou.emit(self.ciclo_atual())

    def carregar(self):
        """Recarrega a lista de ciclos. Qualquer erro aparece numa caixa (nunca silencioso)."""
        self._atualizar_aviso()
        try:
            filtro = self.cb_filtro.currentText()
            if filtro == "Todos":
                filtro = None
            ciclos = CicloRepositorio.listar(filtro)

            self.tabela.setRowCount(len(ciclos))
            for i, c in enumerate(ciclos):
                id_item = QTableWidgetItem(str(c["id"]))
                id_item.setData(Qt.UserRole, c["id"])
                self.tabela.setItem(i, 0, id_item)
                self.tabela.setItem(i, 1, QTableWidgetItem(c["nome"]))
                self.tabela.setItem(
                    i, 2, QTableWidgetItem(c.get("tipo") or ""))
                self.tabela.setItem(
                    i, 3, QTableWidgetItem(c.get("versao") or ""))
                self.tabela.setItem(
                    i, 4, QTableWidgetItem(c.get("status") or ""))
                self.tabela.setItem(i, 5, QTableWidgetItem(
                    c.get("responsavel") or ""))
                self.tabela.setItem(i, 6, QTableWidgetItem(
                    c.get("data_inicio") or ""))
                self.tabela.setItem(
                    i, 7, QTableWidgetItem(c.get("data_fim") or ""))
                self.tabela.setItem(i, 8, QTableWidgetItem(
                    fmt_moeda(c.get("custo_orcado"))))
                self.tabela.setItem(i, 9, QTableWidgetItem(
                    str(CicloRepositorio.contar_casos(c["id"]))))
            if ciclos and self.ciclo_atual() is None:
                self.tabela.setCurrentCell(0, 0)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao carregar ciclos",
                                 f"Não foi possível carregar os ciclos:\n{e}")
            return
        self.cicloMudou.emit(self.ciclo_atual())

    def _selecionado(self):
        return self.ciclo_atual()

    def _abrir_edicao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        dlg = CicloDialog(self)
        if dlg.exec():
            try:
                novo_id = CicloRepositorio.inserir(dlg.dados())
                self.carregar()
                QMessageBox.information(self, "Sucesso",
                                        f"Ciclo salvo com sucesso (ID {novo_id}).")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao salvar ciclo",
                                     f"Não foi possível salvar o ciclo:\n{e}")

    def editar(self):
        ciclo_id = self._selecionado()
        if not ciclo_id:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        ciclo = CicloRepositorio.obter(ciclo_id)
        dlg = CicloDialog(self, ciclo)
        if dlg.exec():
            try:
                CicloRepositorio.atualizar(ciclo_id, dlg.dados())
                self.carregar()
                QMessageBox.information(self, "Sucesso", "Ciclo atualizado.")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao atualizar ciclo",
                                     f"Não foi possível atualizar o ciclo:\n{e}")

    def copiar(self):
        ciclo_id = self._selecionado()
        if not ciclo_id:
            QMessageBox.information(
                self, "Aviso", "Selecione um ciclo para copiar.")
            return
        try:
            novo_id, msg = CicloRepositorio.copiar(ciclo_id)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao copiar ciclo",
                                 f"Não foi possível copiar o ciclo:\n{e}")
            return
        if novo_id:
            QMessageBox.information(self, "Sucesso", f"✓ {msg}")
            self.carregar()
            for linha in range(self.tabela.rowCount()):
                if self.tabela.item(linha, 0).data(Qt.UserRole) == novo_id:
                    self.tabela.setCurrentCell(linha, 0)
                    break
        else:
            QMessageBox.warning(self, "Atenção", msg)

    def excluir(self):
        ciclo_id = self._selecionado()
        if not ciclo_id:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        resp = QMessageBox.question(
            self, "Confirmar",
            "Excluir este ciclo?\nCasos, etapas, rotinas, horas e custos dele TAMBÉM serão excluídos.")
        if resp == QMessageBox.Yes:
            try:
                CicloRepositorio.excluir(ciclo_id)
                self.carregar()
            except Exception as e:
                QMessageBox.critical(self, "Erro ao excluir ciclo",
                                     f"Não foi possível excluir o ciclo:\n{e}")

    def detalhes(self):
        ciclo_id = self._selecionado()
        if not ciclo_id:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        try:
            dlg = CicloDetalheDialog(self, ciclo_id)
            dlg.exec()
            self.carregar()
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir detalhes",
                                 f"Não foi possível abrir os detalhes:\n{e}")

    def gerenciar_tipos(self):
        dlg = TiposCicloDialog(self)
        dlg.exec()
        self.carregar()
