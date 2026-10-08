"""Widget de ciclos de virada de versão."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QFormLayout, QSpinBox, QDateEdit,
    QMessageBox, QDialog, QDialogButtonBox, QHeaderView, QListWidget,
    QListWidgetItem, QComboBox,
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
        self.ed_versao = QLineEdit()
        self.sp_ano = QSpinBox()
        self.sp_ano.setRange(2000, 2100)
        self.sp_ano.setValue(QDate.currentDate().year())
        self.de_inicio = QDateEdit(QDate.currentDate())
        self.de_inicio.setCalendarPopup(True)
        self.de_fim = QDateEdit(QDate.currentDate().addMonths(2))
        self.de_fim.setCalendarPopup(True)

        form.addRow("Nome do Ciclo:", self.ed_nome)
        form.addRow("Versão:", self.ed_versao)
        form.addRow("Ano:", self.sp_ano)
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
        self.accept()

    def dados(self):
        return {
            "nome": self.ed_nome.text().strip(),
            "versao": self.ed_versao.text().strip(),
            "ano": self.sp_ano.value(),
            "data_inicio": self.de_inicio.date().toString("yyyy-MM-dd"),
            "data_fim": self.de_fim.date().toString("yyyy-MM-dd"),
            "status": "Planejado",
        }


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

        casos = CasoRepositorio.listar()
        dlg = QDialog(self)
        dlg.setWindowTitle("Associar Casos ao Ciclo")
        dlg.setMinimumSize(500, 450)
        layout = QVBoxLayout(dlg)

        layout.addWidget(
            QLabel("Selecione os casos (Ctrl+clique para múltiplos):"))
        lista = QListWidget()
        for c in casos:
            item = QListWidgetItem(
                f"{c['codigo']} — {c['modulo']} — {c['descricao']}")
            item.setData(Qt.UserRole, c["id"])
            lista.addItem(item)
        layout.addWidget(lista)

        botoes = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(botoes)

        def confirmar():
            ids = [lista.item(i).data(Qt.UserRole) for i in range(lista.count())
                   if lista.item(i).isSelected()]
            if not ids:
                QMessageBox.information(
                    dlg, "Aviso", "Selecione ao menos um caso.")
                return
            CicloRepositorio.associar_casos(ciclo_id, ids)
            dlg.accept()
            QMessageBox.information(
                self, "Sucesso", f"{len(ids)} casos associados ao ciclo.")

        botoes.accepted.connect(confirmar)
        botoes.rejected.connect(dlg.reject)
        dlg.exec()
