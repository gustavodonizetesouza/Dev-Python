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

        # Ciclo selecionado na aba 1 alimenta a aba 2 (casos do ciclo)
        self.ciclos.cicloMudou.connect(self.casos.definir_ciclo)
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

        menu_cadastros = barra.addMenu("Cadastros")
        acao_modulos = menu_cadastros.addAction("Módulos...")
        acao_modulos.triggered.connect(self._abrir_modulos)
        acao_usuarios = menu_cadastros.addAction("Usuários...")
        acao_usuarios.triggered.connect(self._abrir_usuarios)
        acao_clientes = menu_cadastros.addAction("Clientes...")
        acao_clientes.triggered.connect(self._abrir_clientes)
        acao_conexoes = menu_cadastros.addAction("Conexões a Bancos...")
        acao_conexoes.triggered.connect(self._abrir_conexoes)
        acao_tipos = menu_cadastros.addAction("Tipos de Ciclo...")
        acao_tipos.triggered.connect(self._abrir_tipos_ciclo)

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
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())

    def _abrir_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())

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

    def _recarregar(self):
        """Recarrega o seletor de clientes e todos os dados."""
        self._preencher_seletor_clientes()
        self.ciclos.carregar()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        self.execucao.carregar_ciclos()
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
            self.execucao.carregar_ciclos()
        elif index == 3:  # Melhorias
            self.melhorias.carregar()
        elif index == 4:  # Relatórios
            self.relatorios.carregar_ciclos()
