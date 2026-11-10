"""Detalhe do chamado: timeline, subtarefas e ações de ciclo de vida."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QComboBox, QPushButton, QMessageBox, QLabel,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt

from database.models_chamados import (
    ChamadoRepositorio, ChamadoTarefaRepositorio, ChamadoHistoricoRepositorio,
)
from database.models_kb import KbRepositorio
from .artigo_kb_dialog import ArtigoKbDialog


class ChamadoDetalheDialog(QDialog):
    def __init__(self, parent=None, chamado_id=None, usuario_logado=None):
        super().__init__(parent)
        self.chamado_id = chamado_id
        self.usuario_logado = usuario_logado or {}
        self.chamado = ChamadoRepositorio.obter(chamado_id) or {}
        codigo = self.chamado.get("codigo") or "?"
        titulo = self.chamado.get("titulo") or ""
        self.setWindowTitle(f"Chamado {codigo} — {titulo}")
        self.resize(900, 640)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.lbl_cabecalho = QLabel(self._texto_cabecalho())
        self.lbl_cabecalho.setWordWrap(True)
        layout.addWidget(self.lbl_cabecalho)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._aba_timeline(), "Linha do tempo")
        self.tabs.addTab(self._aba_tarefas(), "Subtarefas")
        self.tabs.addTab(self._aba_acoes(), "Ações")
        self.tabs.addTab(self._aba_kb(), "Artigos KB")
        layout.addWidget(self.tabs, 1)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.accept)
        layout.addWidget(btn_fechar, alignment=Qt.AlignRight)

        self.tabs.currentChanged.connect(self._on_aba)
        self._carregar_tudo()

    def _texto_cabecalho(self):
        c = self.chamado
        sla = "⚠ ATRASADO" if c.get("sla_atrasado") else "OK"
        return (
            f"<b>{c.get('codigo')} — {c.get('titulo')}</b><br>"
            f"<small>Status: <b>{c.get('status')}</b> · "
            f"Prioridade: {c.get('prioridade')} · "
            f"Tipo: {c.get('tipo')} · "
            f"Responsável: {c.get('responsavel') or '—'} · "
            f"Solicitante: {c.get('solicitante') or '—'} · "
            f"SLA: {sla}</small>"
        )

    # ---------- Linha do tempo ----------
    def _aba_timeline(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_hist = QTableWidget(0, 4)
        self.tabela_hist.setHorizontalHeaderLabels(
            ["Data", "Evento", "Autor", "Comentário"])
        self.tabela_hist.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch)
        self.tabela_hist.setColumnWidth(0, 140)
        self.tabela_hist.setColumnWidth(1, 100)
        self.tabela_hist.setColumnWidth(2, 120)
        self.tabela_hist.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_hist, 1)

        linha = QHBoxLayout()
        self.ed_comentario = QTextEdit()
        self.ed_comentario.setFixedHeight(60)
        self.ed_comentario.setPlaceholderText("Novo comentário...")
        btn_comentar = QPushButton("Comentar")
        btn_comentar.clicked.connect(self._comentar)
        linha.addWidget(self.ed_comentario, 1)
        linha.addWidget(btn_comentar, alignment=Qt.AlignBottom)
        layout.addLayout(linha)
        return w

    def _carregar_historico(self):
        hist = ChamadoHistoricoRepositorio.listar(self.chamado_id)
        self.tabela_hist.setRowCount(len(hist))
        for i, h in enumerate(hist):
            self.tabela_hist.setItem(
                i, 0, QTableWidgetItem(h.get("criado_em") or ""))
            self.tabela_hist.setItem(
                i, 1, QTableWidgetItem(h.get("tipo_evento") or ""))
            self.tabela_hist.setItem(
                i, 2, QTableWidgetItem(h.get("autor") or ""))
            coment = h.get("comentario") or ""
            if h.get("de_status") and h.get("para_status"):
                coment = f"{h['de_status']} → {h['para_status']} {coment}".strip()
            self.tabela_hist.setItem(i, 3, QTableWidgetItem(coment))
        self.tabela_hist.scrollToBottom()

    def _comentar(self):
        txt = self.ed_comentario.toPlainText().strip()
        if not txt:
            return
        login = self.usuario_logado.get("login")
        # SLA antes do comentário
        ChamadoRepositorio.registrar_primeira_resposta(self.chamado_id, login)
        ChamadoRepositorio.comentar(self.chamado_id, login, txt)
        self.ed_comentario.clear()
        self._carregar_tudo()

    # ---------- Subtarefas ----------
    def _aba_tarefas(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.tabela_tar = QTableWidget(0, 5)
        self.tabela_tar.setHorizontalHeaderLabels(
            ["ID", "Título", "Responsável", "Status", "Concluída em"])
        self.tabela_tar.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.tabela_tar.setColumnWidth(0, 45)
        self.tabela_tar.setColumnWidth(2, 140)
        self.tabela_tar.setColumnWidth(3, 130)
        self.tabela_tar.setColumnWidth(4, 160)
        self.tabela_tar.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_tar.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_tar, 1)

        linha = QHBoxLayout()
        self.ed_nova_tarefa = QLineEdit()
        self.ed_nova_tarefa.setPlaceholderText("Nova subtarefa...")
        btn_add = QPushButton("Adicionar")
        btn_concluir = QPushButton("Concluir")
        btn_excluir = QPushButton("Excluir")
        btn_add.clicked.connect(self._adicionar_tarefa)
        btn_concluir.clicked.connect(self._concluir_tarefa)
        btn_excluir.clicked.connect(self._excluir_tarefa)
        linha.addWidget(self.ed_nova_tarefa, 1)
        linha.addWidget(btn_add)
        linha.addWidget(btn_concluir)
        linha.addWidget(btn_excluir)
        layout.addLayout(linha)
        return w

    def _carregar_tarefas(self):
        tarefas = ChamadoTarefaRepositorio.listar(self.chamado_id)
        self.tabela_tar.setRowCount(len(tarefas))
        for i, t in enumerate(tarefas):
            id_item = QTableWidgetItem(str(t["id"]))
            id_item.setData(Qt.UserRole, t["id"])
            self.tabela_tar.setItem(i, 0, id_item)
            self.tabela_tar.setItem(i, 1, QTableWidgetItem(t["titulo"]))
            self.tabela_tar.setItem(
                i, 2, QTableWidgetItem(t.get("responsavel") or ""))
            self.tabela_tar.setItem(
                i, 3, QTableWidgetItem(t.get("status") or ""))
            self.tabela_tar.setItem(
                i, 4, QTableWidgetItem(t.get("concluida_em") or ""))

    def _tarefa_selecionada(self):
        linha = self.tabela_tar.currentRow()
        if linha < 0:
            return None
        return self.tabela_tar.item(linha, 0).data(Qt.UserRole)

    def _adicionar_tarefa(self):
        txt = self.ed_nova_tarefa.text().strip()
        if not txt:
            return
        ChamadoTarefaRepositorio.inserir(self.chamado_id, {
            "titulo": txt,
            "responsavel": self.chamado.get("responsavel"),
        })
        self.ed_nova_tarefa.clear()
        self._carregar_tudo()

    def _concluir_tarefa(self):
        tid = self._tarefa_selecionada()
        if not tid:
            QMessageBox.information(self, "Aviso", "Selecione uma subtarefa.")
            return
        ChamadoTarefaRepositorio.concluir(tid)
        self._carregar_tudo()

    def _excluir_tarefa(self):
        tid = self._tarefa_selecionada()
        if not tid:
            return
        if QMessageBox.question(
                self, "Confirmar", "Excluir esta subtarefa?") != QMessageBox.Yes:
            return
        ChamadoTarefaRepositorio.excluir(tid)
        self._carregar_tudo()

    # ---------- Ações ----------
    def _aba_acoes(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        g_status = QHBoxLayout()
        g_status.addWidget(QLabel("Mudar status para:"))
        self.cb_novo_status = QComboBox()
        self.cb_novo_status.addItems(ChamadoRepositorio.STATUS_OPCOES)
        self.cb_novo_status.setCurrentText(
            self.chamado.get("status") or "Aberto")
        btn_mudar = QPushButton("Aplicar")
        btn_mudar.clicked.connect(self._mudar_status)
        g_status.addWidget(self.cb_novo_status)
        g_status.addWidget(btn_mudar)
        g_status.addStretch()
        layout.addLayout(g_status)

        layout.addWidget(QLabel("<b>Encerramento com valor agregado:</b>"))
        g_saida = QHBoxLayout()
        btn_melhoria = QPushButton("Encerrar e criar Melhoria")
        btn_kb = QPushButton("Encerrar e publicar em KB")
        btn_melhoria.setToolTip(
            "Cria um registro em Melhorias vinculado a este chamado.")
        btn_kb.setToolTip(
            "Abre o cadastro de artigo da KB já pré-preenchido com "
            "os dados deste chamado.")
        btn_melhoria.clicked.connect(self._encerrar_como_melhoria)
        btn_kb.clicked.connect(self._encerrar_como_kb)
        g_saida.addWidget(btn_melhoria)
        g_saida.addWidget(btn_kb)
        g_saida.addStretch()
        layout.addLayout(g_saida)

        layout.addStretch()
        return w

    def _mudar_status(self):
        novo = self.cb_novo_status.currentText()
        ok, msg = ChamadoRepositorio.mudar_status(
            self.chamado_id, novo, self.usuario_logado.get("login"))
        if ok:
            QMessageBox.information(self, "Sucesso", msg)
            self.chamado = ChamadoRepositorio.obter(self.chamado_id) or {}
            self.lbl_cabecalho.setText(self._texto_cabecalho())
            self._carregar_tudo()
        else:
            QMessageBox.warning(self, "Atenção", msg)

    def _encerrar_como_melhoria(self):
        """Cria uma Melhoria real vinculada ao chamado."""
        from database.models import MelhoriaRepositorio
        resp = QMessageBox.question(
            self, "Criar Melhoria",
            "Encerrar este chamado e criar um registro em Melhorias?\n\n"
            "A melhoria será proposta com o título, descrição e módulo "
            "deste chamado, e ficará vinculada a ele.")
        if resp != QMessageBox.Yes:
            return
        try:
            dados = {
                "titulo": self.chamado.get("titulo") or "Melhoria de chamado",
                "descricao": self.chamado.get("descricao"),
                "modulo": self.chamado.get("modulo"),
                "prioridade": self.chamado.get("prioridade") or "Media",
                "status": "Proposta",
                "responsavel": self.chamado.get("responsavel"),
                "ciclo_id": self.chamado.get("ciclo_id"),
            }
            novo_id, codigo = MelhoriaRepositorio.inserir(
                dados, autor_login=self.usuario_logado.get("login"))
        except Exception as e:
            QMessageBox.critical(self, "Erro",
                                 f"Não foi possível criar a melhoria:\n{e}")
            return
        # Vincula a melhoria ao chamado e encerra
        ChamadoRepositorio.vincular_melhoria(self.chamado_id, novo_id)
        ChamadoHistoricoRepositorio.registrar(
            self.chamado_id, "melhoria", self.usuario_logado.get("login"),
            comentario=f"Melhoria {codigo} criada a partir deste chamado.")
        ok, msg = ChamadoRepositorio.mudar_status(
            self.chamado_id, "Encerrado",
            self.usuario_logado.get("login"),
            comentario=f"Encerrado com criação da melhoria {codigo}.")
        if not ok:
            QMessageBox.warning(
                self, "Atenção",
                f"Melhoria {codigo} criada, mas o chamado não foi encerrado:\n"
                f"{msg}\n\nAltere o status manualmente na aba Ações.")
        else:
            QMessageBox.information(
                self, "Sucesso",
                f"Melhoria {codigo} criada e chamado encerrado.")
        self.chamado = ChamadoRepositorio.obter(self.chamado_id) or {}
        self.lbl_cabecalho.setText(self._texto_cabecalho())
        self._carregar_tudo()

    def _encerrar_como_kb(self):
        """Publica em KB: abre o diálogo de artigo pré-preenchido."""
        dlg = ArtigoKbDialog(self, chamado_origem=self.chamado,
                             usuario_logado=self.usuario_logado)
        if not dlg.exec():
            return
        try:
            novo_id, codigo = KbRepositorio.inserir(
                dlg.dados(), autor_login=self.usuario_logado.get("login"))
        except Exception as e:
            QMessageBox.critical(self, "Erro",
                                 f"Não foi possível publicar o artigo:\n{e}")
            return
        # Vincula e encerra
        KbRepositorio.vincular_chamado(self.chamado_id, novo_id)
        ChamadoRepositorio.vincular_artigo_kb(self.chamado_id, novo_id)
        ChamadoHistoricoRepositorio.registrar(
            self.chamado_id, "kb", self.usuario_logado.get("login"),
            comentario=f"Artigo {codigo} publicado a partir deste chamado.")
        ok, msg = ChamadoRepositorio.mudar_status(
            self.chamado_id, "Encerrado",
            self.usuario_logado.get("login"),
            comentario=f"Encerrado com publicação em KB ({codigo}).")
        if not ok:
            QMessageBox.warning(
                self, "Atenção",
                f"Artigo {codigo} publicado, mas o chamado não foi encerrado:\n"
                f"{msg}\n\nAltere o status manualmente na aba Ações.")
        else:
            QMessageBox.information(
                self, "Sucesso",
                f"Artigo {codigo} publicado na Base de Conhecimento e "
                f"chamado encerrado.")
        self.chamado = ChamadoRepositorio.obter(self.chamado_id) or {}
        self.lbl_cabecalho.setText(self._texto_cabecalho())
        self._carregar_kb()
        self._carregar_tudo()

    # ---------- Artigos KB vinculados ----------
    def _aba_kb(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel(
            "<b>Artigos da Base de Conhecimento vinculados a este chamado</b>"))
        self.tabela_kb = QTableWidget(0, 3)
        self.tabela_kb.setHorizontalHeaderLabels(
            ["Código", "Título", "Criado em"])
        self.tabela_kb.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.tabela_kb.setColumnWidth(0, 90)
        self.tabela_kb.setColumnWidth(2, 160)
        self.tabela_kb.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_kb.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela_kb, 1)
        return w

    def _carregar_kb(self):
        vinculos = KbRepositorio.listar_vinculos(self.chamado_id)
        self.tabela_kb.setRowCount(len(vinculos))
        for i, v in enumerate(vinculos):
            self.tabela_kb.setItem(
                i, 0, QTableWidgetItem(v.get("codigo") or ""))
            self.tabela_kb.setItem(
                i, 1, QTableWidgetItem(v.get("titulo") or ""))
            self.tabela_kb.setItem(
                i, 2, QTableWidgetItem(v.get("criado_em") or ""))

    def _carregar_tudo(self):
        self._carregar_historico()
        self._carregar_tarefas()
        self._carregar_kb()

    def _on_aba(self, index):
        self._carregar_tudo()
