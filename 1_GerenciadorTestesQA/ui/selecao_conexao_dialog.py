"""Diálogo de Seleção de Conexão — exibido após o login (mobilidade).

Lista SOMENTE as conexões dos clientes que o usuário pode acessar
(usuario_clientes; admin vê todas). Cada conexão é TESTADA na hora com
timeout curto e recebe selo 🟢 (acessível) / 🔴 (inacessível) — o usuário
escolhe consciente antes de o app abrir.

A escolha vira a CONEXÃO DA SESSÃO (override temporário): não altera a
conexão padrão do cliente. Opção extra: 'Banco temporário da sessão'
(fallback em memória — útil quando nenhuma rede está disponível).
"""
import os
import traceback
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QRadioButton, QButtonGroup,
    QProgressBar, QApplication,
)
from PySide6.QtCore import Qt, QThread, Signal
from database.acessos import ConexaoAcessoRepositorio
from database.connection import Database
from utils.seguranca import obter_senha


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


class _TestadorConexoes(QThread):
    """Testa as conexões em background (a UI não congela durante o teste)."""
    resultado = Signal(int, bool, str)  # (linha, ok, mensagem)
    concluido = Signal()

    def __init__(self, conexoes, parent=None):
        super().__init__(parent)
        self._conexoes = conexoes
        self._cancelado = False

    def cancelar(self):
        self._cancelado = True

    def run(self):
        for i, cx in enumerate(self._conexoes):
            if self._cancelado:
                return
            try:
                cfg = dict(cx)
                senha = obter_senha(cx["id"], cx.get("senha"))
                ok, msg = Database.testar_conexao(cfg, senha=senha, timeout=5)
            except Exception as e:
                ok, msg = False, str(e)
            self.resultado.emit(i, ok, msg)
        self.concluido.emit()


