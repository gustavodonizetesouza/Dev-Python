"""Cadastro de clientes (cada cliente tem seu próprio banco de dados)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QLineEdit, QTextEdit,
    QFormLayout, QDialogButtonBox, QCheckBox,
)
from PySide6.QtCore import Qt
from database.models import ClienteRepositorio


class ClienteDialog(QDialog):
    def __init__(self, parent=None, cliente=None):
        super().__init__(parent)
        self.cliente = cliente
        self.setWindowTitle(
            "Novo Cliente" if not cliente else "Editar Cliente")
        self.setMinimumWidth(440)

        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.cb_ativo = QCheckBox("Ativo")
        self.cb_ativo.setChecked(True)
        self.ed_obs = QTextEdit()
        self.ed_obs.setFixedHeight(70)

        form.addRow("Nome:", self.ed_nome)
        form.addRow("", self.cb_ativo)
        form.addRow("Observações:", self.ed_obs)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if cliente:
            self.ed_nome.setText(cliente["nome"])
            self.cb_ativo.setChecked(bool(cliente.get("ativo", 1)))
            self.ed_obs.setPlainText(cliente.get("observacoes") or "")

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o nome do cliente.")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "ativo": 1 if self.cb_ativo.isChecked() else 0,
            "observacoes": self.ed_obs.toPlainText().strip(),
        }


class ClientesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clientes")
        self.resize(560, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cada cliente tem seu próprio banco de dados. Cadastre aqui e depois "
                                "vincule as CONEXÕES a ele em Cadastros > Conexões a Bancos."))

        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Nome", "Ativo", "Observações"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(2, 55)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

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

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)

        self.carregar()

    def carregar(self):
        clientes = ClienteRepositorio.listar(apenas_ativos=False)
        self.tabela.setRowCount(len(clientes))
        for i, c in enumerate(clientes):
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.UserRole, c["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(c["nome"]))
            self.tabela.setItem(i, 2, QTableWidgetItem(
                "Sim" if c.get("ativo", 1) else "Não"))
            self.tabela.setItem(i, 3, QTableWidgetItem(
                c.get("observacoes") or ""))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_edicao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        dlg = ClienteDialog(self)
        if dlg.exec():
            ClienteRepositorio.inserir(dlg.dados())
            self.carregar()

    def editar(self):
        cliente_id = self._selecionado()
        if not cliente_id:
            QMessageBox.information(self, "Aviso", "Selecione um cliente.")
            return
        cliente = ClienteRepositorio.obter(cliente_id)
        dlg = ClienteDialog(self, cliente)
        if dlg.exec():
            ClienteRepositorio.atualizar(cliente_id, dlg.dados())
            self.carregar()

    def excluir(self):
        cliente_id = self._selecionado()
        if not cliente_id:
            QMessageBox.information(self, "Aviso", "Selecione um cliente.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir este cliente?") == QMessageBox.Yes:
            if ClienteRepositorio.excluir(cliente_id):
                self.carregar()
            else:
                QMessageBox.warning(
                    self, "Não é possível",
                    "Este cliente ainda possui conexões vinculadas.\n"
                    "Exclua as conexões dele antes (Cadastros > Conexões a Bancos).")
