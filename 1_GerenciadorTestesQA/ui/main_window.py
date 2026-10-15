"""Janela principal com abas."""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QComboBox,
)
from PySide6.QtCore import Qt, QCoreApplication
from .ciclos_widget import CiclosWidget
from .casos_widget import CasosWidget
from .execucao_widget import ExecucaoWidget
from .relatorios_widget import RelatoriosWidget
from .melhorias_widget import MelhoriasWidget
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog
from .clientes_dialog import ClientesDialog
from .conexoes_dialog import ConexoesDialog
from .tipos_ciclo_dialog import TiposCicloDialog
from .tipos_teste_dialog import TiposTesteDialog
from utils.themes import ThemeManager
from database.models import ClienteRepositorio
from database.connection import Database


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador Testes Essencial — Virada de Versão")
        self.resize(1280, 800)

        self._criar_menu()

        self.tabs = QTabWidget()
        self.ciclos = CiclosWidget()
        self.casos = CasosWidget()
        self.execucao = ExecucaoWidget()
        self.melhorias = MelhoriasWidget()
        self.relatorios = RelatoriosWidget()

        self.tabs.addTab(self.ciclos, "Ciclos")
        self.tabs.addTab(self.casos, "Casos do Ciclo")
        self.tabs.addTab(self.execucao, "Execução")
        self.tabs.addTab(self.melhorias, "Melhorias")
        self.tabs.addTab(self.relatorios, "Relatórios & KPIs")

        self.setCentralWidget(self.tabs)

        self.setWindowState(Qt.WindowMaximized)

        # Ciclo selecionado na aba 1 alimenta as abas Casos e Execução
        self.ciclos.cicloMudou.connect(self.casos.definir_ciclo)
        self.ciclos.cicloMudou.connect(self.execucao.definir_ciclo)
        self.tabs.currentChanged.connect(self._on_aba)
        self.statusBar().showMessage("Pronto")

        self.cb_cliente = QComboBox()
        self.cb_cliente.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cb_cliente.setMinimumContentsLength(18)
        self.cb_cliente.currentIndexChanged.connect(self._trocar_cliente)
        self.statusBar().addPermanentWidget(self.cb_cliente)
        self._preencher_seletor_clientes()

    def _criar_menu(self):
        barra = self.menuBar()

        # ---- MENU CADASTRO (catálogos) ----
        menu_cadastro = barra.addMenu("Cadastro")
        acao_modulos = menu_cadastro.addAction("Módulos...")
        acao_modulos.triggered.connect(self._abrir_modulos)
        acao_clientes = menu_cadastro.addAction("Clientes...")
        acao_clientes.triggered.connect(self._abrir_clientes)
        acao_usuarios = menu_cadastro.addAction("Usuários...")
        acao_usuarios.triggered.connect(self._abrir_usuarios)

        # ---- MENU CONFIGURAÇÕES (parametrização do sistema) ----
        menu_config = barra.addMenu("Configurações")
        acao_tipos_ciclo = menu_config.addAction("Tipos de Ciclo...")
        acao_tipos_ciclo.triggered.connect(self._abrir_tipos_ciclo)
        acao_tipos_teste = menu_config.addAction("Tipos de Teste...")
        acao_tipos_teste.triggered.connect(self._abrir_tipos_teste)
        acao_conexoes = menu_config.addAction("Conexões a Bancos...")
        acao_conexoes.triggered.connect(self._abrir_conexoes)

        # ---- MENU TEMA ----
        menu_tema = barra.addMenu("Tema")
        acao_claro = menu_tema.addAction("Claro")
        acao_escuro = menu_tema.addAction("Escuro")
        acao_sistema = menu_tema.addAction("Sistema (segue o Windows)")

        acao_claro.triggered.connect(lambda: self._trocar_tema("claro"))
        acao_escuro.triggered.connect(lambda: self._trocar_tema("escuro"))
        acao_sistema.triggered.connect(lambda: self._trocar_tema("sistema"))

    # ---------- Handlers dos menus (é AQUI que o método entra) ----------

    def _abrir_modulos(self):
        dlg = ModulosDialog(self)
        dlg.exec()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        self.execucao.definir_ciclo(self.ciclos.ciclo_atual())

    def _abrir_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        self.execucao.definir_ciclo(self.ciclos.ciclo_atual())

    def _abrir_clientes(self):
        dlg = ClientesDialog(self)
        dlg.exec()
        self._recarregar()

    def _abrir_conexoes(self):
        dlg = ConexoesDialog(self)
        dlg.exec()
        self._recarregar()

    def _abrir_tipos_ciclo(self):
        dlg = TiposCicloDialog(self)
        dlg.exec()
        self.ciclos.carregar()

    def _abrir_tipos_teste(self):
        dlg = TiposTesteDialog(self)
        dlg.exec()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())

    def _recarregar(self):
        """Recarrega o seletor de clientes e todos os dados."""
        self._preencher_seletor_clientes()
        self.ciclos.carregar()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        self.execucao.definir_ciclo(self.ciclos.ciclo_atual())
        self.melhorias.carregar()
        self.relatorios.carregar_ciclos()

    def _preencher_seletor_clientes(self):
        self.cb_cliente.blockSignals(True)
        self.cb_cliente.clear()
        for c in ClienteRepositorio.listar(apenas_ativos=True):
            self.cb_cliente.addItem(c["nome"], c["id"])
        ativo = Database._get_cliente_ativo()
        if ativo and ativo.get("id"):
            idx = self.cb_cliente.findData(ativo["id"])
            if idx >= 0:
                self.cb_cliente.setCurrentIndex(idx)
        self.cb_cliente.blockSignals(False)
        self.cb_cliente.setMinimumContentsLength(18)
        self.cb_cliente.adjustSize()

    def _trocar_cliente(self, index):
        cliente_id = self.cb_cliente.itemData(index)
        if cliente_id is None:
            return
        Database.definir_cliente_ativo(cliente_id)
        Database.init_db()
        self._recarregar()
        self.statusBar().showMessage(
            f"Cliente ativo: {self.cb_cliente.currentText()}", 3000)

    def _trocar_tema(self, tema):
        app = QCoreApplication.instance()
        ThemeManager.aplicar(app, tema)
        self.statusBar().showMessage(f"Tema alterado para: {tema}", 3000)

    def _on_aba(self, index):
        if index == 0:  # Ciclos
            self.ciclos.carregar()
        elif index == 1:  # Casos do Ciclo
            self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        elif index == 2:  # Execução
            self.execucao.definir_ciclo(self.ciclos.ciclo_atual())
        elif index == 3:  # Melhorias
            self.melhorias.carregar()
        elif index == 4:  # Relatórios
            self.relatorios.carregar_ciclos()