"""Widget de controle de melhorias propostas durante os testes."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView,
)
from PySide6.QtCore import Qt
from database.models import (MelhoriaRepositorio, ModuloRepositorio,
                             UsuarioRepositorio, CicloRepositorio)
from utils.helpers import PRIORIDADES_OPCOES
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog


class MelhoriaDialog(QDialog):
    def __init__(self, parent=None, melhoria=None):
        super().__init__(parent)
        self.melhoria = melhoria
        self.setWindowTitle(
            "Nova Melhoria" if not melhoria else "Editar Melhoria")
        self.setMinimumWidth(520)

        form = QFormLayout()
        self.cb_ciclo = QComboBox()
        self.cb_ciclo.addItem("", None)
        for c in CicloRepositorio.listar():
            self.cb_ciclo.addItem(
                f"{c['nome']} ({c.get('tipo') or ''})", c["id"])
        self.ed_titulo = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(80)

        # Módulo com botão "+"
        self.cb_modulo = QComboBox()
        self.cb_modulo.addItem("")
        self.cb_modulo.addItems([m["nome"]
                                for m in ModuloRepositorio.listar()])
        linha_modulo = QHBoxLayout()
        linha_modulo.addWidget(self.cb_modulo, 1)
        btn_mod = QPushButton("+")
        btn_mod.setToolTip("Cadastrar módulo")
        btn_mod.setMaximumWidth(32)
        btn_mod.clicked.connect(self._gerenciar_modulos)
        linha_modulo.addWidget(btn_mod)

        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(PRIORIDADES_OPCOES)
        self.cb_status = QComboBox()
        self.cb_status.addItems(MelhoriaRepositorio.STATUS_OPCOES)

        # Responsável com botão "+"
        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        linha_resp = QHBoxLayout()
        linha_resp.addWidget(self.cb_responsavel, 1)
        btn_resp = QPushButton("+")
        btn_resp.setToolTip("Cadastrar usuário")
        btn_resp.setMaximumWidth(32)
        btn_resp.clicked.connect(self._gerenciar_usuarios)
        linha_resp.addWidget(btn_resp)

        self.ed_obs = QTextEdit()
        self.ed_obs.setFixedHeight(60)

        form.addRow("Ciclo:", self.cb_ciclo)
        form.addRow("Título:", self.ed_titulo)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Módulo:", linha_modulo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Status:", self.cb_status)
        form.addRow("Responsável:", linha_resp)
        form.addRow("Observações:", self.ed_obs)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if melhoria:
            self._preencher(melhoria)

    def _gerenciar_modulos(self):
        dlg = ModulosDialog(self)
        dlg.exec()
        atual = self.cb_modulo.currentText()
        self.cb_modulo.clear()
        self.cb_modulo.addItem("")
        self.cb_modulo.addItems([m["nome"]
                                for m in ModuloRepositorio.listar()])
        idx = self.cb_modulo.findText(atual)
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)

    def _gerenciar_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        atual = self.cb_responsavel.currentText()
        self.cb_responsavel.clear()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"]
                                     for u in UsuarioRepositorio.listar()])
        idx = self.cb_responsavel.findText(atual)
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)

    def _preencher(self, melhoria):
        if melhoria.get("ciclo_id"):
            idx = self.cb_ciclo.findData(melhoria["ciclo_id"])
            if idx >= 0:
                self.cb_ciclo.setCurrentIndex(idx)
        self.ed_titulo.setText(melhoria["titulo"])
        self.ed_descricao.setPlainText(melhoria.get("descricao") or "")
        idx = self.cb_modulo.findText(melhoria.get("modulo") or "")
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        idx = self.cb_prioridade.findText(
            melhoria.get("prioridade") or "Media")
        if idx >= 0:
            self.cb_prioridade.setCurrentIndex(idx)
        idx = self.cb_status.findText(melhoria.get("status") or "Proposta")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(melhoria.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_obs.setPlainText(melhoria.get("observacoes") or "")

    def _validar(self):
        if not self.ed_titulo.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Informe o título da melhoria.")
            return
        self.accept()

    def dados(self):
        return {
            "titulo": self.ed_titulo.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "modulo": self.cb_modulo.currentText(),
            "prioridade": self.cb_prioridade.currentText(),
            "status": self.cb_status.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "ciclo_id": self.cb_ciclo.currentData(),
            "observacoes": self.ed_obs.toPlainText().strip(),
        }


class GerarCasoNoCicloDialog(QDialog):
    """Escolhe o ciclo onde o caso gerado pela melhoria será criado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerar Caso no Ciclo")
        self.setMinimumWidth(460)
        form = QFormLayout()
        self.cb_ciclo = QComboBox()
        for c in CicloRepositorio.listar():
            self.cb_ciclo.addItem(
                f"{c['nome']} ({c.get('tipo') or ''})", c["id"])
        self.ed_novo = QLineEdit()
        self.ed_novo.setPlaceholderText(
            "Ou informe o nome para criar um novo ciclo")
        form.addRow("Ciclo existente:", self.cb_ciclo)
        form.addRow("Criar novo ciclo:", self.ed_novo)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

    def _validar(self):
        if self.cb_ciclo.count() == 0 and not self.ed_novo.text().strip():
            QMessageBox.warning(self, "Validação",
                                "Escolha um ciclo ou informe o nome de um novo ciclo.")
            return
        self.accept()

    def ciclo_alvo(self, titulo_melhoria):
        if self.ed_novo.text().strip():
            novo_id = CicloRepositorio.inserir({
                "nome": self.ed_novo.text().strip(),
                "tipo": "Outro",
                "status": "Planejado",
            })
            return novo_id
        if self.cb_ciclo.currentIndex() >= 0:
            return self.cb_ciclo.currentData()
        return None


class MelhoriasWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Status:"))
        self.cb_filtro = QComboBox()
        self.cb_filtro.addItem("Todos")
        self.cb_filtro.addItems(MelhoriaRepositorio.STATUS_OPCOES)
        self.cb_filtro.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro)
        topo.addWidget(QLabel("Ciclo:"))
        self.cb_filtro_ciclo = QComboBox()
        self.cb_filtro_ciclo.addItem("Todos", None)
        for c in CicloRepositorio.listar():
            self.cb_filtro_ciclo.addItem(
                f"{c['nome']} ({c.get('tipo') or ''})", c["id"])
        self.cb_filtro_ciclo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro_ciclo)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 9)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Título", "Ciclo", "Módulo", "Prioridade", "Status", "Responsável", "Caso Gerado"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 75)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 80)
        self.tabela.setColumnWidth(5, 75)
        self.tabela.setColumnWidth(6, 95)
        self.tabela.setColumnWidth(7, 105)
        self.tabela.setColumnWidth(8, 85)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Nova Melhoria")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_gerar = QPushButton("Gerar Caso no Ciclo")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        btn_gerar.clicked.connect(self.gerar_caso)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addWidget(btn_gerar)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar(self):
        filtro = self.cb_filtro.currentText()
        if filtro == "Todos":
            filtro = None
        filtro_ciclo = self.cb_filtro_ciclo.currentData()
        melhorias = MelhoriaRepositorio.listar(filtro, filtro_ciclo)

        ciclos = {c["id"]: c["nome"] for c in CicloRepositorio.listar()}

        self.tabela.setRowCount(len(melhorias))
        for i, m in enumerate(melhorias):
            id_item = QTableWidgetItem(str(m["id"]))
            id_item.setData(Qt.UserRole, m["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(m["codigo"]))
            self.tabela.setItem(i, 2, QTableWidgetItem(m["titulo"]))
            self.tabela.setItem(i, 3, QTableWidgetItem(
                ciclos.get(m.get("ciclo_id")) or ""))
            self.tabela.setItem(i, 4, QTableWidgetItem(m.get("modulo") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(
                m.get("prioridade") or ""))
            self.tabela.setItem(i, 6, QTableWidgetItem(m.get("status") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(
                m.get("responsavel") or ""))
            self.tabela.setItem(i, 8, QTableWidgetItem(
                m["codigo"] if m.get("caso_teste_id") else ""))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_edicao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        dlg = MelhoriaDialog(self)
        if dlg.exec():
            MelhoriaRepositorio.inserir(dlg.dados())
            self.carregar()

    def editar(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        melhoria = MelhoriaRepositorio.obter(melhoria_id)
        dlg = MelhoriaDialog(self, melhoria)
        if dlg.exec():
            MelhoriaRepositorio.atualizar(melhoria_id, dlg.dados())
            self.carregar()

    def excluir(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        if QMessageBox.question(self, "Confirmar", "Excluir esta melhoria?") == QMessageBox.Yes:
            MelhoriaRepositorio.excluir(melhoria_id)
            self.carregar()

    def gerar_caso(self):
        melhoria_id = self._selecionado()
        if not melhoria_id:
            QMessageBox.information(self, "Aviso", "Selecione uma melhoria.")
            return
        melhoria = MelhoriaRepositorio.obter(melhoria_id)
        if melhoria.get("caso_teste_id"):
            QMessageBox.information(
                self, "Atenção", "Esta melhoria já gerou um caso de teste.")
            return
        if melhoria.get("status") not in ("Aprovada", "Implementada"):
            QMessageBox.warning(
                self, "Atenção",
                "A melhoria precisa estar 'Aprovada' ou 'Implementada'\n"
                "para gerar um caso de teste no ciclo.")
            return
        dlg = GerarCasoNoCicloDialog(self)
        if dlg.exec():
            ciclo_id = dlg.ciclo_alvo(melhoria["titulo"])
            ok, msg, caso_id = MelhoriaRepositorio.gerar_caso_no_ciclo(
                melhoria_id, ciclo_id)
            if ok:
                QMessageBox.information(self, "Sucesso", f"✓ {msg}")
            else:
                QMessageBox.warning(self, "Atenção", msg)
            self.carregar()
