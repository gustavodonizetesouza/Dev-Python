"""Janela principal com abas."""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QHeaderView,
)
from PySide6.QtCore import QCoreApplication
from .casos_widget import CasosWidget
from .ciclos_widget import CiclosWidget
from .execucao_widget import ExecucaoWidget
from .relatorios_widget import RelatoriosWidget
from .modulos_dialog import ModulosDialog
from utils.themes import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador Testes Essencial — Virada de Versão")
        self.resize(1100, 700)

        self._criar_menu()

        self.tabs = QTabWidget()
        self.casos = CasosWidget()
        self.ciclos = CiclosWidget()
        self.execucao = ExecucaoWidget()
        self.relatorios = RelatoriosWidget()

        self.tabs.addTab(self.casos, "Casos de Teste")
        self.tabs.addTab(self.ciclos, "Ciclos de Virada")
        self.tabs.addTab(self.execucao, "Execução")
        self.tabs.addTab(self.relatorios, "Relatórios & KPIs")

        self.setCentralWidget(self.tabs)

        # Ao trocar de aba, sincroniza ciclos nos widgets dependentes
        self.tabs.currentChanged.connect(self._on_aba)
        self.statusBar().showMessage("Pronto")

    def _criar_menu(self):
        """Cria a barra de menu (Cadastros + Tema)."""
        barra = self.menuBar()

        # Menu de cadastros
        menu_cadastros = barra.addMenu("Cadastros")
        acao_modulos = menu_cadastros.addAction("Módulos...")
        acao_modulos.triggered.connect(self._abrir_modulos)

        # Menu de tema
        menu_tema = barra.addMenu("Tema")
        acao_claro = menu_tema.addAction("Claro")
        acao_escuro = menu_tema.addAction("Escuro")
        acao_sistema = menu_tema.addAction("Sistema (segue o Windows)")

        acao_claro.triggered.connect(lambda: self._trocar_tema("claro"))
        acao_escuro.triggered.connect(lambda: self._trocar_tema("escuro"))
        acao_sistema.triggered.connect(lambda: self._trocar_tema("sistema"))

    def _abrir_modulos(self):
        dlg = ModulosDialog(self)
        dlg.exec()
        # Atualiza os combos da aba Casos se o usuário cadastrou módulos novos
        self.casos.carregar()

    def _trocar_tema(self, tema):
        """Aplica o tema e atualiza a barra de status."""
        app = QCoreApplication.instance()
        ThemeManager.aplicar(app, tema)
        self.statusBar().showMessage(f"Tema alterado para: {tema}", 3000)

    def _on_aba(self, index):
        if index == 2:  # Execução
            self.execucao.carregar_ciclos()
        elif index == 3:  # Relatórios
            self.relatorios.carregar_ciclos()
