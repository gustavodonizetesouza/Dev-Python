"""Cadastro e edição de chamados (tela modal)."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox, QMessageBox,
)
from database.models import (
    CicloRepositorio, UsuarioRepositorio, ModuloRepositorio,
)
from database.models_chamados import ChamadoRepositorio


class ChamadoDialog(QDialog):
    """Cria ou edita um chamado. Edição = melhoria 1."""

    def __init__(self, parent=None, chamado=None, usuario_logado=None):
        super().__init__(parent)
        self.chamado = chamado
        self.usuario_logado = usuario_logado or {}
        self.setWindowTitle("Editar Chamado" if chamado else "Novo Chamado")
        self.setMinimumWidth(580)
        self.setModal(True)

        form = QFormLayout()

        self.ed_titulo = QLineEdit()
        self.ed_titulo.setPlaceholderText("Resumo do problema (1 linha)")
        self.ed_titulo.setMaxLength(255)

        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(100)
        self.ed_descricao.setPlaceholderText(
            "Descrição detalhada: passos para reproduzir, ambiente, "
            "evidências, mensagem de erro do Protheus...")

        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(ChamadoRepositorio.TIPO_OPCOES)

        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(ChamadoRepositorio.SEVERIDADE_OPCOES)
        self.cb_prioridade.setCurrentText("Media")

        self.cb_severidade = QComboBox()
        self.cb_severidade.addItems([""] + ChamadoRepositorio.SEVERIDADE_OPCOES)

        self.cb_origem = QComboBox()
        self.cb_origem.addItems(ChamadoRepositorio.ORIGEM_OPCOES)
        self.cb_origem.setCurrentText("Manual")
        self.cb_origem.setEnabled(False)

        self.cb_ambiente = QComboBox()
        self.cb_ambiente.addItems([""] + ChamadoRepositorio.AMBIENTE_OPCOES)

        self.cb_modulo = QComboBox()
        self.cb_modulo.setEditable(True)
        self.cb_modulo.addItem("")
        try:
            for m in ModuloRepositorio.listar():
                self.cb_modulo.addItem(m["nome"])
        except Exception:
            pass

        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        try:
            for u in UsuarioRepositorio.listar():
                self.cb_responsavel.addItem(u["nome"])
        except Exception:
            pass

        # Melhoria 2 — solicitante NÃO pré-carrega mais o nome do usuário logado.
        # Em edição carrega o valor salvo; em novo chamado fica vazio.
        self.ed_solicitante = QLineEdit()
        self.ed_solicitante.setPlaceholderText("Nome do solicitante")

        self.cb_ciclo = QComboBox()
        self.cb_ciclo.addItem("(sem ciclo)", None)
        try:
            for c in CicloRepositorio.listar():
                self.cb_ciclo.addItem(
                    f"{c['nome']} ({c.get('tipo') or ''})", c["id"])
        except Exception:
            pass

        form.addRow("Título:", self.ed_titulo)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Severidade:", self.cb_severidade)
        form.addRow("Origem:", self.cb_origem)
        form.addRow("Ambiente:", self.cb_ambiente)
        form.addRow("Módulo:", self.cb_modulo)
        form.addRow("Responsável:", self.cb_responsavel)
        form.addRow("Solicitante:", self.ed_solicitante)
        form.addRow("Ciclo (opcional):", self.cb_ciclo)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if chamado:
            self._preencher(chamado)

    def _preencher(self, chamado):
        self.ed_titulo.setText(chamado.get("titulo") or "")
        self.ed_descricao.setPlainText(chamado.get("descricao") or "")

        idx = self.cb_tipo.findText(chamado.get("tipo") or "Suporte")
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)

        idx = self.cb_prioridade.findText(chamado.get("prioridade") or "Media")
        if idx >= 0:
            self.cb_prioridade.setCurrentIndex(idx)

        idx = self.cb_severidade.findText(chamado.get("severidade") or "")
        if idx >= 0:
            self.cb_severidade.setCurrentIndex(idx)

        idx = self.cb_origem.findText(chamado.get("origem") or "Manual")
        if idx >= 0:
            self.cb_origem.setCurrentIndex(idx)

        idx = self.cb_ambiente.findText(chamado.get("ambiente") or "")
        if idx >= 0:
            self.cb_ambiente.setCurrentIndex(idx)

        self.cb_modulo.setCurrentText(chamado.get("modulo") or "")

        idx = self.cb_responsavel.findText(chamado.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)

        self.ed_solicitante.setText(chamado.get("solicitante") or "")

        if chamado.get("ciclo_id"):
            idx = self.cb_ciclo.findData(chamado["ciclo_id"])
            if idx >= 0:
                self.cb_ciclo.setCurrentIndex(idx)

    def _validar(self):
        if not self.ed_titulo.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o título do chamado.")
            return
        if not self.ed_descricao.toPlainText().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe a descrição detalhada do problema.")
            return
        self.accept()

    def dados(self):
        return {
            "titulo": self.ed_titulo.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "tipo": self.cb_tipo.currentText(),
            "prioridade": self.cb_prioridade.currentText(),
            "severidade": self.cb_severidade.currentText() or None,
            "origem": self.cb_origem.currentText() or "Manual",
            "ambiente": self.cb_ambiente.currentText() or None,
            "modulo": (self.cb_modulo.currentText() or "").strip() or None,
            "responsavel": (self.cb_responsavel.currentText() or "").strip() or None,
            "solicitante": self.ed_solicitante.text().strip() or None,
            "ciclo_id": self.cb_ciclo.currentData(),
            "status": (self.chamado or {}).get("status", "Aberto"),
        }