"""Janela principal com abas — login, seleção de conexão e escopo de clientes.

- Login obrigatório antes de abrir o app (LoginDialog);
- SELEÇÃO DE CONEXÃO pós-login (mobilidade);
- Seletor de clientes do rodapé com escopo por usuário;
- Abas: Ciclos, Casos, Execução, Melhorias, Relatórios, Chamados, Base de Conhecimento.
"""
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QComboBox, QLabel, QDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QCoreApplication

from .ciclos_widget import CiclosWidget
from .casos_widget import CasosWidget
from .execucao_widget import ExecucaoWidget
from .relatorios_widget import RelatoriosWidget
from .melhorias_widget import MelhoriasWidget
from .chamados_widget import ChamadosWidget
from .kb_widget import KbWidget
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog
from .clientes_dialog import ClientesDialog
from .conexoes_dialog import ConexoesDialog
from .tipos_ciclo_dialog import TiposCicloDialog
from .tipos_teste_dialog import TiposTesteDialog
from .login_dialog import LoginDialog
from .usuarios_acessos_dialog import UsuariosAcessosDialog
from .selecao_conexao_dialog import SelecaoConexaoDialog
from utils.themes import ThemeManager
from database.models import ClienteRepositorio
from database.acessos import UsuarioClienteRepositorio
from database.connection import Database, SESSAO_MEMORIA


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador Testes Essencial — Virada de Versão")
        self.resize(1280, 800)

        # ---------- LOGIN — antes de montar qualquer tela ----------
        dlg = LoginDialog(None)
        if dlg.exec() != QDialog.Accepted or not dlg.usuario:
            raise SystemExit(0)
        self.usuario_logado = dlg.usuario

        if not self._usuario_e_admin():
            try:
                tem_clientes = bool(UsuarioClienteRepositorio.listar_clientes(
                    self.usuario_logado["id"], apenas_ativos=True))
            except Exception:
                tem_clientes = False
            if not tem_clientes:
                QMessageBox.warning(
                    self, "Sem acesso",
                    "Seu usuário não possui clientes vinculados.\n"
                    "Solicite ao administrador o vínculo em:\n"
                    "Configurações → Usuários e Acessos...")
                raise SystemExit(0)

        # ---------- SELEÇÃO DE CONEXÃO (mobilidade) ----------
        self._selecionar_conexao_inicial()

        self._criar_menu()

        # ---------- ABAS ----------
        self.tabs = QTabWidget()
        self.ciclos = CiclosWidget()
        self.casos = CasosWidget()
        self.execucao = ExecucaoWidget()
        self.melhorias = MelhoriasWidget()
        self.relatorios = RelatoriosWidget()
        self.chamados = ChamadosWidget(usuario_logado=self.usuario_logado)
        self.kb = KbWidget(usuario_logado=self.usuario_logado)

        self.tabs.addTab(self.ciclos, "Ciclos")
        self.tabs.addTab(self.casos, "Casos do Ciclo")
        self.tabs.addTab(self.execucao, "Execução")
        self.tabs.addTab(self.melhorias, "Melhorias")
        self.tabs.addTab(self.relatorios, "Relatórios & KPIs")
        self.tabs.addTab(self.chamados, "Chamados")
        self.tabs.addTab(self.kb, "Base de Conhecimento")

        self.setCentralWidget(self.tabs)
        self.setWindowState(Qt.WindowMaximized)

        self.ciclos.cicloMudou.connect(self.casos.definir_ciclo)
        self.ciclos.cicloMudou.connect(self.execucao.definir_ciclo)
        self.tabs.currentChanged.connect(self._on_aba)
        self.statusBar().showMessage("Pronto")

        self.lbl_usuario = QLabel("")
        self.statusBar().addPermanentWidget(self.lbl_usuario)

        self.cb_cliente = QComboBox()
        self.cb_cliente.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cb_cliente.setMinimumContentsLength(18)
        self.cb_cliente.currentIndexChanged.connect(self._trocar_cliente)
        self.statusBar().addPermanentWidget(self.cb_cliente)

        self.lbl_conexao = QLabel("")
        self.statusBar().addPermanentWidget(self.lbl_conexao)

        self._mostrar_usuario()
        self._garantir_cliente_permitido()
        self._preencher_seletor_clientes()
        self._mostrar_conexao_ativa()

    # ---------- Sessão / escopo de acesso ----------
    def _usuario_e_admin(self):
        return (self.usuario_logado or {}).get("perfil_nome") == "Administrador"

    def _mostrar_usuario(self):
        u = self.usuario_logado or {}
        nome = u.get("nome") or u.get("login") or "?"
        perfil = u.get("perfil_nome") or "?"
        self.lbl_usuario.setText(f"Usuário: {nome} ({perfil})   ")

    # ---------- Seleção de conexão ----------
    def _aplicar_escolha_conexao(self, dlg):
        if dlg.usar_temporario:
            Database.definir_conexao_sessao(SESSAO_MEMORIA)
            return
        cx = dlg.conexao_escolhida
        if cx:
            Database.definir_conexao_sessao(cx["id"])
            if cx.get("cliente_id"):
                Database.definir_cliente_ativo(cx["cliente_id"])
            Database.init_db()

    def _selecionar_conexao_inicial(self):
        dlg = SelecaoConexaoDialog(None, usuario=self.usuario_logado)
        if dlg.exec() != QDialog.Accepted:
            Database.limpar_conexao_sessao()
            return
        self._aplicar_escolha_conexao(dlg)

    def _trocar_conexao(self):
        dlg = SelecaoConexaoDialog(self, usuario=self.usuario_logado)
        if dlg.exec() != QDialog.Accepted:
            return
        self._aplicar_escolha_conexao(dlg)
        self._preencher_seletor_clientes()
        self._mostrar_conexao_ativa()
        self._recarregar()
        self.statusBar().showMessage("Conexão da sessão alterada.", 3000)

    def _mostrar_conexao_ativa(self):
        estado = Database.conexao_sessao_ativa()
        if estado == SESSAO_MEMORIA:
            self.lbl_conexao.setText(
                "Conexão: banco temporário da sessão (dados não salvos)   ")
            return
        cfg = Database._get_conexao_sessao()
        origem = "sessão"
        if cfg is None:
            cliente = Database._get_cliente_ativo()
            cfg = None
            if cliente.get("id"):
                cfg = Database._get_conexao_padrao_cliente(cliente["id"])
            origem = "padrão do cliente"
        if cfg:
            destino = cfg.get("banco") or ""
            if cfg.get("tipo") == "sqlserver" and cfg.get("host"):
                destino = f"{cfg['host']} · {destino}"
            self.lbl_conexao.setText(
                f"Conexão: {cfg.get('nome')} ({cfg.get('tipo')}) [{origem}]   ")
        else:
            self.lbl_conexao.setText("Conexão: banco temporário da sessão   ")

    def _clientes_permitidos(self):
        if self._usuario_e_admin():
            try:
                return ClienteRepositorio.listar(apenas_ativos=True)
            except Exception:
                return []
        try:
            return UsuarioClienteRepositorio.listar_clientes(
                self.usuario_logado["id"], apenas_ativos=True)
        except Exception:
            return []

    def _garantir_cliente_permitido(self):
        permitidos = self._clientes_permitidos()
        if not permitidos:
            return
        ids = {c["id"] for c in permitidos}
        ativo = Database._get_cliente_ativo()
        if not ativo.get("id") or ativo["id"] not in ids:
            Database.definir_cliente_ativo(permitidos[0]["id"])
            Database.init_db()

    def _criar_menu(self):
        barra = self.menuBar()

        menu_cadastro = barra.addMenu("Cadastro")
        acao_modulos = menu_cadastro.addAction("Módulos...")
        acao_modulos.triggered.connect(self._abrir_modulos)
        acao_clientes = menu_cadastro.addAction("Clientes...")
        acao_clientes.triggered.connect(self._abrir_clientes)
        acao_usuarios = menu_cadastro.addAction("Usuários...")
        acao_usuarios.triggered.connect(self._abrir_usuarios)

        menu_config = barra.addMenu("Configurações")
        acao_tipos_ciclo = menu_config.addAction("Tipos de Ciclo...")
        acao_tipos_ciclo.triggered.connect(self._abrir_tipos_ciclo)
        acao_tipos_teste = menu_config.addAction("Tipos de Teste...")
        acao_tipos_teste.triggered.connect(self._abrir_tipos_teste)
        acao_conexoes = menu_config.addAction("Conexões a Bancos...")
        acao_conexoes.triggered.connect(self._abrir_conexoes)
        acao_trocar_conexao = menu_config.addAction("Trocar Conexão...")
        acao_trocar_conexao.setToolTip(
            "Escolhe outra conexão de dados para esta sessão "
            "(ex.: nuvem ↔ local, conforme a rede disponível).")
        acao_trocar_conexao.triggered.connect(self._trocar_conexao)
        if self._usuario_e_admin():
            acao_usuarios_acessos = menu_config.addAction(
                "Usuários e Acessos...")
            acao_usuarios_acessos.triggered.connect(
                self._abrir_usuarios_acessos)

        menu_tema = barra.addMenu("Tema")
        acao_claro = menu_tema.addAction("Claro")
        acao_escuro = menu_tema.addAction("Escuro")
        acao_sistema = menu_tema.addAction("Sistema (segue o Windows)")
        acao_claro.triggered.connect(lambda: self._trocar_tema("claro"))
        acao_escuro.triggered.connect(lambda: self._trocar_tema("escuro"))
        acao_sistema.triggered.connect(lambda: self._trocar_tema("sistema"))

    # ---------- Handlers dos menus ----------
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

    def _abrir_usuarios_acessos(self):
        dlg = UsuariosAcessosDialog(self, usuario_logado=self.usuario_logado)
        dlg.exec()
        self._preencher_seletor_clientes()
        self._recarregar()

    def _recarregar(self):
        self._preencher_seletor_clientes()
        self._mostrar_conexao_ativa()
        self.ciclos.carregar()
        self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        self.execucao.definir_ciclo(self.ciclos.ciclo_atual())
        self.melhorias.carregar()
        self.relatorios.carregar_ciclos()
        self.chamados.carregar()
        self.kb.carregar()

    def _preencher_seletor_clientes(self):
        self.cb_cliente.blockSignals(True)
        self.cb_cliente.clear()
        for c in self._clientes_permitidos():
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
        if Database.conexao_sessao_ativa() != SESSAO_MEMORIA:
            Database.limpar_conexao_sessao()
        Database.definir_cliente_ativo(cliente_id)
        Database.init_db()
        self._mostrar_conexao_ativa()
        self._recarregar()
        self.statusBar().showMessage(
            f"Cliente ativo: {self.cb_cliente.currentText()}", 3000)

    def _trocar_tema(self, tema):
        app = QCoreApplication.instance()
        ThemeManager.aplicar(app, tema)
        self.statusBar().showMessage(f"Tema alterado para: {tema}", 3000)

    def _on_aba(self, index):
        if index == 0:
            self.ciclos.carregar()
        elif index == 1:
            self.casos.definir_ciclo(self.ciclos.ciclo_atual())
        elif index == 2:
            self.execucao.definir_ciclo(self.ciclos.ciclo_atual())
        elif index == 3:
            self.melhorias.carregar()
        elif index == 4:
            self.relatorios.carregar_ciclos()
        elif index == 5:
            self.chamados.carregar()
        elif index == 6:
            self.kb.carregar()
