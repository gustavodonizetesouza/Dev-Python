"""Cadastro de conexões a bancos de dados (vinculadas a um cliente)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView, QFormLayout,
    QDialogButtonBox, QComboBox, QSpinBox,
)
from PySide6.QtCore import Qt
from database.models import ConexaoRepositorio, ClienteRepositorio
from database.connection import Database
from utils.seguranca import obter_senha


class ConexaoDialog(QDialog):
    def __init__(self, parent=None, conexao=None):
        super().__init__(parent)
        self.conexao = conexao
        self.setWindowTitle(
            "Nova Conexão" if not conexao else "Editar Conexão")
        self.setMinimumWidth(480)

        form = QFormLayout()
        self.cb_cliente = QComboBox()
        for c in ClienteRepositorio.listar(apenas_ativos=True):
            self.cb_cliente.addItem(c["nome"], c["id"])
        self.ed_nome = QLineEdit()
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(["sqlite", "sqlserver", "mysql"])
        self.ed_host = QLineEdit()
        self.sp_porta = QSpinBox()
        self.sp_porta.setRange(1, 65535)
        self.sp_porta.setValue(1433)
        self.ed_banco = QLineEdit()
        self.ed_usuario = QLineEdit()
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.Password)
        self.ed_driver = QLineEdit()
        self.ed_driver.setPlaceholderText("ODBC Driver 17 for SQL Server")

        form.addRow("Cliente:", self.cb_cliente)
        form.addRow("Nome:", self.ed_nome)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Host:", self.ed_host)
        form.addRow("Porta:", self.sp_porta)
        form.addRow("Banco/Arquivo:", self.ed_banco)
        form.addRow("Usuário:", self.ed_usuario)
        form.addRow("Senha:", self.ed_senha)
        form.addRow("Driver (SQL Server):", self.ed_driver)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if conexao:
            self._preencher(conexao)
        else:
            ativo = Database._get_cliente_ativo()
            if ativo and ativo.get("id"):
                idx = self.cb_cliente.findData(ativo["id"])
                if idx >= 0:
                    self.cb_cliente.setCurrentIndex(idx)

    def _preencher(self, conexao):
        if conexao.get("cliente_id"):
            idx = self.cb_cliente.findData(conexao["cliente_id"])
            if idx >= 0:
                self.cb_cliente.setCurrentIndex(idx)
        self.ed_nome.setText(conexao["nome"])
        idx = self.cb_tipo.findText(conexao["tipo"])
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)
        self.ed_host.setText(conexao.get("host") or "")
        if conexao.get("porta"):
            self.sp_porta.setValue(int(conexao["porta"]))
        self.ed_banco.setText(conexao.get("banco") or "")
        self.ed_usuario.setText(conexao.get("usuario") or "")
        self.ed_driver.setText(conexao.get("driver") or "")

    def _validar(self):
        if self.cb_cliente.currentData() is None:
            QMessageBox.warning(
                self, "Validação", "Selecione um cliente (Cadastre em Clientes...).")
            return
        if not self.ed_nome.text().strip() or not self.ed_banco.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Nome e Banco/Arquivo são obrigatórios.")
            return
        self.accept()

    def dados(self):
        idx = self.cb_cliente.currentIndex()
        nome_cli = self.cb_cliente.currentText()
        return {
            "nome": self.ed_nome.text().strip(),
            "cliente": nome_cli,
            "cliente_id": self.cb_cliente.itemData(idx),
            "tipo": self.cb_tipo.currentText(),
            "host": self.ed_host.text().strip(),
            "porta": self.sp_porta.value(),
            "banco": self.ed_banco.text().strip(),
            "usuario": self.ed_usuario.text().strip(),
            "driver": self.ed_driver.text().strip(),
        }


class ConexoesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conexões a Bancos de Dados")
        self.resize(720, 440)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Cada conexão pertence a um cliente. Uma conexão por cliente é a PADRÃO.\n"
            "Ao salvar, o banco SQLite é preparado na hora (schema criado) sem travar o app."))

        self.tabela = QTableWidget(0, 7)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Nome", "Cliente", "Tipo", "Banco", "Padrão", "Cliente ID"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(2, 110)
        self.tabela.setColumnWidth(3, 80)
        self.tabela.setColumnWidth(5, 60)
        self.tabela.setColumnWidth(6, 0)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_testar = QPushButton("Testar Conexão")
        btn_padrao = QPushButton("Definir Padrão")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        btn_testar.clicked.connect(self.testar)
        btn_padrao.clicked.connect(self.definir_padrao)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_testar)
        botoes.addWidget(btn_padrao)
        botoes.addStretch()
        layout.addLayout(botoes)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar)

        self.carregar()

    def carregar(self):
        conexoes = ConexaoRepositorio.listar()
        self.tabela.setRowCount(len(conexoes))
        for i, c in enumerate(conexoes):
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.UserRole, c["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(c["nome"]))
            self.tabela.setItem(i, 2, QTableWidgetItem(
                c.get("cliente_nome") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(c["tipo"]))
            self.tabela.setItem(i, 4, QTableWidgetItem(c.get("banco") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(
                "★" if c.get("padrao") else ""))
            self.tabela.setItem(i, 6, QTableWidgetItem(
                str(c.get("cliente_id") or "")))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def novo(self):
        dlg = ConexaoDialog(self)
        if dlg.exec():
            dados = dlg.dados()
            try:
                ConexaoRepositorio.inserir(
                    dados, dlg.ed_senha.text(), dados["cliente_id"])
                # Se a conexão é do cliente ATIVO, garante o schema na hora
                ativo = Database._get_cliente_ativo()
                if ativo and ativo.get("id") == dados["cliente_id"]:
                    Database.init_db()
                self.carregar()
                QMessageBox.information(
                    self, "Sucesso",
                    "Conexão cadastrada com sucesso.\n"
                    "Se for SQLite, o banco já está pronto em data/.")
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro",
                    f"Não foi possível salvar a conexão:\n{e}")

    def editar(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        conexao = ConexaoRepositorio.obter(conexao_id)
        dlg = ConexaoDialog(self, conexao)
        if dlg.exec():
            dados = dlg.dados()
            try:
                ConexaoRepositorio.atualizar(conexao_id, dados,
                                             dlg.ed_senha.text() or None,
                                             dados["cliente_id"])
                ativo = Database._get_cliente_ativo()
                if ativo and ativo.get("id") == dados["cliente_id"]:
                    Database.init_db()
                self.carregar()
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro",
                    f"Não foi possível salvar a conexão:\n{e}")

    def excluir(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir esta conexão?") == QMessageBox.Yes:
            try:
                ConexaoRepositorio.excluir(conexao_id)
                self.carregar()
            except Exception as e:
                QMessageBox.critical(
                    self, "Erro", f"Não foi possível excluir:\n{e}")

    def testar(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        conexao = ConexaoRepositorio.obter(conexao_id)
        senha = obter_senha(conexao_id, conexao.get("senha"))
        ok, msg = Database.testar_conexao(conexao, senha)
        if ok:
            QMessageBox.information(self, "Sucesso", f"✓ {msg}")
        else:
            QMessageBox.critical(self, "Falha", f"✗ Falha ao conectar:\n{msg}")

    def definir_padrao(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        Database.definir_conexao_padrao(conexao_id)
        self.carregar()
