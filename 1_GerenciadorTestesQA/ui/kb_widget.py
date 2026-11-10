"""Aba Base de Conhecimento — busca, leitura e cadastro de artigos."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QGridLayout, QApplication, QTextBrowser, QSplitter,
)
from PySide6.QtCore import Qt

from database.models_kb import KbRepositorio
from .artigo_kb_dialog import ArtigoKbDialog


class KbWidget(QWidget):
    """Aba de Base de Conhecimento."""

    def __init__(self, usuario_logado=None):
        super().__init__()
        self.usuario_logado = usuario_logado or {}
        self.artigo_atual = None
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # KPIs
        self.grid_kpi = QGridLayout()
        self.lbl_kpis = {}
        for i, (chave, rotulo) in enumerate([
            ("total", "Total"), ("publicados", "Publicados"),
            ("rascunhos", "Rascunhos"), ("visualizacoes", "Visualizações"),
            ("util_sim", "Útil"), ("util_nao", "Não útil"),
        ]):
            self.grid_kpi.addWidget(QLabel(f"<b>{rotulo}</b>"), 0, i)
            lbl = QLabel("0")
            lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
            self.lbl_kpis[chave] = lbl
            self.grid_kpi.addWidget(lbl, 1, i)
        layout.addLayout(self.grid_kpi)

        # Filtros
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Buscar:"))
        self.ed_busca = QLineEdit()
        self.ed_busca.setPlaceholderText(
            "Título, sintoma, solução, tags ou código (KB-0001)")
        self.ed_busca.textChanged.connect(self.carregar)
        topo.addWidget(self.ed_busca, 2)

        topo.addWidget(QLabel("Código de erro:"))
        self.ed_codigo_erro = QLineEdit()
        self.ed_codigo_erro.setPlaceholderText("SX6, SX7...")
        self.ed_codigo_erro.setMaximumWidth(140)
        self.ed_codigo_erro.textChanged.connect(self.carregar)
        topo.addWidget(self.ed_codigo_erro)

        topo.addWidget(QLabel("Módulo:"))
        self.ed_modulo = QLineEdit()
        self.ed_modulo.setMaximumWidth(140)
        self.ed_modulo.textChanged.connect(self.carregar)
        topo.addWidget(self.ed_modulo)
        layout.addLayout(topo)

        # Splitter: tabela | leitor
        splitter = QSplitter(Qt.Horizontal)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["Código", "Título", "Cód. erro", "Módulo", "Vis.", "Útil"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 85)
        self.tabela.setColumnWidth(2, 90)
        self.tabela.setColumnWidth(3, 110)
        self.tabela.setColumnWidth(4, 55)
        self.tabela.setColumnWidth(5, 55)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.itemSelectionChanged.connect(self._mostrar_artigo)
        self.tabela.cellDoubleClicked.connect(self.editar)
        splitter.addWidget(self.tabela)

        self.leitor = QTextBrowser()
        self.leitor.setOpenExternalLinks(False)
        splitter.addWidget(self.leitor)
        splitter.setSizes([520, 420])
        layout.addWidget(splitter, 1)

        # Botões
        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Artigo")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_util_sim = QPushButton("👍 Útil")
        btn_util_nao = QPushButton("👎 Não útil")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        btn_util_sim.clicked.connect(lambda: self._votar(True))
        btn_util_nao.clicked.connect(lambda: self._votar(False))
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        botoes.addWidget(btn_util_sim)
        botoes.addWidget(btn_util_nao)
        layout.addLayout(botoes)

    def _atualizar_kpis(self):
        try:
            k = KbRepositorio.kpis()
        except Exception:
            k = {}
        for chave, lbl in self.lbl_kpis.items():
            lbl.setText(str(k.get(chave, 0)))

    def carregar(self):
        try:
            self.tabela.setUpdatesEnabled(False)
            self._atualizar_kpis()
            artigos = KbRepositorio.buscar(
                termo=self.ed_busca.text().strip() or None,
                codigo_erro=self.ed_codigo_erro.text().strip() or None,
                modulo=self.ed_modulo.text().strip() or None,
                limite=200)
            self.tabela.setRowCount(len(artigos))
            for i, a in enumerate(artigos):
                id_item = QTableWidgetItem(a["codigo"])
                id_item.setData(Qt.UserRole, a["id"])
                self.tabela.setItem(i, 0, id_item)
                self.tabela.setItem(i, 1, QTableWidgetItem(a["titulo"]))
                self.tabela.setItem(i, 2, QTableWidgetItem(
                    a.get("codigo_erro") or ""))
                self.tabela.setItem(
                    i, 3, QTableWidgetItem(a.get("modulo") or ""))
                self.tabela.setItem(i, 4, QTableWidgetItem(
                    str(a.get("visualizacoes") or 0)))
                self.tabela.setItem(i, 5, QTableWidgetItem(
                    f"+{a.get('util_sim') or 0}/-{a.get('util_nao') or 0}"))
            if not artigos:
                self.leitor.setHtml(
                    "<p style='color:#666'>Nenhum artigo encontrado. "
                    "Cadastre o primeiro no botão <b>Novo Artigo</b>.</p>")
                self.artigo_atual = None
        except Exception as e:
            QMessageBox.critical(self, "Erro ao carregar KB",
                                 f"Não foi possível carregar a KB:\n{e}")
            return
        finally:
            self.tabela.setUpdatesEnabled(True)
            self.tabela.viewport().update()
            QApplication.processEvents()

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _mostrar_artigo(self):
        artigo_id = self._selecionado()
        if not artigo_id:
            return
        self.artigo_atual = KbRepositorio.obter(
            artigo_id, incrementar_visualizacao=True)
        if not self.artigo_atual:
            return
        a = self.artigo_atual
        html = f"""
        <h2 style='color:#1565C0'>{a.get('codigo')} — {a.get('titulo')}</h2>
        <p style='color:#666;font-size:11px'>
          Módulo: <b>{a.get('modulo') or '—'}</b> ·
          Código de erro: <b>{a.get('codigo_erro') or '—'}</b> ·
          Autor: {a.get('autor') or '—'} ·
          Vis.: {a.get('visualizacoes') or 0}
        </p>
        <h3>Sintoma</h3>
        <div style='white-space:pre-wrap'>{a.get('sintoma') or ''}</div>
        <h3>Causa raiz</h3>
        <div style='white-space:pre-wrap'>{a.get('causa_raiz') or '—'}</div>
        <h3>Solução</h3>
        <div style='white-space:pre-wrap'>{a.get('solucao') or ''}</div>
        <p style='color:#999;font-size:11px;margin-top:16px'>
          Tags: {a.get('tags') or '—'} · Atualizado: {a.get('atualizado_em') or '—'}
        </p>
        """
        self.leitor.setHtml(html)
        self._atualizar_kpis()

    def novo(self):
        dlg = ArtigoKbDialog(self, usuario_logado=self.usuario_logado)
        if not dlg.exec():
            return
        try:
            novo_id, codigo = KbRepositorio.inserir(
                dlg.dados(), autor_login=self.usuario_logado.get("login"))
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar artigo",
                                 f"Não foi possível gravar:\n{e}")
            return
        self.carregar()
        self._selecionar_por_id(novo_id)

    def editar(self):
        artigo_id = self._selecionado()
        if not artigo_id:
            QMessageBox.information(self, "Aviso", "Selecione um artigo.")
            return
        artigo = KbRepositorio.obter(artigo_id)
        if not artigo:
            QMessageBox.warning(self, "Aviso", "Artigo não encontrado.")
            self.carregar()
            return
        dlg = ArtigoKbDialog(self, artigo=artigo,
                             usuario_logado=self.usuario_logado)
        if not dlg.exec():
            return
        try:
            KbRepositorio.atualizar(artigo_id, dlg.dados())
        except Exception as e:
            QMessageBox.critical(self, "Erro ao atualizar",
                                 f"Não foi possível atualizar:\n{e}")
            return
        self.carregar()
        self._selecionar_por_id(artigo_id)

    def excluir(self):
        artigo_id = self._selecionado()
        if not artigo_id:
            QMessageBox.information(self, "Aviso", "Selecione um artigo.")
            return
        if QMessageBox.question(
                self, "Confirmar", "Excluir este artigo?") != QMessageBox.Yes:
            return
        try:
            KbRepositorio.excluir(artigo_id)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao excluir",
                                 f"Não foi possível excluir:\n{e}")
            return
        self.leitor.clear()
        self.artigo_atual = None
        self.carregar()

    def _votar(self, util):
        if not self.artigo_atual:
            QMessageBox.information(self, "Aviso", "Selecione um artigo.")
            return
        KbRepositorio.registrar_utilidade(self.artigo_atual["id"], util)
        self.carregar()
        self._selecionar_por_id(self.artigo_atual["id"])

    def _selecionar_por_id(self, artigo_id):
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, 0)
            if item and item.data(Qt.UserRole) == artigo_id:
                self.tabela.setCurrentCell(linha, 0)
                self._mostrar_artigo()
                return
