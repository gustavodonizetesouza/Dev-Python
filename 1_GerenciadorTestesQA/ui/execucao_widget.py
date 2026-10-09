"""Widget de execução dos testes de um ciclo."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QFileDialog,
)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt
from database.models import CicloRepositorio, UsuarioRepositorio
from utils.helpers import STATUS_OPCOES


def horas_para_float(texto):
    """Converte 'HH:MM' em horas decimais (ex.: '01:30' -> 1.5)."""
    texto = (texto or "").strip()
    if not texto or texto in ("00:00", "0:00"):
        return 0.0
    try:
        partes = texto.split(":")
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        return round(h + m / 60, 2)
    except (ValueError, IndexError):
        return 0.0


def float_para_horas(valor):
    """Converte horas decimais em 'HH:MM' (ex.: 1.5 -> '01:30')."""
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        valor = 0.0
    h = int(valor)
    m = int(round((valor - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{h:02d}:{m:02d}"


def tem_execucao(exec):
    """Diz se um caso já possui execução registrada (além do padrão)."""
    return (
        exec.get("status") not in ("Não iniciado", "Nao iniciado", None, "")
        or int(exec.get("percentual") or 0) > 0
        or bool(exec.get("responsavel"))
        or bool(exec.get("evidencia"))
        or bool(exec.get("observacoes"))
    )


class ExecucaoDialog(QDialog):
    """Registro (novo) ou edição de execução.
    - execucao=None  -> título 'Registrar Execução', campos vazios
    - execucao=dict  -> título 'Editar Execução', campos pré-preenchidos
    """

    def __init__(self, execucao=None, parent=None):
        super().__init__(parent)
        self.execucao = execucao
        editando = execucao is not None
        self.setWindowTitle(
            "Editar Execução" if editando else "Registrar Execução")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        # Status
        linha_status = QHBoxLayout()
        linha_status.addWidget(QLabel("Status:"))
        self.cb_status = QComboBox()
        self.cb_status.addItems(STATUS_OPCOES)
        linha_status.addWidget(self.cb_status, 1)
        layout.addLayout(linha_status)

        # Percentual — campo digitável SEM setinhas
        linha_perc = QHBoxLayout()
        linha_perc.addWidget(QLabel("Percentual (%):"))
        self.ed_perc = QLineEdit()
        self.ed_perc.setPlaceholderText("0 a 100")
        self.ed_perc.setValidator(QIntValidator(0, 100))
        self.ed_perc.setText("0")
        linha_perc.addWidget(self.ed_perc, 1)
        layout.addLayout(linha_perc)

        # Horas — máscara HH:MM SEM setinhas
        linha_horas = QHBoxLayout()
        linha_horas.addWidget(QLabel("Horas (HH:MM):"))
        self.ed_horas = QLineEdit()
        self.ed_horas.setInputMask("00:00")
        self.ed_horas.setText("00:00")
        linha_horas.addWidget(self.ed_horas, 1)
        layout.addLayout(linha_horas)

        # Responsável — combo carregado dos usuários cadastrados
        linha_resp = QHBoxLayout()
        linha_resp.addWidget(QLabel("Responsável:"))
        self.cb_responsavel = QComboBox()
        self._carregar_usuarios(self.cb_responsavel)
        linha_resp.addWidget(self.cb_responsavel, 1)
        layout.addLayout(linha_resp)

        # Evidência
        layout.addWidget(QLabel("Evidência (caminho do arquivo/print):"))
        linha_ev = QHBoxLayout()
        self.ed_evidencia = QLineEdit()
        btn_anexar = QPushButton("Anexar...")
        linha_ev.addWidget(self.ed_evidencia, 1)
        linha_ev.addWidget(btn_anexar)
        layout.addLayout(linha_ev)
        btn_anexar.clicked.connect(self._anexar)

        # Observações
        layout.addWidget(QLabel("Observações:"))
        self.ed_obs = QTextEdit()
        self.ed_obs.setFixedHeight(80)
        layout.addWidget(self.ed_obs)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        if editando:
            self._preencher(execucao)

    @staticmethod
    def _carregar_usuarios(combo):
        combo.clear()
        combo.addItem("")
        usuarios = UsuarioRepositorio.listar()
        combo.addItems([u["nome"] for u in usuarios])

    def _anexar(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar evidência")
        if arquivo:
            self.ed_evidencia.setText(arquivo)

    def _preencher(self, execucao):
        idx = self.cb_status.findText(execucao.get("status") or "")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        self.ed_perc.setText(str(int(execucao.get("percentual") or 0)))
        self.ed_horas.setText(float_para_horas(
            execucao.get("horas_reais") or 0))
        idx = self.cb_responsavel.findText(execucao.get("responsavel") or "")
        if idx >= 0:
            self.cb_responsavel.setCurrentIndex(idx)
        self.ed_evidencia.setText(execucao.get("evidencia") or "")
        self.ed_obs.setPlainText(execucao.get("observacoes") or "")

    def _validar(self):
        self.accept()

    def dados(self):
        try:
            perc = int(self.ed_perc.text().strip())
        except ValueError:
            perc = 0
        perc = max(0, min(100, perc))
        return {
            "status": self.cb_status.currentText(),
            "percentual": perc,
            "responsavel": self.cb_responsavel.currentText(),
            "horas_reais": horas_para_float(self.ed_horas.text()),
            "evidencia": self.ed_evidencia.text().strip(),
            "observacoes": self.ed_obs.toPlainText().strip(),
        }


class ExecucaoWidget(QWidget):
    def __init__(self):
        super().__init__()
        # estado exato de cada linha (índice da lista = linha do grid)
        self._dados_linha = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("Ciclo:"))
        self.cb_ciclo = QComboBox()
        self.cb_ciclo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_ciclo, 1)
        topo.addStretch()
        layout.addLayout(topo)

        self.lbl_kpis = QLabel("Selecione um ciclo para ver os KPIs.")
        layout.addWidget(self.lbl_kpis)

        self.tabela = QTableWidget(0, 9)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Código", "Tarefa", "Módulo", "Status", "%", "Responsável",
             "Execução", "Atualizado"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 45)
        self.tabela.setColumnWidth(1, 120)
        self.tabela.setColumnWidth(3, 90)
        self.tabela.setColumnWidth(4, 110)
        self.tabela.setColumnWidth(5, 55)
        self.tabela.setColumnWidth(6, 110)
        self.tabela.setColumnWidth(7, 100)
        # Ordenação desligada: a ordem do grid é SEMPRE a ordem da lista self._dados_linha
        self.tabela.setSortingEnabled(False)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        # Ao selecionar uma linha, atualiza quais botões ficam habilitados
        self.tabela.currentCellChanged.connect(self._atualizar_botoes)
        # Duplo clique = Editar (só funciona se houver execução)
        self.tabela.cellDoubleClicked.connect(self._abrir_edicao_linha)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        self.btn_novo = QPushButton("Novo Lançamento")
        self.btn_novo.clicked.connect(self.novo)
        self.btn_editar = QPushButton("Editar")
        self.btn_editar.clicked.connect(self.editar)
        botoes.addWidget(self.btn_novo)
        botoes.addWidget(self.btn_editar)
        botoes.addStretch()
        layout.addLayout(botoes)

        self.btn_novo.setEnabled(False)
        self.btn_editar.setEnabled(False)

    def carregar_ciclos(self):
        ciclos = CicloRepositorio.listar()
        self.cb_ciclo.blockSignals(True)
        self.cb_ciclo.clear()
        for c in ciclos:
            self.cb_ciclo.addItem(
                f"{c['nome']} ({c.get('versao') or 'sem versão'})", c["id"])
        self.cb_ciclo.blockSignals(False)
        if ciclos:
            self.carregar()
        else:
            self.tabela.setRowCount(0)
            self._dados_linha = []
            self.lbl_kpis.setText("Nenhum ciclo cadastrado ainda.")
            self.btn_novo.setEnabled(False)
            self.btn_editar.setEnabled(False)

    def carregar(self):
        idx = self.cb_ciclo.currentIndex()
        if idx < 0:
            return
        ciclo_id = self.cb_ciclo.itemData(idx)
        casos = CicloRepositorio.casos_do_ciclo(ciclo_id)
        kpis = CicloRepositorio.kpis(ciclo_id)

        self.lbl_kpis.setText(
            f"Total: {kpis['total']} | Execução: {kpis['perc_execucao']}% | "
            f"Aprovação: {kpis['perc_aprovacao']}% | Defeitos: {kpis['defeitos']} | "
            f"Progresso médio: {kpis['perc_medio']}% | Andamento: {kpis['andamento']}"
        )

        # Estado calculado UMA VEZ na carga: cada linha guarda o próprio registro + flag
        self._dados_linha = []
        for c in casos:
            reg = dict(c)
            reg["_tem_exec"] = tem_execucao(c)
            self._dados_linha.append(reg)

        self.tabela.setRowCount(len(self._dados_linha))
        for i, reg in enumerate(self._dados_linha):
            tem = reg["_tem_exec"]
            valores = [
                str(reg["id"]), reg["codigo"], reg.get(
                    "tarefa") or "", reg["modulo"],
                reg["status"], str(reg["percentual"]), reg.get(
                    "responsavel") or "",
                "Registrada" if tem else "—",
                reg.get("atualizado_em") or "",
            ]
            for j, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setData(Qt.UserRole, reg["id"])
                if j == 7:  # coluna "Execução" com cor
                    if tem:
                        item.setBackground(Qt.green)
                        item.setForeground(Qt.black)
                    else:
                        item.setBackground(Qt.lightGray)
                self.tabela.setItem(i, j, item)

        self._atualizar_botoes()

    def _atualizar_botoes(self, *args):
        """Habilita/desabilita os botões conforme a linha selecionada."""
        linha = self.tabela.currentRow()
        tem = False
        if 0 <= linha < len(self._dados_linha):
            tem = self._dados_linha[linha].get("_tem_exec", False)
        self.btn_novo.setEnabled(
            0 <= linha < len(self._dados_linha) and not tem)
        self.btn_editar.setEnabled(0 <= linha < len(self._dados_linha) and tem)

    def _abrir_edicao_linha(self, linha, coluna):
        self.tabela.setCurrentCell(linha, 0)
        self.editar()

    def novo(self):
        """Novo lançamento: só em caso SEM execução."""
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self._dados_linha):
            QMessageBox.information(
                self, "Aviso", "Selecione um teste na lista.")
            return
        reg = self._dados_linha[linha]
        if reg["_tem_exec"]:
            QMessageBox.warning(
                self, "Execução já existente",
                "Este teste já possui execução registrada.\nUse o botão 'Editar'.")
            return
        dlg = ExecucaoDialog(None, self)
        if dlg.exec():
            self._salvar(linha, dlg.dados())

    def editar(self):
        """Editar: só em caso COM execução."""
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self._dados_linha):
            QMessageBox.information(
                self, "Aviso", "Selecione um teste na lista.")
            return
        reg = self._dados_linha[linha]
        if not reg["_tem_exec"]:
            QMessageBox.information(
                self, "Sem execução",
                "Este teste ainda não possui execução registrada.\n"
                "Use o botão 'Novo Lançamento' para iniciar.")
            return
        dlg = ExecucaoDialog(reg, self)
        if dlg.exec():
            self._salvar(linha, dlg.dados())

    def _salvar(self, linha, dados):
        """Atualiza no banco usando o ID da PRÓPRIA linha e recarrega."""
        cc_id = self._dados_linha[linha]["id"]
        CicloRepositorio.atualizar_execucao(
            cc_id, dados["status"], dados["percentual"], dados["responsavel"],
            dados["horas_reais"], dados["evidencia"], dados["observacoes"])
        self.carregar()
