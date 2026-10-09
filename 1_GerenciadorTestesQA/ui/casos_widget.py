"""Widget de Casos de Teste — mostra os casos do ciclo selecionado na aba Ciclos.

CORREÇÃO: QTextEdit não tem .text() — usa .toPlainText(). A validação anterior
quebrava com AttributeError e o diálogo nunca aceitava, por isso o caso
"não salvava". Também grava qualquer erro em erros.log para diagnóstico fácil.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QDoubleSpinBox,
)
from PySide6.QtCore import Qt
from database.models import CasoRepositorio, CicloRepositorio, ModuloRepositorio, UsuarioRepositorio
from utils.helpers import TIPOS_OPCOES, PRIORIDADES_OPCOES
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog


def _log_erro():
    """Grava o traceback completo no arquivo erros.log (na raiz do projeto)
    e também no console. Assim, qualquer erro fica fácil de me enviar."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


class CasoDialog(QDialog):
    def __init__(self, parent=None, caso=None):
        super().__init__(parent)
        self.caso = caso
        self.setWindowTitle("Novo Caso" if not caso else "Editar Caso")
        self.setMinimumWidth(540)

        form = QFormLayout()
        self.ed_codigo = QLineEdit()
        self.ed_codigo.setPlaceholderText("Deixe vazio para gerar automático")
        self.ed_tarefa = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(90)

        # Módulo com botão "+" para cadastrar módulo na hora (recarrega e seleciona o novo)
        self.cb_modulo = QComboBox()
        self.cb_modulo.setEditable(True)
        self.cb_modulo.addItems([m["nome"]
                                for m in ModuloRepositorio.listar()])
        linha_modulo = QHBoxLayout()
        linha_modulo.addWidget(self.cb_modulo, 1)
        btn_mod = QPushButton("+")
        btn_mod.setToolTip("Cadastrar módulo")
        btn_mod.setMaximumWidth(32)
        btn_mod.clicked.connect(self._gerenciar_modulos)
        linha_modulo.addWidget(btn_mod)

        self.ed_rotina = QLineEdit()
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(TIPOS_OPCOES)
        self.cb_prioridade = QComboBox()
        self.cb_prioridade.addItems(PRIORIDADES_OPCOES)

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

        self.ed_requisito = QLineEdit()
        self.sp_horas = QDoubleSpinBox()
        self.sp_horas.setRange(0, 99999)
        self.sp_horas.setDecimals(2)

        form.addRow("Código:", self.ed_codigo)
        form.addRow("Tarefa/Objetivo:", self.ed_tarefa)
        form.addRow("Descrição:", self.ed_descricao)
        form.addRow("Módulo:", linha_modulo)
        form.addRow("Rotina:", self.ed_rotina)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Responsável:", linha_resp)
        form.addRow("Requisito/Compliance:", self.ed_requisito)
        form.addRow("Horas estimadas:", self.sp_horas)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

        if caso:
            self._preencher(caso)

    def _gerenciar_modulos(self):
        dlg = ModulosDialog(self)
        dlg.exec()
        try:
            modulos = ModuloRepositorio.listar()
        except Exception:
            _log_erro()
            QMessageBox.warning(
                self, "Aviso", "Não foi possível atualizar os módulos. Veja erros.log")
            return
        atual = self.cb_modulo.currentText()
        self.cb_modulo.clear()
        self.cb_modulo.addItems([m["nome"] for m in modulos])
        # Se cadastrou um módulo novo, seleciona ele direto
        if getattr(dlg, "ultimo_novo", None):
            idx = self.cb_modulo.findText(dlg.ultimo_novo)
            if idx >= 0:
                self.cb_modulo.setCurrentIndex(idx)
                return
        idx = self.cb_modulo.findText(atual)
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        else:
            self.cb_modulo.setEditText(atual)

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

    def _preencher(self, caso):
        self.ed_codigo.setText(caso.get("codigo") or "")
        self.ed_tarefa.setText(caso.get("tarefa") or "")
        self.ed_descricao.setPlainText(caso.get("descricao") or "")
        idx = self.cb_modulo.findText(caso.get("modulo") or "")
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        else:
            self.cb_modulo.setEditText(caso.get("modulo") or "")
        self.ed_rotina.setText(caso.get("rotina") or "")
        idx = self.cb_tipo.findText(caso.get("tipo") or "Funcional")
        if idx >= 0:
            self.cb_tipo.setCurrentIndex(idx)
        idx = self.cb_prioridade.findText(caso.get("prioridade") or "Media")
        if idx >= 0:
            self.cb_prioridade.setCurrentIndex(idx)
        idx = self.cb_responsavel.findText(caso.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_requisito.setText(caso.get("requisito_compliance") or "")
        self.sp_horas.setValue(float(caso.get("horas_estimadas") or 0))

    def _validar(self):
        """VALIDAÇÃO CORRIGIDA: QTextEdit usa toPlainText(), não .text()."""
        try:
            descricao = (self.ed_descricao.toPlainText() or "").strip()
            modulo = (self.cb_modulo.currentText() or "").strip()

            if not descricao:
                QMessageBox.warning(self, "Validação",
                                    "Informe a descrição do caso.")
                return
            if not modulo:
                QMessageBox.warning(self, "Validação",
                                    "Informe o módulo do caso.")
                return
            self.accept()
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro",
                                 "Erro ao validar o caso. Detalhes em erros.log")

    def dados(self):
        return {
            "codigo": self.ed_codigo.text().strip(),
            "tarefa": self.ed_tarefa.text().strip(),
            "descricao": self.ed_descricao.toPlainText().strip(),
            "modulo": self.cb_modulo.currentText().strip().upper(),
            "rotina": self.ed_rotina.text().strip(),
            "tipo": self.cb_tipo.currentText(),
            "prioridade": self.cb_prioridade.currentText(),
            "responsavel": self.cb_responsavel.currentText(),
            "requisito_compliance": self.ed_requisito.text().strip(),
            "horas_estimadas": self.sp_horas.value(),
        }


