"""Cadastro e edição de artigos da Base de Conhecimento."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox, QMessageBox, QCheckBox,
)


class ArtigoKbDialog(QDialog):
    """Cria ou edita um artigo de KB."""

    def __init__(self, parent=None, artigo=None, chamado_origem=None,
                 usuario_logado=None):
        super().__init__(parent)
        self.artigo = artigo
        self.chamado_origem = chamado_origem or {}
        self.usuario_logado = usuario_logado or {}
        self.setWindowTitle("Editar Artigo" if artigo else "Novo Artigo KB")
        self.setMinimumWidth(680)
        self.setModal(True)

        form = QFormLayout()

        self.ed_titulo = QLineEdit()
        self.ed_titulo.setPlaceholderText(
            "Ex.: Erro SX6 ao acessar rotina MATA010")
        self.ed_titulo.setMaxLength(255)

        self.ed_sintoma = QTextEdit()
        self.ed_sintoma.setFixedHeight(70)
        self.ed_sintoma.setPlaceholderText(
            "O que o usuário vê / o que acontece (mensagem de erro completa).")

        self.ed_causa = QTextEdit()
        self.ed_causa.setFixedHeight(60)
        self.ed_causa.setPlaceholderText(
            "Causa raiz identificada (ex.: tabela SX6 sem permissão).")

        self.ed_solucao = QTextEdit()
        self.ed_solucao.setFixedHeight(110)
        self.ed_solucao.setPlaceholderText(
            "Passo a passo da solução (numerado):\n"
            "1) Acesse ...\n"
            "2) Verifique ...\n"
            "3) Reinicie ...")

        self.ed_codigo_erro = QLineEdit()
        self.ed_codigo_erro.setPlaceholderText(
            "Ex.: SX6, SX7, RUN001, LOG0001")
        self.ed_codigo_erro.setMaxLength(50)

        self.ed_modulo = QLineEdit()
        self.ed_modulo.setPlaceholderText("Ex.: Financeiro, Estoque, Fiscal")

        self.ed_tags = QLineEdit()
        self.ed_tags.setPlaceholderText(
            "Separadas por vírgula: protheus, sx6, permissao, mata010")

        self.chk_publicado = QCheckBox("Publicado (visível na busca)")
        self.chk_publicado.setChecked(True)

        form.addRow("Título:", self.ed_titulo)
        form.addRow("Sintoma:", self.ed_sintoma)
        form.addRow("Causa raiz:", self.ed_causa)
        form.addRow("Solução:", self.ed_solucao)
        form.addRow("Código de erro:", self.ed_codigo_erro)
        form.addRow("Módulo:", self.ed_modulo)
        form.addRow("Tags:", self.ed_tags)
        form.addRow("", self.chk_publicado)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if artigo:
            self._preencher(artigo)
        elif chamado_origem:
            self._preencher_do_chamado(chamado_origem)

    def _preencher(self, artigo):
        self.ed_titulo.setText(artigo.get("titulo") or "")
        self.ed_sintoma.setPlainText(artigo.get("sintoma") or "")
        self.ed_causa.setPlainText(artigo.get("causa_raiz") or "")
        self.ed_solucao.setPlainText(artigo.get("solucao") or "")
        self.ed_codigo_erro.setText(artigo.get("codigo_erro") or "")
        self.ed_modulo.setText(artigo.get("modulo") or "")
        self.ed_tags.setText(artigo.get("tags") or "")
        self.chk_publicado.setChecked(bool(artigo.get("publicado", 1)))

    def _preencher_do_chamado(self, chamado):
        """Pré-preenche o artigo a partir do chamado encerrado.

        Título = código + título do chamado; Sintoma = descrição;
        Solução = campo solucao do chamado (quando existir);
        Módulo = módulo do chamado.
        """
        codigo = chamado.get("codigo") or ""
        titulo = chamado.get("titulo") or ""
        self.ed_titulo.setText(f"{codigo} — {titulo}".strip(" —"))
        self.ed_sintoma.setPlainText(chamado.get("descricao") or "")
        self.ed_solucao.setPlainText(chamado.get("solucao") or "")
        self.ed_modulo.setText(chamado.get("modulo") or "")

    def _validar(self):
        if not self.ed_titulo.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o título do artigo.")
            return
        if not self.ed_sintoma.toPlainText().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o sintoma (o que acontece).")
            return
        if not self.ed_solucao.toPlainText().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe a solução (passo a passo).")
            return
        self.accept()

    def dados(self):
        return {
            "titulo": self.ed_titulo.text().strip(),
            "sintoma": self.ed_sintoma.toPlainText().strip(),
            "causa_raiz": self.ed_causa.toPlainText().strip() or None,
            "solucao": self.ed_solucao.toPlainText().strip(),
            "codigo_erro": (self.ed_codigo_erro.text().strip().upper()
                            or None),
            "modulo": self.ed_modulo.text().strip() or None,
            "tags": self.ed_tags.text().strip() or None,
            "publicado": self.chk_publicado.isChecked(),
            "chamado_origem_id": (self.chamado_origem or {}).get("id"),
        }
