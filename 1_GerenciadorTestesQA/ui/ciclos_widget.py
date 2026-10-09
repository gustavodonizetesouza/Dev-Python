"""Widget de ciclos de virada de versão."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QFormLayout, QDateEdit,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView,
)
from PySide6.QtCore import Qt, QDate
from database.models import CicloRepositorio, CasoRepositorio


class CicloDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Ciclo de Virada")
        self.setMinimumWidth(520)

        form = QFormLayout()
        self.ed_nome = QLineEdit()
        self.ed_nome.setPlaceholderText("Ex.: Release 12.1.2410")

        self.ed_versao = QLineEdit()
        self.ed_versao.setPlaceholderText("Ex.: 12.1.2410")

        # Ano agora é digitação MANUAL (sem setinhas de spinbox)
        self.ed_ano = QLineEdit()
        self.ed_ano.setPlaceholderText("Ex.: 2026")
        self.ed_ano.setText(str(QDate.currentDate().year()))

        self.de_inicio = QDateEdit(QDate.currentDate())
        self.de_inicio.setCalendarPopup(True)
        self.de_fim = QDateEdit(QDate.currentDate().addMonths(2))
        self.de_fim.setCalendarPopup(True)

        form.addRow("Nome do Ciclo:", self.ed_nome)
        form.addRow("Versão:", self.ed_versao)
        form.addRow("Ano:", self.ed_ano)
        form.addRow("Início:", self.de_inicio)
        form.addRow("Fim:", self.de_fim)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self._validar)
        botoes.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botoes)

    def _validar(self):
        if not self.ed_nome.text().strip():
            QMessageBox.warning(self, "Validação", "Informe o nome do ciclo.")
            return
        ano = self.ed_ano.text().strip()
        if not ano.isdigit() or len(ano) != 4:
            QMessageBox.warning(self, "Validação",
                                "Informe um ano válido (ex.: 2026).")
            return
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "versao": self.ed_versao.text().strip(),
            "ano": int(self.ed_ano.text().strip()),
            "data_inicio": self.de_inicio.date().toString("yyyy-MM-dd"),
            "data_fim": self.de_fim.date().toString("yyyy-MM-dd"),
            "status": "Planejado",
        }


class AssociarCasosDialog(QDialog):
    """Diálogo de associação com status de vínculo e opção de retirar.

    - Checkbox marcado  = caso JÁ vinculado ao ciclo
    - Checkbox desmarcado = caso NÃO vinculado
    - Ao confirmar: marca -> vincula; desmarca -> desvincula
    """

    def __init__(self, ciclo_id, parent=None):
        super().__init__(parent)
        self.ciclo_id = ciclo_id
        self.setWindowTitle("Associar Casos ao Ciclo")
        self.resize(760, 600)  # tela maior

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Marque para VINCULAR · Desmarque para RETIRAR o vínculo do ciclo. "
            "Depois clique em 'Aplicar Alterações':"))

        # Grid: Selecionar | Código | Tarefa | Vínculo
        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(
            ["Selecionar", "Código", "Tarefa", "Vínculo"])
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabela.setColumnWidth(0, 90)
        self.tabela.setColumnWidth(1, 150)
        self.tabela.setColumnWidth(3, 120)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        # Legenda
        layout.addWidget(QLabel(
            "Legenda:  ☑ marcado = vinculado  ·  ☐ desmarcado = não vinculado"))

        self._carregar()

        botoes = QHBoxLayout()
        btn_aplicar = QPushButton("Aplicar Alterações")
        btn_aplicar.clicked.connect(self._aplicar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_aplicar)
        botoes.addStretch()
        botoes.addWidget(btn_cancelar)
        layout.addLayout(botoes)

    def _carregar(self):
        casos = CasoRepositorio.listar()
        vinculados = CicloRepositorio.casos_vinculados(self.ciclo_id)

        self.tabela.setRowCount(len(casos))
        for i, c in enumerate(casos):
            ja_vinculado = c["id"] in vinculados

            # Coluna 0: checkbox (marcado se já vinculado)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if ja_vinculado else Qt.Unchecked)
            chk.setData(Qt.UserRole, c["id"])
            self.tabela.setItem(i, 0, chk)

            # Coluna 1: código
            self.tabela.setItem(i, 1, QTableWidgetItem(c["codigo"]))

            # Coluna 2: tarefa
            self.tabela.setItem(i, 2, QTableWidgetItem(c.get("tarefa") or ""))

            # Coluna 3: status do vínculo (com cor)
            status_item = QTableWidgetItem(
                "Vinculado" if ja_vinculado else "Não vinculado")
            status_item.setFlags(Qt.ItemIsEnabled)  # só leitura
            if ja_vinculado:
                status_item.setBackground(Qt.green)
                status_item.setForeground(Qt.black)
            else:
                status_item.setBackground(Qt.lightGray)
            self.tabela.setItem(i, 3, status_item)

    def _aplicar(self):
        # Separa os casos por estado do checkbox
        marcados = []      # querem ficar vinculados
        for i in range(self.tabela.rowCount()):
            item = self.tabela.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                marcados.append(item.data(Qt.UserRole))

        vinculados_atuais = CicloRepositorio.casos_vinculados(self.ciclo_id)

        # Para VINCULAR: marcados que ainda não estão vinculados
        a_vincular = [cid for cid in marcados if cid not in vinculados_atuais]
        # Para DESVINCULAR: não marcados que estão vinculados
        a_desvincular = [
            cid for cid in vinculados_atuais if cid not in marcados]

        if a_vincular:
            CicloRepositorio.associar_casos(self.ciclo_id, a_vincular)
        if a_desvincular:
            CicloRepositorio.desvincular_casos(self.ciclo_id, a_desvincular)

        if not a_vincular and not a_desvincular:
            QMessageBox.information(
                self, "Sem alterações", "Nenhuma mudança foi aplicada.")
            return

        msg = f"Alterações aplicadas!\n"
        if a_vincular:
            msg += f"\n✓ {len(a_vincular)} caso(s) VINCULADO(S)"
        if a_desvincular:
            msg += f"\n✗ {len(a_desvincular)} caso(s) DESVINCULADO(S)"
        QMessageBox.information(self, "Sucesso", msg)
        self.accept()


class CiclosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.carregar()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tabela = QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Nome", "Versão", "Ano", "Início", "Fim"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabela)

        botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo Ciclo")
        btn_associar = QPushButton("Associar Casos")
        btn_novo.clicked.connect(self.novo)
        btn_associar.clicked.connect(self.associar)
        botoes.addWidget(btn_novo)
        botoes.addWidget(btn_associar)
        botoes.addStretch()
        layout.addLayout(botoes)

    def carregar(self):
        ciclos = CicloRepositorio.listar()
        self.tabela.setRowCount(len(ciclos))
        for i, c in enumerate(ciclos):
            valores = [str(c["id"]), c["nome"], c.get("versao") or "", str(c.get("ano") or ""),
                       c.get("data_inicio") or "", c.get("data_fim") or ""]
            for j, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if j == 0:
                    item.setData(Qt.UserRole, c["id"])
                self.tabela.setItem(i, j, item)

    def _ciclo_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.tabela.item(linha, 0).data(Qt.UserRole)

    def novo(self):
        dlg = CicloDialog(self)
        if dlg.exec():
            CicloRepositorio.inserir(dlg.dados())
            self.carregar()

    def associar(self):
        ciclo_id = self._ciclo_selecionado()
        if not ciclo_id:
            QMessageBox.information(self, "Aviso", "Selecione um ciclo.")
            return
        dlg = AssociarCasosDialog(ciclo_id, self)
        dlg.exec()
