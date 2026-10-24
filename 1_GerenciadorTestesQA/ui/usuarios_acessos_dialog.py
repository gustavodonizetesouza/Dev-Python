"""Usuários e Acessos (Fase 1) — Configurações → Usuários e Acessos...

Gerencia a identidade de LOGIN do sistema (usuarios_sistema): perfil, senha,
ativo e o vínculo N:N usuário ↔ clientes (escopo do seletor do rodapé).

IMPORTANTE: esta identidade de login é GLOBAL (banco de configuração) e é
diferente do catálogo 'usuarios' por cliente (Cadastro → Usuários), que
continua servindo como lista de analistas/responsáveis dos casos.

Somente o perfil Administrador acessa esta tela.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QLineEdit, QComboBox,
    QCheckBox, QFormLayout, QListWidget, QListWidgetItem, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from database.acessos import (
    PerfilRepositorio, UsuarioSistemaRepositorio, UsuarioClienteRepositorio,
)


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


class UsuarioFormDialog(QDialog):
    """Formulário de usuário do sistema (novo/editar)."""

    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle(
            "Novo Usuário" if not usuario else "Editar Usuário")
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.ed_login = QLineEdit()
        self.ed_nome = QLineEdit()
        self.cb_perfil = QComboBox()
        try:
            for p in PerfilRepositorio.listar():
                self.cb_perfil.addItem(p["nome"], p["id"])
        except Exception:
            _log_erro()
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.Password)
        if usuario:
            self.ed_senha.setPlaceholderText(
                "Deixe vazio para manter a senha atual")
        else:
            self.ed_senha.setPlaceholderText("Defina a senha de acesso")
        self.cb_ativo = QCheckBox("Ativo (pode fazer login)")
        self.cb_ativo.setChecked(True)

        form.addRow("Login:", self.ed_login)
        form.addRow("Nome:", self.ed_nome)
        form.addRow("Perfil:", self.cb_perfil)
        form.addRow("Senha:", self.ed_senha)
        form.addRow("", self.cb_ativo)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        if usuario:
            self.ed_login.setText(usuario.get("login") or "")
            self.ed_nome.setText(usuario.get("nome") or "")
            idx = self.cb_perfil.findData(usuario.get("perfil_id"))
            if idx >= 0:
                self.cb_perfil.setCurrentIndex(idx)
            self.cb_ativo.setChecked(bool(usuario.get("ativo", 1)))

    def _validar(self):
        if not self.ed_login.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o login.")
            return
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome.")
            return
        if not self.usuario and not self.ed_senha.text():
            QMessageBox.warning(self, "Validação", "Defina a senha de acesso.")
            return
        self.accept()

    def dados(self):
        return {
            "login": self.ed_login.text().strip(),
            "nome": self.ed_nome.text().strip(),
            "perfil_id": self.cb_perfil.currentData(),
            "ativo": 1 if self.cb_ativo.isChecked() else 0,
            "senha": self.ed_senha.text(),
        }


class UsuarioClientesDialog(QDialog):
    """Vínculo N:N usuário ↔ clientes (escopo de acesso)."""

    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario
        titulo = "Clientes do Usuário"
        if usuario:
            titulo = f"Clientes de {usuario.get('nome') or usuario.get('login')}"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Marque os clientes que este usuário pode ver no seletor do rodapé.\n"
            "Administradores veem todos os clientes automaticamente."))

        self.lista = QListWidget()
        layout.addWidget(self.lista)

        botoes = QHBoxLayout()
        btn_salvar = QPushButton("Salvar")
        btn_cancelar = QPushButton("Cancelar")
        btn_salvar.clicked.connect(self._salvar)
        btn_cancelar.clicked.connect(self.reject)
        botoes.addStretch()
        botoes.addWidget(btn_salvar)
        botoes.addWidget(btn_cancelar)
        layout.addLayout(botoes)

        self._carregar()

    def _carregar(self):
        self.lista.clear()
        try:
            clientes = UsuarioClienteRepositorio.listar_todos_com_marcacao(
                self.usuario["id"])
        except Exception:
            _log_erro()
            clientes = []
        for c in clientes:
            rotulo = c["nome"] + ("" if c.get("ativo") else "  (inativo)")
            item = QListWidgetItem(rotulo)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if c.get(
                "vinculado") else Qt.Unchecked)
            item.setData(Qt.UserRole, c["id"])
            self.lista.addItem(item)

    def _salvar(self):
        ids = []
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        try:
            UsuarioClienteRepositorio.definir_vinculos(self.usuario["id"], ids)
        except Exception:
            _log_erro()
            QMessageBox.critical(
                self, "Erro", "Falha ao salvar vínculos. Veja erros.log")
            return
        self.accept()


class UsuariosAcessosDialog(QDialog):
    def __init__(self, parent=None, usuario_logado=None):
        super().__init__(parent)
        self.usuario_logado = usuario_logado or {}
        self.setWindowTitle("Usuários e Acessos")
        self.resize(680, 440)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Identidade de login do sistema (global) e escopo de clientes por usuário.\n"
            "O catálogo de analistas por cliente continua em Cadastro → Usuários."))

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Login", "Nome", "Perfil", "Ativo", "Clientes"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 120)
        self.tabela.setColumnWidth(3, 130)
        self.tabela.setColumnWidth(4, 60)
        self.tabela.setColumnWidth(5, 80)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.doubleClicked.connect(self._editar)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo")
        btn_editar = QPushButton("Editar")
        btn_clientes = QPushButton("Clientes...")
        btn_excluir = QPushButton("Excluir")
        btn_fechar = QPushButton("Fechar")
        btn_novo.clicked.connect(self._novo)
        btn_editar.clicked.connect(self._editar)
        btn_clientes.clicked.connect(self._clientes)
        btn_excluir.clicked.connect(self._excluir)
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_clientes)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

        self.carregar()

    def carregar(self):
        try:
            usuarios = UsuarioSistemaRepositorio.listar()
        except Exception:
            _log_erro()
            usuarios = []
        self.tabela.setRowCount(len(usuarios))
        for i, u in enumerate(usuarios):
            id_item = QTableWidgetItem(str(u["id"]))
            id_item.setData(Qt.UserRole, u["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(u.get("login") or ""))
            self.tabela.setItem(i, 2, QTableWidgetItem(u.get("nome") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(
                u.get("perfil_nome") or ""))
            self.tabela.setItem(i, 4, QTableWidgetItem(
                "Sim" if u.get("ativo") else "Não"))
            self.tabela.setItem(i, 5, QTableWidgetItem(
                str(u.get("total_clientes") or 0)))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        item = self.tabela.item(linha, 0)
        return item.data(Qt.UserRole) if item else None

    def _novo(self):
        dlg = UsuarioFormDialog(self)
        if dlg.exec():
            d = dlg.dados()
            try:
                novo_id, erro = UsuarioSistemaRepositorio.inserir(
                    d["login"], d["nome"], d["senha"], d["perfil_id"], d["ativo"])
            except Exception:
                _log_erro()
                QMessageBox.critical(
                    self, "Erro", "Falha ao salvar. Veja erros.log")
                return
            if novo_id is None:
                QMessageBox.warning(
                    self, "Atenção", erro or "Não foi possível salvar.")
                return
            self.carregar()

    def _usuario_da_linha(self):
        usuario_id = self._selecionado()
        if not usuario_id:
            QMessageBox.information(self, "Aviso", "Selecione um usuário.")
            return None
        try:
            return UsuarioSistemaRepositorio.obter(usuario_id)
        except Exception:
            _log_erro()
            return None

    def _editar(self):
        usuario = self._usuario_da_linha()
        if not usuario:
            return
        dlg = UsuarioFormDialog(self, usuario)
        if dlg.exec():
            d = dlg.dados()
            try:
                ok, msg = UsuarioSistemaRepositorio.atualizar(
                    usuario["id"], d, senha=d["senha"] or None)
            except Exception:
                _log_erro()
                QMessageBox.critical(
                    self, "Erro", "Falha ao atualizar. Veja erros.log")
                return
            if ok:
                self.carregar()
            else:
                QMessageBox.warning(self, "Atenção", msg)

    def _clientes(self):
        usuario = self._usuario_da_linha()
        if not usuario:
            return
        dlg = UsuarioClientesDialog(self, usuario)
        if dlg.exec():
            self.carregar()

    def _excluir(self):
        usuario_id = self._selecionado()
        if not usuario_id:
            QMessageBox.information(self, "Aviso", "Selecione um usuário.")
            return
        if QMessageBox.question(self, "Confirmar",
                                "Excluir este usuário do sistema?") != QMessageBox.Yes:
            return
        try:
            ok, msg = UsuarioSistemaRepositorio.excluir(
                usuario_id, usuario_logado_id=self.usuario_logado.get("id"))
        except Exception:
            _log_erro()
            QMessageBox.critical(
                self, "Erro", "Falha ao excluir. Veja erros.log")
            return
        if ok:
            self.carregar()
        else:
            QMessageBox.warning(self, "Atenção", msg)
