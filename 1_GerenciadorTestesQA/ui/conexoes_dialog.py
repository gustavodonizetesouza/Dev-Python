"""Cadastro de conexões a bancos de dados (SQLite, SQL Server, MySQL)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView, QFormLayout,
    QDialogButtonBox, QComboBox, QSpinBox,
)
from PySide6.QtCore import Qt
from database.models import ConexaoRepositorio
from database.connection import Database
from utils.seguranca import obter_senha


class ConexaoDialog(QDialog):
    def __init__(self, parent=None, conexao=None):
        super().__init__(parent)
        self.conexao = conexao
        self.setWindowTitle("Nova Conexão" if not conexao else "Editar Conexão")
        self.setMinimumWidth(480)

        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.ed_cliente = QLineEdit()
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

        form.addRow("Nome:", self.ed_nome)
        form.addRow("Cliente:", self.ed_cliente)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Host:", self.ed_host)
        form.addRow("Porta:", self.sp_porta)
        form.addRow("Banco/Arquivo:", self.ed_banco)
        form.addRow("Usuário:", self.ed_usuario)
        form.addRow("Senha:", self.ed_senha)
        form.addRow("Driver (SQL Server):", self.ed_driver)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if conexao:
            self._preencher(conexao)

    def _preencher(self, conexao):
        self.ed_nome.setText(conexao["nome"])
        self.ed_cliente.setText(conexao.get("cliente") or "")
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
        if not self.ed_nome.text().strip() or not self.ed_banco.text().strip():
            QMessageBox.warning(self, "Validação", "Nome e Banco/Arquivo são obrigatórios.")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "cliente": self.ed_cliente.text().strip(),
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
        self.resize(640, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cada conexão aponta para o banco de um cliente:"))

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "Cliente", "Tipo", "Banco"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(3, 90)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_testar = QPushButton("Testar Conexão")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        btn_testar.clicked.connect(self.testar)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_testar)
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
            self.tabela.setItem(i, 2, QTableWidgetItem(c.get("cliente") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(c["tipo"]))
            self.tabela.setItem(i, 4, QTableWidgetItem(c.get("banco") or ""))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def novo(self):
        dlg = ConexaoDialog(self)
        if dlg.exec():
            dados = dlg.dados()
            novo_id = ConexaoRepositorio.inserir(dados, dlg.ed_senha.text())
            # Se for SQLite, já cria o schema na hora (fica pronto)
            if dados["tipo"] == "sqlite":
                cfg = ConexaoRepositorio.obter(novo_id)
                Database.criar_schema_para(cfg)
            # Torna a nova conexão a ATIVA
            Database.definir_conexao_ativa(novo_id)
            self.carregar()

    def editar(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        conexao = ConexaoRepositorio.obter(conexao_id)
        dlg = ConexaoDialog(self, conexao)
        if dlg.exec():
            ConexaoRepositorio.atualizar(conexao_id, dlg.dados(),
                                         dlg.ed_senha.text() or None)
            self.carregar()

    def excluir(self):
        conexao_id = self._selecionado()
        if not conexao_id:
            QMessageBox.information(self, "Aviso", "Selecione uma conexão.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir esta conexão?") == QMessageBox.Yes:
            ConexaoRepositorio.excluir(conexao_id)
            self.carregar()

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