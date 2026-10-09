"""Widget de controle de melhorias propostas durante os testes."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView,
)
from PySide6.QtCore import Qt
from database.models import MelhoriaRepositorio, ModuloRepositorio, UsuarioRepositorio
from utils.helpers import PRIORIDADES_OPCOES


class MelhoriaDialog(QDialog):
    def __init__(self, parent=None, melhoria=None):
        super().__init__(parent)
        self.melhoria = melhoria
        self.setWindowTitle(
            "Nova Melhoria" if not melhoria else "Editar Melhoria")
        self.setMinimumWidth(520)

        form = QFormLayout()
        self.ed_titulo = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(80)
        self.cb_modulo = QComboBox()
        self.cb_modulo.addItem("")
        self.cb_modulo.addItems([m["nome"]
                                for m in ModuloRepositorio.listar()])
        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(PRIORIDADES_OPCOES)
        self.cb_status = QComboBox()
        self.cb_status.addItems(MelhoriaRepositorio.STATUS_OPCOES)
        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        self.ed_obs = QTextEdit()
        self.ed_obs.setFixedHeight(60)

        form.addRow("Título:", self.ed_titulo)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Módulo:", self.cb_modulo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Status:", self.cb_status)
        form.addRow("Responsável:", self.cb_responsavel)
        form.addRow("Observações:", self.ed_obs)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if melhoria:
            self._preencher(melhoria)

    def _preencher(self, melhoria):
        self.ed_titulo.setText(melhoria["titulo"])
        self.ed_descricao.setPlainText(melhoria.get("descricao") or "")
        idx = self.cb_modulo.findText(melhoria.get("modulo") or "")
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        idx = self.cb_prioridade.findText(
            melhoria.get("prioridade") or "Media")
        if idx >= 0:
            self.cb_prioridade.setCurrentIndex(idx)
        idx = self.cb_status.findText(melhoria.get("status") or "Proposta")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(melhoria.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_obs.setPlainText(melhoria.get("observacoes") or "")

    def _validar(self):
        if not self.ed_titulo.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o título da melhoria.")
            return
        self.accept()

    def dados(self):
        return {
            "titulo": self.ed_titulo.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "modulo": self.cb_modulo.currentText(),
            "prioridade": self.cb_prioridade.currentText(),
            "status": self.cb_status.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "observacoes": self.ed_obs.toPlainText().strip(),
        }


class MelhoriasWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Status:"))
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItem("Todos")
        self.cb_filtro.addItems(MelhoriaRepositorio.STATUS_OPCOES)
        self.cb_filtro.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Título", "Módulo", "Prioridade", "Status", "Responsável", "Caso Gerado"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 80)
        self.tabela.setColumnWidth(3, 90)
        self.tabela.setColumnWidth(4, 80)
        self.tabela.setColumnWidth(5, 100)
        self.tabela.setColumnWidth(6, 110)
        self.tabela.setColumnWidth(7, 90)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        # Duplo clique abre a melhoria para visualizar/editar (como na aba Casos)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova Melhoria")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_gerar = QPushButton("Gerar Caso de Teste")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        btn_gerar.clicked.connect(self.gerar_caso)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_gerar)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar(self):
        filtro = self.cb_filtro.currentText()
        if filtro == "Todos":
            filtro = None
        melhorias = MelhoriaRepositorio.listar(filtro)

        self.tabela.setRowCount(len(melhorias))
        for i, m in enumerate(melhorias):
            id_item = QTableWidgetItem(str(m["id"]))
            id_item.setData(Qt.UserRole, m["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(m["codigo"]))
            self.tabela.setItem(i, 2, QTableWidgetItem(m["titulo"]))
            self.tabela.setItem(i, 3, QTableWidgetItem(m.get("modulo") or ""))
            self.tabela.setItem(i, 4, QTableWidgetItem(
                m.get("prioridade") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(m.get("status") or ""))
            self.tabela.setItem(i, 6, QTableWidgetItem(
                m.get("responsavel") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(
                m["codigo"] if m.get("caso_teste_id") else ""))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_edicao_linha(self, linha, coluna):
        """Duplo clique: abre a melhoria selecionada em modo de edição."""
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        dlg = MelhoriaDialog(self)
        if dlg.exec():
            MelhoriaRepositorio.inserir(dlg.dados())
            self.carregar()

    def editar(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        melhoria = MelhoriaRepositorio.obter(melhoria_id)
        dlg = MelhoriaDialog(self, melhoria)
        if dlg.exec():
            MelhoriaRepositorio.atualizar(melhoria_id, dlg.dados())
            self.carregar()

    def excluir(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir esta melhoria?") == QMessageBox.Yes:
            MelhoriaRepositorio.excluir(melhoria_id)
            self.carregar()

    def gerar_caso(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        ok, msg, caso_id = MelhoriaRepositorio.gerar_caso_teste(melhoria_id)
        if ok:
            QMessageBox.information(self, "Sucesso", f"✓ {msg}")
        else:
            QMessageBox.warning(self, "Atenção", msg)
        self.carregar()