class SelecaoConexaoDialog(QDialog):
    """Seleção de conexão pós-login, com teste de conectividade 🟢/🔴."""

    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.usuario = usuario or {}
        self.conexao_escolhida = None   # dict da conexão escolhida
        self.usar_temporario = False    # True = banco em memória da sessão
        self.setWindowTitle("Selecionar Conexão de Dados")
        self.setMinimumWidth(620)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Olá, <b>{self.usuario.get('nome') or self.usuario.get('login') or '?'}</b> — "
            "escolha a conexão de dados para esta sessão.\n"
            "🟢 = acessível agora  |  🔴 = inacessível (rede/permissão)"))

        self.lista = QListWidget()
        self.lista.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.lista, 1)

        # Opção de fallback: banco temporário da sessão (offline)
        self.rb_temporario = QRadioButton(
            "Usar banco temporário da sessão (dados não ficam salvos)")
        self.grupo = QButtonGroup(self)
        self.grupo.addButton(self.rb_temporario)
        layout.addWidget(self.rb_temporario)

        self.progresso = QProgressBar()
        self.progresso.setRange(0, 0)  # indeterminado durante o teste
        self.progresso.hide()
        layout.addWidget(self.progresso)

        self.lbl_status = QLabel("Testando conexões...")
        self.lbl_status.setStyleSheet("color:#555;")
        layout.addWidget(self.lbl_status)

        botoes = QHBoxLayout()
        btn_atualizar = QPushButton("Testar Novamente")
        btn_ok = QPushButton("Conectar")
        btn_ok.setDefault(True)
        btn_cancelar = QPushButton("Cancelar")
        btn_atualizar.clicked.connect(self._testar_todos)
        btn_ok.clicked.connect(self._conectar)
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_atualizar)
        botoes.addStretch()
        botoes.addWidget(btn_ok)
        botoes.addWidget(btn_cancelar)
        layout.addLayout(botoes)

        self._testador = None
        self._resultados = {}  # linha -> (ok, msg)
        self._carregar()

    # ---------- Carregamento e teste ----------
    def _carregar(self):
        try:
            self._conexoes = ConexaoAcessoRepositorio.listar_conexoes_permitidas(
                self.usuario)
        except Exception:
            _log_erro()
            self._conexoes = []
        self.lista.clear()
        self._resultados = {}
        if not self._conexoes:
            self.lbl_status.setText(
                "Nenhuma conexão cadastrada para os seus clientes.\n"
                "Peça ao administrador para cadastrar em "
                "Configurações → Conexões a Bancos...")
            self.rb_temporario.setChecked(True)
            return
        _TIPO_ROTULO = {"sqlite": "SQLite local", "sqlserver": "SQL Server",
                        "mysql": "MySQL"}
        for cx in self._conexoes:
            cliente = cx.get("cliente_nome") or "—"
            tipo = _TIPO_ROTULO.get(cx.get("tipo"), cx.get("tipo") or "?")
            destino = cx.get("banco") or ""
            if cx.get("tipo") == "sqlserver" and cx.get("host"):
                destino = f"{cx['host']} · {destino}"
            item = QListWidgetItem(
                f"⏳  {cliente} → {cx['nome']}  [{tipo}]  {destino}")
            item.setData(Qt.UserRole, cx)
            self.lista.addItem(item)
        self._testar_todos()

    def _testar_todos(self):
        if self._testador and self._testador.isRunning():
            return
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            item.setText(item.text().replace("🟢", "⏳").replace("🔴", "⏳")
                         if "⏳" not in item.text() else item.text())
            if not item.text().startswith("⏳"):
                item.setText(f"⏳ {item.text()}")
        self.progresso.show()
        self.lbl_status.setText("Testando conexões (timeout 5s cada)...")
        self._testador = _TestadorConexoes(self._conexoes, self)
        self._testador.resultado.connect(self._resultado_teste)
        self._testador.concluido.connect(self._teste_concluido)
        self._testador.start()

    def _resultado_teste(self, linha, ok, msg):
        if linha >= self.lista.count():
            return
        item = self.lista.item(linha)
        texto = item.text()
        # remove o marcador inicial (⏳/🟢/🔴) e reinsere o novo
        for marcador in ("⏳ ", "🟢 ", "🔴 "):
            if texto.startswith(marcador):
                texto = texto[len(marcador):]
                break
        item.setText(("🟢 " if ok else "🔴 ") + texto)
        item.setToolTip(msg if not ok else "Conexão OK")
        self._resultados[linha] = (ok, msg)

    def _teste_concluido(self):
        self.progresso.hide()
        acessiveis = sum(1 for ok, _ in self._resultados.values() if ok)
        self.lbl_status.setText(
            f"{acessiveis} de {len(self._conexoes)} conexão(ões) acessível(is). "
            "Selecione uma conexão 🟢 e clique em Conectar.")

    # ---------- Escolha ----------
    def _conectar(self):
        if self.rb_temporario.isChecked():
            self.usar_temporario = True
            self.conexao_escolhida = None
            self.accept()
            return
        linha = self.lista.currentRow()
        if linha < 0:
            QMessageBox.information(
                self, "Aviso",
                "Selecione uma conexão na lista (ou marque a opção temporária).")
            return
        ok, msg = self._resultados.get(linha, (None, ""))
        if ok is False:
            resposta = QMessageBox.question(
                self, "Conexão inacessível",
                f"Esta conexão está 🔴 inacessível agora:\n{msg}\n\n"
                "Deseja conectar mesmo assim? "
                "(as telas podem falhar até a rede voltar)")
            if resposta != QMessageBox.Yes:
                return
        self.conexao_escolhida = self.lista.item(linha).data(Qt.UserRole)
        self.usar_temporario = False
        self.accept()

    def closeEvent(self, event):
        if self._testador and self._testador.isRunning():
            self._testador.cancelar()
            self._testador.wait(2000)
        super().closeEvent(event)