class CasosWidget(QWidget):
    """Aba 2 — casos do ciclo selecionado na aba 1."""

    def __init__(self):
        super().__init__()
        self.ciclo_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.lbl_ciclo = QLabel(
            "Selecione um ciclo na aba 'Ciclos' para ver os casos.")
        layout.addWidget(self.lbl_ciclo)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Módulo:"))
        self.cb_filtro_modulo = QComboBox()
        self.cb_filtro_modulo.addItem("Todos")
        self.cb_filtro_modulo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro_modulo)
        topo.addWidget(QLabel("Tipo:"))
        self.cb_filtro_tipo = QComboBox()
        self.cb_filtro_tipo.addItem("Todos")
        self.cb_filtro_tipo.addItems(TIPOS_OPCOES)
        self.cb_filtro_tipo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_filtro_tipo)
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Tarefa", "Módulo", "Tipo", "Prioridade", "Responsável", "Status Exec."])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 110)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 90)
        self.tabela.setColumnWidth(5, 80)
        self.tabela.setColumnWidth(6, 110)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Caso")
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_excluir.clicked.connect(self.excluir)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)

    def definir_ciclo(self, ciclo_id):
        self.ciclo_id = ciclo_id
        if ciclo_id:
            try:
                ciclo = CicloRepositorio.obter(ciclo_id)
            except Exception:
                ciclo = None
            nome = ciclo["nome"] if ciclo else "?"
            self.lbl_ciclo.setText(f"Ciclo: {nome} — casos abaixo.")
            try:
                modulos = sorted({c["modulo"]
                                 for c in CasoRepositorio.listar(ciclo_id)})
            except Exception:
                modulos = []
            self.cb_filtro_modulo.blockSignals(True)
            self.cb_filtro_modulo.clear()
            self.cb_filtro_modulo.addItem("Todos")
            self.cb_filtro_modulo.addItems(modulos)
            self.cb_filtro_modulo.blockSignals(False)
        else:
            self.lbl_ciclo.setText(
                "Selecione um ciclo na aba 'Ciclos' para ver os casos.")
            self.tabela.setRowCount(0)
        self.carregar()

    def carregar(self):
        if not self.ciclo_id:
            self.tabela.setRowCount(0)
            return
        try:
            casos = CasoRepositorio.listar(self.ciclo_id)
        except Exception:
            _log_erro()
            QMessageBox.critical(
                self, "Erro", "Não foi possível carregar os casos. Veja erros.log")
            return

        filtro_modulo = self.cb_filtro_modulo.currentText()
        filtro_tipo = self.cb_filtro_tipo.currentText()
        if filtro_modulo != "Todos":
            casos = [c for c in casos if c["modulo"] == filtro_modulo]
        if filtro_tipo != "Todos":
            casos = [c for c in casos if c["tipo"] == filtro_tipo]

        self.tabela.setRowCount(len(casos))
        for i, c in enumerate(casos):
            id_item = QTableWidgetItem(str(c["id"]))
            id_item.setData(Qt.UserRole, c["id"])
            self.tabela.setItem(i, 0, id_item)
            self.tabela.setItem(i, 1, QTableWidgetItem(c.get("codigo") or ""))
            self.tabela.setItem(i, 2, QTableWidgetItem(c.get("tarefa") or ""))
            self.tabela.setItem(i, 3, QTableWidgetItem(c.get("modulo") or ""))
            self.tabela.setItem(i, 4, QTableWidgetItem(c.get("tipo") or ""))
            self.tabela.setItem(i, 5, QTableWidgetItem(
                c.get("prioridade") or ""))
            self.tabela.setItem(i, 6, QTableWidgetItem(
                c.get("responsavel") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(
                c.get("status_exec") or ""))

    def _selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def _abrir_edicao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        if not self.ciclo_id:
            QMessageBox.information(
                self, "Aviso", "Selecione um ciclo na aba 'Ciclos' primeiro.")
            return
        dlg = CasoDialog(self)
        if dlg.exec():
            try:
                resultado = CasoRepositorio.inserir(self.ciclo_id, dlg.dados())
                codigo = resultado[1] if isinstance(resultado, tuple) else ""
                self.definir_ciclo(self.ciclo_id)  # SEMPRE recarrega a lista
                QMessageBox.information(
                    self, "Sucesso",
                    f"Caso salvo com sucesso ({codigo or 'código automático'}).")
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Não foi possível salvar o caso. Veja erros.log")

    def editar(self):
        caso_id = self._selecionado()
        if not caso_id:
            QMessageBox.information(self, "Aviso", "Selecione um caso.")
            return
        caso = CasoRepositorio.obter(caso_id)
        dlg = CasoDialog(self, caso)
        if dlg.exec():
            try:
                CasoRepositorio.atualizar(caso_id, dlg.dados())
                self.carregar()
                QMessageBox.information(self, "Sucesso", "Caso atualizado.")
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Não foi possível atualizar o caso. Veja erros.log")

    def excluir(self):
        caso_id = self._selecionado()
        if not caso_id:
            QMessageBox.information(self, "Aviso", "Selecione um caso.")
            return
        if QMessageBox.question(self, "Confirmar",
                                "Excluir este caso do ciclo?") == QMessageBox.Yes:
            try:
                CasoRepositorio.excluir(caso_id)
                self.definir_ciclo(self.ciclo_id)
            except Exception:
                _log_erro()
                QMessageBox.critical(
                    self, "Erro", "Não foi possível excluir. Veja erros.log")
