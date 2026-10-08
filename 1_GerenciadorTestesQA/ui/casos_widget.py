"""Widget de cadastro de casos de teste (catálogo mestre)."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QFormLayout, QTextEdit,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView,
)
from PySide6.QtCore import Qt
from database.models import CasoRepositorio, ModuloRepositorio, UsuarioRepositorio
from utils.helpers import TIPOS_OPCOES, PRIORIDADES_OPCOES


class CasoDialog(QDialog):
    def __init__(self, parent=None, caso=None):
        super().__init__(parent)
        self.caso = caso
        self.setWindowTitle(
            "Novo Caso de Teste" if not caso else "Editar Caso de Teste")
        self.setMinimumWidth(520)

        form = QFormLayout()
        self.ed_codigo = QLineEdit()
        self.ed_codigo.setPlaceholderText("Ex.: ER1-System access")

        self.ed_tarefa = QLineEdit()
        self.ed_tarefa.setPlaceholderText("Nome curto da tarefa")

        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(70)
        self.ed_descricao.setPlaceholderText("Detalhamento do cenário testado")

        self.cb_modulo = QComboBox()
        self._carregar_modulos(self.cb_modulo)

        self.ed_rotina = QLineEdit()
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(TIPOS_OPCOES)
        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(PRIORIDADES_OPCOES)

        # Responsável agora é um combo vinculado aos usuários cadastrados
        self.cb_responsavel = QComboBox()
        self._carregar_usuarios(self.cb_responsavel)

        self.ed_compliance = QLineEdit()

        form.addRow("Código:", self.ed_codigo)
        form.addRow("Tarefa:", self.ed_tarefa)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Módulo:", self.cb_modulo)
        form.addRow("Rotina:", self.ed_rotina)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Responsável:", self.cb_responsavel)
        form.addRow("Req. Compliance:", self.ed_compliance)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if caso:
            self._preencher(caso)

    @staticmethod
    def _carregar_modulos(combo):
        combo.clear()
        modulos = ModuloRepositorio.listar()
        combo.addItems([m["nome"] for m in modulos] or ["SIGACFG"])

    @staticmethod
    def _carregar_usuarios(combo):
        combo.clear()
        combo.addItem("")  # opção em branco
        usuarios = UsuarioRepositorio.listar()
        combo.addItems([u["nome"] for u in usuarios])

    def _preencher(self, caso):
        self.ed_codigo.setText(caso["codigo"])
        self.ed_tarefa.setText(caso.get("tarefa") or "")
        self.ed_descricao.setText(caso["descricao"])
        idx = self.cb_modulo.findText(caso["modulo"])
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        self.ed_rotina.setText(caso.get("rotina") or "")
        idx = self.cb_tipo.findText(caso.get("tipo") or "Funcional")
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)
        idx = self.cb_prioridade.findText(caso.get("prioridade") or "Média")
        if idx >= 0:
            self.cb_prioridade.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(caso.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_compliance.setText(caso.get("requisito_compliance") or "")

    def _validar(self):
        if not self.ed_codigo.text().strip() or not self.ed_descricao.toPlainText().strip():
            QMessageBox.warning(self, "Validação",
                                "Código e Descrição são obrigatórios.")
            return
        self.accept()

    def dados(self):
        return {
            "codigo": self.ed_codigo.text().strip(),
            "tarefa": self.ed_tarefa.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "modulo": self.cb_modulo.currentText(),
            "rotina": self.ed_rotina.text().strip(),
            "tipo": self.cb_tipo.currentText(),
            "prioridade": self.cb_prioridade.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "requisito_compliance": self.ed_compliance.text().strip(),
        }


class CasoViewDialog(QDialog):
    """Diálogo de SOMENTE VISUALIZAÇÃO (aberto por duplo clique)."""

    def __init__(self, caso, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Visualizar Caso — {caso['codigo']}")
        self.setMinimumWidth(520)

        form = QFormLayout()
        campos = [
            ("ID", str(caso["id"])),
            ("Código", caso["codigo"]),
            ("Tarefa", caso.get("tarefa") or ""),
            ("Descrição", caso["descricao"]),
            ("Módulo", caso["modulo"]),
            ("Rotina", caso.get("rotina") or ""),
            ("Tipo", caso["tipo"]),
            ("Prioridade", caso["prioridade"]),
            ("Responsável", caso.get("responsavel") or ""),
            ("Req. Compliance", caso.get("requisito_compliance") or ""),
        ]
        for rotulo, valor in campos:
            campo = QLineEdit(valor)
            campo.setReadOnly(True)
            if rotulo == "Descrição":
                campo.setFixedHeight(70)
            form.addRow(f"{rotulo}:", campo)

        botoes = QDialogButtonBox(QDialogButtonBox.Close)
        botoes.rejected.connect(self.reject)
        botoes.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)


class CasosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Barra de filtros
        barra = QHBoxLayout()
        barra.addWidget(QLabel("Filtrar Módulo:"))
        self.cb_filtro_modulo = QComboBox()
        self.cb_filtro_modulo.currentIndexChanged.connect(self.carregar)
        barra.addWidget(self.cb_filtro_modulo)
        barra.addWidget(QLabel("Tipo:"))
        self.cb_filtro_tipo = QComboBox()
        self.cb_filtro_tipo.addItem("Todos")
        self.cb_filtro_tipo.addItems(TIPOS_OPCOES)
        self.cb_filtro_tipo.currentIndexChanged.connect(self.carregar)
        barra.addWidget(self.cb_filtro_tipo)
        barra.addStretch()
        layout.addLayout(barra)

        # Tabela
        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Módulo", "Tarefa", "Tipo", "Prioridade", "Responsável", "Compliance"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 140)
        self.tabela.setColumnWidth(2, 90)
        self.tabela.setColumnWidth(4, 110)
        self.tabela.setColumnWidth(5, 90)
        self.tabela.setColumnWidth(6, 130)
        self.tabela.setColumnWidth(7, 110)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        # Duplo clique abre a visualização (somente leitura)
        self.tabela.cellDoubleClicked.connect(self._visualizar)
        layout.addWidget(self.tabela)

        # Botões
        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar(self):
        mod = None if self.cb_filtro_modulo.currentText(
        ) == "Todos" else self.cb_filtro_modulo.currentText()
        tipo = None if self.cb_filtro_tipo.currentText(
        ) == "Todos" else self.cb_filtro_tipo.currentText()
        casos = CasoRepositorio.listar(mod, tipo)

        # Filtro de módulo: mostra APENAS módulos que têm testes cadastrados
        self.cb_filtro_modulo.blockSignals(True)
        atual = self.cb_filtro_modulo.currentText()
        self.cb_filtro_modulo.clear()
        self.cb_filtro_modulo.addItem("Todos")
        self.cb_filtro_modulo.addItems(CasoRepositorio.modulos_com_testes())
        idx = self.cb_filtro_modulo.findText(atual)
        self.cb_filtro_modulo.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_filtro_modulo.blockSignals(False)

        self.tabela.setRowCount(len(casos))
        for i, c in enumerate(casos):
            valores = [str(c["id"]), c["codigo"], c["modulo"],
                       c.get("tarefa") or "", c["tipo"],
                       c["prioridade"], c.get("responsavel") or "",
                       c.get("requisito_compliance") or ""]
            for j, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setData(Qt.UserRole, c["id"])
                self.tabela.setItem(i, j, item)

    def _caso_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _visualizar(self, linha, coluna):
        """Duplo clique: abre o caso em modo somente visualização."""
        caso_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        caso = CasoRepositorio.obter(caso_id)
        if caso:
            dlg = CasoViewDialog(caso, self)
            dlg.exec()

    def novo(self):
        dlg = CasoDialog(self)
        if dlg.exec():
            CasoRepositorio.inserir(dlg.dados())
            self.carregar()

    def editar(self):
        caso_id = self._caso_selecionado()
        if not caso_id:
            QMessageBox.information(
                self, "Aviso", "Selecione um caso de teste.")
            return
        caso = CasoRepositorio.obter(caso_id)
        dlg = CasoDialog(self, caso)
        if dlg.exec():
            CasoRepositorio.atualizar(caso_id, dlg.dados())
            self.carregar()

    def excluir(self):
        caso_id = self._caso_selecionado()
        if not caso_id:
            QMessageBox.information(
                self, "Aviso", "Selecione um caso de teste.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir este caso de teste?") == QMessageBox.Yes:
            CasoRepositorio.excluir(caso_id)
            self.carregar()
