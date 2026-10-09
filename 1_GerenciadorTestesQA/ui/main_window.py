"""Janela principal com abas."""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QComboBox,
)
from PySide6.QtCore import Qt, QCoreApplication
from .casos_widget import CasosWidget
from .ciclos_widget import CiclosWidget
from .execucao_widget import ExecucaoWidget
from .relatorios_widget import RelatoriosWidget
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog
from .conexoes_dialog import ConexoesDialog
from utils.themes import ThemeManager
from database.models import ConexaoRepositorio
from database.connection import Database


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador Testes Essencial — Virada de Versão")
        self.resize(1280, 800)

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

        # Inicia maximizado
        self.setWindowState(Qt.WindowMaximized)

        self.tabs.currentChanged.connect(self._on_aba)
        self.statusBar().showMessage("Pronto")

        # Seletor de conexão ativa na barra de status
        self.cb_conexao = QComboBox()
        self.cb_conexao.currentIndexChanged.connect(self._trocar_conexao)
        self.statusBar().addPermanentWidget(self.cb_conexao)
        self._preencher_seletor_conexao()

    def _criar_menu(self):
        """Cria a barra de menu (Cadastros + Tema)."""
        barra = self.menuBar()

        # Menu de cadastros
        menu_cadastros = barra.addMenu("Cadastros")
        acao_modulos = menu_cadastros.addAction("Módulos...")
        acao_modulos.triggered.connect(self._abrir_modulos)
        acao_usuarios = menu_cadastros.addAction("Usuários...")
        acao_usuarios.triggered.connect(self._abrir_usuarios)
        acao_conexoes = menu_cadastros.addAction("Conexões a Bancos...")
        acao_conexoes.triggered.connect(self._abrir_conexoes)

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
        self.casos.carregar()

    def _abrir_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        self.casos.carregar()

    def _abrir_conexoes(self):
        dlg = ConexoesDialog(self)
        dlg.exec()
        self._recarregar_conexao()

    def _recarregar_conexao(self):
        """Recarrega o seletor e todos os dados após trocar de conexão."""
        self._preencher_seletor_conexao()
        self.casos.carregar()
        self.ciclos.carregar()
        self.execucao.carregar_ciclos()
        self.relatorios.carregar_ciclos()

    def _preencher_seletor_conexao(self):
        """Preenche o combo da barra de status com as conexões cadastradas."""
        self.cb_conexao.blockSignals(True)
        self.cb_conexao.clear()
        conexoes = ConexaoRepositorio.listar()
        for c in conexoes:
            self.cb_conexao.addItem(f"{c['nome']} ({c['tipo']})", c["id"])
        # Marca a conexão ativa
        ativa = Database._get_conexao_ativa()
        if ativa:
            idx = self.cb_conexao.findData(ativa["id"])
            if idx >= 0:
                self.cb_conexao.setCurrentIndex(idx)
        self.cb_conexao.blockSignals(False)

    def _trocar_conexao(self, index):
        """Ao trocar no seletor, define a nova conexão ativa e recarrega."""
        conexao_id = self.cb_conexao.itemData(index)
        if conexao_id is None:
            return
        Database.definir_conexao_ativa(conexao_id)
        Database.init_db()  # garante o schema na conexão nova
        self._recarregar_conexao()
        self.statusBar().showMessage(
            f"Conexão ativa: {self.cb_conexao.currentText()}", 3000)

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
