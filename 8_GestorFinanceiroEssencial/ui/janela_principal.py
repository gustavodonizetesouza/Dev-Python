"""Janela principal: navegação lateral, troca de páginas, tema e sessão.

O painel de Usuários aparece apenas quando o usuário logado é admin.
O botão 'Sair da conta' encerra a sessão e sinaliza ao main.py para
reabrir a tela de login (sem fechar a aplicação).
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QPushButton,
                             QStackedWidget, QVBoxLayout, QWidget)

from ui.paginas import (PaginaCategorias, PaginaContas, PaginaDashboard,
                        PaginaLancamentos, PaginaRecorrencias,
                        PaginaRelatorios, PaginaUsuarios)
from ui.tema import alternar_tema, aplicar_tema, ler_tema, salvar_tema


class JanelaPrincipal(QMainWindow):
    sair_solicitado = pyqtSignal()

    PAGINAS = [("Dashboard", PaginaDashboard),
               ("Lançamentos", PaginaLancamentos),
               ("Contas", PaginaContas),
               ("Categorias", PaginaCategorias),
               ("Recorrências", PaginaRecorrencias),
               ("Relatórios", PaginaRelatorios)]

    def __init__(self, repo, repo_usuarios, sessao, descricao_banco=""):
        super().__init__()
        self.repo = repo
        self.repo_usuarios = repo_usuarios
        self.sessao = sessao
        self.setWindowTitle(
            f"Gestor Financeiro — {self.sessao.usuario.nome}")
        self.resize(1080, 680)
        self.setMinimumSize(940, 600)

        central = QWidget()
        raiz = QHBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        self.setCentralWidget(central)

        # ---------- barra lateral ----------
        lateral_frame = QFrame()
        lateral_frame.setFixedWidth(210)
        lateral = QVBoxLayout(lateral_frame)
        lateral.setContentsMargins(12, 14, 12, 14)
        lateral.setSpacing(4)

        titulo = QLabel("Gestor Financeiro")
        titulo.setObjectName("tituloApp")
        titulo.setWordWrap(True)
        lateral.addWidget(titulo)
        lateral.addSpacing(8)

        # ---------- cartão do usuário logado ----------
        card_usuario = QFrame()
        card_usuario.setObjectName("card")
        vu = QVBoxLayout(card_usuario)
        vu.setContentsMargins(10, 8, 10, 8)
        vu.setSpacing(2)
        lb_nome = QLabel(self.sessao.usuario.nome)
        lb_nome.setObjectName("tituloCard")
        lb_nome.setWordWrap(True)
        lb_email = QLabel(self.sessao.usuario.email)
        lb_email.setObjectName("tituloCard")
        lb_email.setWordWrap(True)
        lb_papel = QLabel(
            "Administrador" if self.sessao.eh_admin else "Usuário")
        lb_papel.setObjectName("tituloCard")
        vu.addWidget(lb_nome)
        vu.addWidget(lb_email)
        vu.addWidget(lb_papel)
        lateral.addWidget(card_usuario)
        lateral.addSpacing(10)

        # ---------- navegação ----------
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.stack = QStackedWidget()
        self.paginas = []

        def _adicionar_pagina(nome, pagina):
            idx = len(self.paginas)
            pagina.dados_alterados.connect(self._refrescar_todas)
            self.paginas.append(pagina)
            self.stack.addWidget(pagina)
            bt = QPushButton(nome)
            bt.setObjectName("nav")
            bt.setCheckable(True)
            bt.setCursor(Qt.CursorShape.PointingHandCursor)
            bt.clicked.connect(lambda _=False, i=idx: self._ir_para(i))
            self.grupo.addButton(bt)
            lateral.addWidget(bt)

        for nome, cls in self.PAGINAS:
            _adicionar_pagina(nome, cls(repo))

        # Página de administração — somente para admins.
        if self.sessao.eh_admin:
            _adicionar_pagina("Usuários",
                              PaginaUsuarios(self.repo_usuarios, self.sessao))

        self.grupo.buttons()[0].setChecked(True)
        lateral.addStretch()

        bt_tema = QPushButton("Alternar tema")
        bt_tema.setObjectName("nav")
        bt_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        bt_tema.clicked.connect(self._alternar_tema)
        lateral.addWidget(bt_tema)

        bt_sair = QPushButton("Sair da conta")
        bt_sair.setObjectName("nav")
        bt_sair.setCursor(Qt.CursorShape.PointingHandCursor)
        bt_sair.clicked.connect(self._sair)
        lateral.addWidget(bt_sair)

        raiz.addWidget(lateral_frame)
        raiz.addWidget(self.stack, 1)

        self.statusBar().showMessage(
            f"Banco de dados: {descricao_banco} | Usuário: "
            f"{self.sessao.usuario.email}" if descricao_banco else "")
        self._ir_para(0)

    def _ir_para(self, idx):
        self.stack.setCurrentIndex(idx)
        self.paginas[idx].refrescar()

    def _refrescar_todas(self):
        for pagina in self.paginas:
            pagina.refrescar()

    def _alternar_tema(self):
        novo = alternar_tema(ler_tema())
        salvar_tema(novo)
        aplicar_tema(QApplication.instance(), novo)

    def _sair(self):
        r = QMessageBox.question(
            self, "Sair da conta",
            "Deseja sair da conta e voltar à tela de login?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.sair_solicitado.emit()
            self.close()
