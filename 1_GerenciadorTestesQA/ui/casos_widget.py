"""Widget de Casos de Teste — mostra os casos do ciclo selecionado na aba Ciclos.

MÓDULO COMO LIST BOX: o combo de módulo é NÃO editável (dropdown puro).
ETAPAS DO CASO (teste de processo): botão 'Etapas do Ciclo' no rodapé abre o
diálogo que vincula as rotinas do ciclo como etapas; o formulário de edição
também exibe a grade de etapas com vínculo e status.
Coluna Tarefa em Stretch; coluna Tipo aumentada.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QDoubleSpinBox,
    QInputDialog,
)
from PySide6.QtCore import Qt
from database.models import (
    CasoRepositorio, CicloRepositorio, ModuloRepositorio, UsuarioRepositorio,
    CasoEtapaRepositorio, CicloDetalheRepositorio,
)
from utils.helpers import TIPOS_OPCOES, PRIORIDADES_OPCOES
from .modulos_dialog import ModulosDialog
from .usuarios_dialog import UsuariosDialog
from .caso_etapas_dialog import CasoEtapasDialog, _carregar_rotinas_combo


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


def _carregar_modulos_no_combo(combo):
    """Popula o combo (LIST BOX) com os módulos cadastrados. Retorna a lista."""
    try:
        modulos = ModuloRepositorio.listar()
    except Exception:
        _log_erro()
        modulos = []
    combo.clear()
    combo.addItems([m["nome"] for m in modulos])
    return modulos


class CasoDialog(QDialog):
    def __init__(self, parent=None, caso=None, ciclo_id=None):
        super().__init__(parent)
        self.caso = caso
        self.ciclo_id = ciclo_id
        self.setWindowTitle("Novo Caso" if not caso else "Editar Caso")
        self.setMinimumWidth(560)

        form = QFormLayout()
        self.ed_codigo = QLineEdit()
        self.ed_codigo.setPlaceholderText("Deixe vazio para gerar automático")
        self.ed_tarefa = QLineEdit()
        self.ed_descricao = QTextEdit()
        self.ed_descricao.setFixedHeight(80)

        # ---- MÓDULO COMO LIST BOX (NÃO editável: seleciona da lista) ----
        self.cb_modulo = QComboBox()
        try:
            self.cb_modulo.setPlaceholderText("Selecione um módulo")
        except AttributeError:
            pass
        self.cb_modulo.setToolTip(
            "Selecione um módulo da lista ou clique em + para cadastrar um novo.")
        self._modulos_carregados = _carregar_modulos_no_combo(self.cb_modulo)
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

        self.cb_responsavel = QComboBox()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"] for u in UsuarioRepositorio.listar()])
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
        form.addRow("Rotina relacionada:", self.ed_rotina)
        form.addRow("Tipo:", self.cb_tipo)
        form.addRow("Prioridade:", self.cb_prioridade)
        form.addRow("Responsável:", linha_resp)
        form.addRow("Requisito/Compliance:", self.ed_requisito)
        form.addRow("Horas estimadas:", self.sp_horas)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)

        # ---- SEÇÃO ETAPAS DO CASO (modo edição) ----
        if caso and caso.get("id") and self.ciclo_id:
            layout.addWidget(QLabel("Etapas de validação deste caso (teste de processo):"))
            linha_etp = QHBoxLayout()
            linha_etp.addWidget(QLabel("Rotina do ciclo:"))
            self.cb_rotinas_form = QComboBox()
            _carregar_rotinas_combo(self.cb_rotinas_form, self.ciclo_id)
            linha_etp.addWidget(self.cb_rotinas_form, 1)
            btn_vinc = QPushButton("+ Rotina")
            btn_vinc.clicked.connect(self._vincular_rotina_form)
            btn_man = QPushButton("+ Manual")
            btn_man.clicked.connect(self._adicionar_manual_form)
            btn_sinc = QPushButton("Sincronizar")
            btn_sinc.clicked.connect(self._sincronizar_form)
            btn_rem = QPushButton("Remover")
            btn_rem.clicked.connect(self._remover_etapa_form)
            linha_etp.addWidget(btn_vinc)
            linha_etp.addWidget(btn_man)
            linha_etp.addWidget(btn_sinc)
            linha_etp.addWidget(btn_rem)
            layout.addLayout(linha_etp)

            self.grade_etapas = QTableWidget(0, 4)
            self.grade_etapas.setHorizontalHeaderLabels(
                ["Ordem", "Etapa (validação)", "Rotina vinculada", "Status"])
            self.grade_etapas.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.Stretch)
            self.grade_etapas.setColumnWidth(0, 55)
            self.grade_etapas.setColumnWidth(2, 190)
            self.grade_etapas.setColumnWidth(3, 130)
            self.grade_etapas.setSelectionBehavior(QTableWidget.SelectRows)
            self.grade_etapas.setEditTriggers(QTableWidget.NoEditTriggers)
            self.grade_etapas.setFixedHeight(150)
            layout.addWidget(self.grade_etapas)

            self.lbl_resumo_etapas = QLabel("")
            layout.addWidget(self.lbl_resumo_etapas)
        else:
            self.grade_etapas = None
            hint = QLabel(
                "Dica: após salvar o caso, use o botão 'Etapas do Ciclo' no "
                "rodapé da aba para vincular as rotinas do ciclo como etapas.")
            hint.setStyleSheet("color: #666;")
            layout.addWidget(hint)

        layout.addWidget(botoes)

        if caso:
            self._preencher(caso)
        if caso and caso.get("id") and self.ciclo_id:
            self._carregar_etapas_form()

    # ---------- Módulos / usuários ----------
    def _gerenciar_modulos(self):
        dlg = ModulosDialog(self)
        dlg.exec()
        self._modulos_carregados = _carregar_modulos_no_combo(self.cb_modulo)
        if getattr(dlg, "ultimo_novo", None):
            idx = self.cb_modulo.findText(dlg.ultimo_novo)
            if idx >= 0:
                self.cb_modulo.setCurrentIndex(idx)
                return
        atual = self.cb_modulo.currentText()
        idx = self.cb_modulo.findText(atual)
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)

    def _gerenciar_usuarios(self):
        dlg = UsuariosDialog(self)
        dlg.exec()
        atual = self.cb_responsavel.currentText()
        self.cb_responsavel.clear()
        self.cb_responsavel.addItem("")
        self.cb_responsavel.addItems([u["nome"] for u in UsuarioRepositorio.listar()])
        idx = self.cb_responsavel.findText(atual)
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)

    # ---------- Etapas do caso (grade no formulário) ----------
    def _carregar_etapas_form(self):
        if not self.caso or not self.grade_etapas:
            return
        caso_id = self.caso["id"]
        try:
            etapas = CasoEtapaRepositorio.listar(caso_id)
        except Exception:
            _log_erro()
            etapas = []
        self.grade_etapas.setRowCount(len(etapas))
        for i, e in enumerate(etapas):
            id_item = QTableWidgetItem(str(e.get("ordem") or i + 1))
            id_item.setData(Qt.UserRole, e["id"])
            self.grade_etapas.setItem(i, 0, id_item)
            self.grade_etapas.setItem(i, 1, QTableWidgetItem(e.get("nome") or ""))
            rot = ""
            if e.get("rotina_id"):
                rot = (f"{e.get('rotina_codigo') or ''} — "
                       f"{e.get('rotina_nome') or ''}").strip()
            self.grade_etapas.setItem(i, 2, QTableWidgetItem(rot))
            cmb = QComboBox()
            cmb.addItems(CasoEtapaRepositorio.STATUS_OPCOES)
            idx = cmb.findText(e.get("status") or "Nao iniciada")
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.currentIndexChanged.connect(
                lambda text, etid=e["id"]: self._mudar_status_form(etid, text))
            self.grade_etapas.setCellWidget(i, 3, cmb)
        total, passou = CasoEtapaRepositorio.resumo(caso_id)
        self.lbl_resumo_etapas.setText(
            f"Etapas: {total} | Passou: {passou} "
            f"| O caso só é aprovado quando TODAS passarem.")

    def _mudar_status_form(self, etapa_id, status):
        try:
            CasoEtapaRepositorio.atualizar_status(etapa_id, status)
        except Exception:
            _log_erro()

    def _etapa_form_selecionada(self):
        if not self.grade_etapas:
            return None
        linha = self.grade_etapas.currentRow()
        if linha < 0:
            return None
        item = self.grade_etapas.item(linha, 0)
        return item.data(Qt.UserRole) if item else None

    def _vincular_rotina_form(self):
        if not self.caso or not self.ciclo_id:
            return
        rotina_id = self.cb_rotinas_form.currentData()
        if not rotina_id:
            QMessageBox.information(
                self, "Aviso",
                "O ciclo não tem rotinas cadastradas.\n"
                "Cadastre em 'Detalhes do Ciclo → Rotinas'.")
            return
        try:
            ok, msg = CasoEtapaRepositorio.adicionar_de_rotina(
                self.caso["id"], rotina_id)
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro", "Falha ao vincular. Veja erros.log")
            return
        if ok:
            self._carregar_etapas_form()
        else:
            QMessageBox.warning(self, "Atenção", msg)

    def _adicionar_manual_form(self):
        if not self.caso:
            return
        nome, ok = QInputDialog.getText(
            self, "Etapa Manual", "Descreva a validação desta etapa:")
        if ok and nome.strip():
            ok2, msg = CasoEtapaRepositorio.adicionar_manual(self.caso["id"], nome)
            if ok2:
                self._carregar_etapas_form()
            else:
                QMessageBox.warning(self, "Atenção", msg)

    def _sincronizar_form(self):
        if not self.caso:
            return
        try:
            alteradas = CasoEtapaRepositorio.sincronizar_status(self.caso["id"])
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro", "Falha ao sincronizar. Veja erros.log")
            return
        self._carregar_etapas_form()
        QMessageBox.information(
            self, "Sincronizado",
            f"{alteradas} etapa(s) passaram para 'Passou' conforme as rotinas.")

    def _remover_etapa_form(self):
        etapa_id = self._etapa_form_selecionada()
        if not etapa_id:
            QMessageBox.information(self, "Aviso", "Selecione uma etapa.")
            return
        if QMessageBox.question(self, "Confirmar",
                                "Remover esta etapa do caso?") == QMessageBox.Yes:
            CasoEtapaRepositorio.remover(etapa_id)
            self._carregar_etapas_form()

    # ---------- Preencher / validar / dados ----------
    def _preencher(self, caso):
        self.ed_codigo.setText(caso.get("codigo") or "")
        self.ed_tarefa.setText(caso.get("tarefa") or "")
        self.ed_descricao.setPlainText(caso.get("descricao") or "")
        modulo_caso = (caso.get("modulo") or "").strip()
        idx = self.cb_modulo.findText(modulo_caso)
        if idx >= 0:
            self.cb_modulo.setCurrentIndex(idx)
        elif modulo_caso:
            self.cb_modulo.addItem(modulo_caso)
            self.cb_modulo.setCurrentIndex(self.cb_modulo.count() - 1)
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
        try:
            descricao = (self.ed_descricao.toPlainText() or "").strip()
            modulo = (self.cb_modulo.currentText() or "").strip()

            if not descricao:
                QMessageBox.warning(self, "Validação", "Informe a descrição do caso.")
                return
            if not modulo:
                if self.cb_modulo.count() == 0:
                    QMessageBox.warning(
                        self, "Validação",
                        "Nenhum módulo cadastrado.\nClique em + para criar o primeiro módulo.")
                else:
                    QMessageBox.warning(self, "Validação", "Selecione um módulo na lista.")
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

        self.lbl_ciclo = QLabel("Selecione um ciclo na aba 'Ciclos' para ver os casos.")
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
        topo.addStretch()
        layout.addLayout(topo)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Tarefa", "Módulo", "Tipo", "Prioridade", "Responsável", "Status Exec."])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 110)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 150)   # Tipo (aumentada)
        self.tabela.setColumnWidth(5, 80)
        self.tabela.setColumnWidth(6, 110)
        self.tabela.setColumnWidth(7, 110)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Caso")
        btn_editar = QPushButton("Editar")
        btn_etapas = QPushButton("Etapas do Ciclo...")
        btn_excluir = QPushButton("Excluir")
        btn_novo.clicked.connect(self.novo)
        btn_editar.clicked.connect(self.editar)
        btn_etapas.clicked.connect(self._abrir_etapas_ciclo)
        btn_etapas.setToolTip(
            "Vincular as rotinas do ciclo como etapas de validação do caso selecionado.")
        btn_excluir.clicked.connect(self.excluir)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_editar)
        botoes.addWidget(btn_etapas)
        botoes.addWidget(btn_excluir)
        botoes.addStretch()
        layout.addLayout(botoes)

    def _abrir_etapas_ciclo(self):
        caso_id = self._selecionado()
        if not caso_id:
            QMessageBox.information(self, "Aviso", "Selecione um caso.")
            return
        if not self.ciclo_id:
            QMessageBox.information(self, "Aviso",
                                    "Selecione um ciclo na aba 'Ciclos'.")
            return
        dlg = CasoEtapasDialog(self, caso_id=caso_id, ciclo_id=self.ciclo_id)
        dlg.exec()

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
                modulos = sorted({c["modulo"] for c in CasoRepositorio.listar(ciclo_id)})
            except Exception:
                modulos = []
            self.cb_filtro_modulo.blockSignals(True)
            self.cb_filtro_modulo.clear()
            self.cb_filtro_modulo.addItem("Todos")
            self.cb_filtro_modulo.addItems(modulos)
            self.cb_filtro_modulo.blockSignals(False)
        else:
            self.lbl_ciclo.setText("Selecione um ciclo na aba 'Ciclos' para ver os casos.")
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
            QMessageBox.critical(self, "Erro", "Não foi possível carregar os casos. Veja erros.log")
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
            self.tabela.setItem(i, 5, QTableWidgetItem(c.get("prioridade") or ""))
            self.tabela.setItem(i, 6, QTableWidgetItem(c.get("responsavel") or ""))
            self.tabela.setItem(i, 7, QTableWidgetItem(c.get("status_exec") or ""))

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
            QMessageBox.information(self, "Aviso", "Selecione um ciclo na aba 'Ciclos' primeiro.")
            return
        dlg = CasoDialog(self, caso=None, ciclo_id=self.ciclo_id)
        if dlg.exec():
            try:
                resultado = CasoRepositorio.inserir(self.ciclo_id, dlg.dados())
                codigo = resultado[1] if isinstance(resultado, tuple) else ""
                self.definir_ciclo(self.ciclo_id)
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
        dlg = CasoDialog(self, caso, self.ciclo_id)
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
                QMessageBox.critical(self, "Erro", "Não foi possível excluir. Veja erros.log")