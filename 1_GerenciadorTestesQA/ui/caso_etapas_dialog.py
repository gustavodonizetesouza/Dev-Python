"""Diálogo 'Etapas do Ciclo' — vincula as rotinas do ciclo como etapas do caso.

NOVA VERSÃO (prática e funcional):
- Lista as rotinas do ciclo com CHECKBOXES: código + nome + status;
- Marque as rotinas que o caso atravessa e clique 'Vincular Selecionadas';
- Cada rotina vira uma etapa, herdando o status
  (rotina Concluída => etapa 'Passou'; senão 'Não iniciada');
- 'Sincronizar com Rotinas' aplica a regra automaticamente.
"""
import os
import traceback
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QMessageBox, QHeaderView, QInputDialog,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt
from database.models import (
    CasoEtapaRepositorio, CicloDetalheRepositorio, CasoRepositorio,
)


def _log_erro():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "erros.log"),
                  "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write("\n" + "=" * 60 + "\n")
    except Exception:
        pass
    traceback.print_exc()


_STATUS_ROTINA_LABEL = {
    "Pendente": "Pendente",
    "Em andamento": "Em andamento",
    "Concluida": "Concluída",
    "Concluída": "Concluída",
    "Cancelada": "Cancelada",
    "Nao iniciada": "Não iniciada",
}


def _rotina_label(r):
    cod = (r.get("codigo") or "").strip()
    nome = (r.get("nome") or "").strip()
    status = _STATUS_ROTINA_LABEL.get(r.get("status"), r.get("status") or "Pendente")
    base = f"{cod} — {nome}" if cod else nome
    return f"{base}  [{status}]"


def _carregar_rotinas_combo(combo, ciclo_id):
    """Popula um QComboBox com as rotinas do ciclo (código + nome + status).
    Mantida para compatibilidade com o formulário de edição do caso."""
    combo.clear()
    if not ciclo_id:
        return
    try:
        rotinas = CicloDetalheRepositorio.listar_rotinas(ciclo_id)
    except Exception:
        _log_erro()
        rotinas = []
    for r in rotinas:
        combo.addItem(_rotina_label(r), r["id"])


def _listar_rotinas(ciclo_id):
    if not ciclo_id:
        return []
    try:
        return CicloDetalheRepositorio.listar_rotinas(ciclo_id)
    except Exception:
        _log_erro()
        return []


class CasoEtapasDialog(QDialog):
    def __init__(self, parent=None, caso_id=None, ciclo_id=None):
        super().__init__(parent)
        self.caso_id = caso_id
        self.ciclo_id = ciclo_id
        self.setWindowTitle("Etapas do Caso — vinculadas às rotinas do ciclo")
        self.resize(780, 580)

        caso = None
        if caso_id:
            try:
                caso = CasoRepositorio.obter(caso_id)
            except Exception:
                caso = None
        titulo = "?"
        if caso:
            titulo = (f"{caso.get('codigo') or ''} — "
                      f"{caso.get('tarefa') or caso.get('descricao') or ''}").strip()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Caso selecionado: <b>{titulo}</b>"))

        # ---- SEÇÃO 1: rotinas do ciclo (checkboxes) ----
        layout.addWidget(QLabel(
            "<b>1. Rotinas do ciclo</b> — marque as que fazem parte deste caso "
            "e clique em 'Vincular Selecionadas':"))
        self.lista_rotinas = QListWidget()
        self.lista_rotinas.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.lista_rotinas, 2)

        linha_a = QHBoxLayout()
        btn_vincular = QPushButton("Vincular Selecionadas")
        btn_todas = QPushButton("Marcar Todas")
        btn_limpar = QPushButton("Limpar Marcas")
        btn_atualizar = QPushButton("Atualizar Lista")
        btn_vincular.clicked.connect(self._vincular_selecionadas)
        btn_todas.clicked.connect(self._marcar_todas)
        btn_limpar.clicked.connect(self._limpar_marcas)
        btn_atualizar.clicked.connect(self._atualizar_rotinas)
        linha_a.addWidget(btn_vincular)
        linha_a.addWidget(btn_todas)
        linha_a.addWidget(btn_limpar)
        linha_a.addWidget(btn_atualizar)
        linha_a.addStretch()
        layout.addLayout(linha_a)

        self.lbl_rotinas_vazias = QLabel("")
        self.lbl_rotinas_vazias.setStyleSheet("color: #b06a00;")
        self.lbl_rotinas_vazias.setWordWrap(True)
        layout.addWidget(self.lbl_rotinas_vazias)

        # ---- SEÇÃO 2: etapas já vinculadas ----
        layout.addWidget(QLabel("<b>2. Etapas já vinculadas a este caso</b>:"))
        self.grade = QTableWidget(0, 4)
        self.grade.setHorizontalHeaderLabels(
            ["Ordem", "Etapa (validação)", "Rotina vinculada", "Status"])
        self.grade.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.grade.setColumnWidth(0, 55)
        self.grade.setColumnWidth(2, 230)
        self.grade.setColumnWidth(3, 130)
        self.grade.setSelectionBehavior(QTableWidget.SelectRows)
        self.grade.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.grade, 3)

        linha_b = QHBoxLayout()
        btn_manual = QPushButton("Adicionar Manual")
        btn_sinc = QPushButton("Sincronizar com Rotinas")
        btn_remover = QPushButton("Remover Etapa")
        btn_fechar = QPushButton("Fechar")
        btn_manual.clicked.connect(self._adicionar_manual)
        btn_sinc.clicked.connect(self._sincronizar)
        btn_remover.clicked.connect(self._remover)
        btn_fechar.clicked.connect(self.accept)
        linha_b.addWidget(btn_manual)
        linha_b.addWidget(btn_sinc)
        linha_b.addWidget(btn_remover)
        linha_b.addStretch()
        linha_b.addWidget(btn_fechar)
        layout.addLayout(linha_b)

        self._atualizar_rotinas()
        self._carregar_etapas()

    # ---------- Rotinas (lista de checkboxes) ----------
    def _atualizar_rotinas(self):
        self.lista_rotinas.clear()
        rotinas = _listar_rotinas(self.ciclo_id)
        if not rotinas:
            self.lbl_rotinas_vazias.setText(
                "Nenhuma rotina cadastrada neste ciclo ainda.\n"
                "Cadastre em: aba Ciclos → selecione o ciclo → "
                "Detalhes do Ciclo → Rotinas.")
        else:
            self.lbl_rotinas_vazias.setText("")
        for r in rotinas:
            item = QListWidgetItem(_rotina_label(r))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                          Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, r["id"])
            self.lista_rotinas.addItem(item)

    def _rotinas_marcadas(self):
        marcadas = []
        for i in range(self.lista_rotinas.count()):
            item = self.lista_rotinas.item(i)
            if item.checkState() == Qt.Checked:
                marcadas.append(item.data(Qt.UserRole))
        return marcadas

    def _marcar_todas(self):
        for i in range(self.lista_rotinas.count()):
            self.lista_rotinas.item(i).setCheckState(Qt.Checked)

    def _limpar_marcas(self):
        for i in range(self.lista_rotinas.count()):
            self.lista_rotinas.item(i).setCheckState(Qt.Unchecked)

    def _vincular_selecionadas(self):
        if not self.caso_id:
            QMessageBox.information(self, "Aviso", "Selecione um caso primeiro.")
            return
        marcadas = self._rotinas_marcadas()
        if not marcadas:
            QMessageBox.information(
                self, "Aviso",
                "Marque no mínimo uma rotina na lista (item 1) e clique novamente.")
            return
        vinculadas = 0
        ja_existiam = 0
        erros = 0
        for rotina_id in marcadas:
            try:
                ok, _msg = CasoEtapaRepositorio.adicionar_de_rotina(
                    self.caso_id, rotina_id)
            except Exception:
                _log_erro()
                erros += 1
                continue
            if ok:
                vinculadas += 1
            else:
                ja_existiam += 1
        self._limpar_marcas()
        self._carregar_etapas()
        if vinculadas:
            QMessageBox.information(
                self, "Sucesso",
                f"{vinculadas} rotina(s) vinculada(s) como etapa(s) do caso.")
        elif ja_existiam:
            QMessageBox.information(
                self, "Atenção",
                f"{ja_existiam} rotina(s) já estavam vinculadas a este caso.")
        if erros:
            QMessageBox.warning(self, "Erros",
                                f"{erros} vínculo(s) falharam. Veja erros.log")

    # ---------- Etapas já vinculadas ----------
    def _carregar_etapas(self):
        if not self.caso_id:
            return
        try:
            etapas = CasoEtapaRepositorio.listar(self.caso_id)
        except Exception:
            _log_erro()
            etapas = []
        self.grade.setRowCount(len(etapas))
        for i, e in enumerate(etapas):
            id_item = QTableWidgetItem(str(e.get("ordem") or i + 1))
            id_item.setData(Qt.UserRole, e["id"])
            self.grade.setItem(i, 0, id_item)
            self.grade.setItem(i, 1, QTableWidgetItem(e.get("nome") or ""))
            rot = ""
            if e.get("rotina_id"):
                rot = (f"{e.get('rotina_codigo') or ''} — "
                       f"{e.get('rotina_nome') or ''}").strip()
            self.grade.setItem(i, 2, QTableWidgetItem(rot))
            cmb = QComboBox()
            cmb.addItems(CasoEtapaRepositorio.STATUS_OPCOES)
            idx = cmb.findText(e.get("status") or "Nao iniciada")
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.currentIndexChanged.connect(
                lambda text, etid=e["id"]: self._mudar_status(etid, text))
            self.grade.setCellWidget(i, 3, cmb)

    def _mudar_status(self, etapa_id, status):
        try:
            CasoEtapaRepositorio.atualizar_status(etapa_id, status)
        except Exception:
            _log_erro()

    def _etapa_selecionada(self):
        linha = self.grade.currentRow()
        if linha < 0:
            return None
        item = self.grade.item(linha, 0)
        return item.data(Qt.UserRole) if item else None

    def _adicionar_manual(self):
        if not self.caso_id:
            return
        nome, ok = QInputDialog.getText(
            self, "Etapa Manual", "Descreva a validação desta etapa:")
        if ok and nome.strip():
            try:
                ok2, msg = CasoEtapaRepositorio.adicionar_manual(self.caso_id, nome)
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Falha ao adicionar. Veja erros.log")
                return
            if ok2:
                self._carregar_etapas()
            else:
                QMessageBox.warning(self, "Atenção", msg)

    def _sincronizar(self):
        if not self.caso_id:
            return
        try:
            alteradas = CasoEtapaRepositorio.sincronizar_status(self.caso_id)
        except Exception:
            _log_erro()
            QMessageBox.critical(self, "Erro",
                                 "Falha ao sincronizar. Veja erros.log")
            return
        self._carregar_etapas()
        QMessageBox.information(
            self, "Sincronizado",
            f"{alteradas} etapa(s) passaram para 'Passou' conforme as rotinas "
            f"concluídas do ciclo.")

    def _remover(self):
        etapa_id = self._etapa_selecionada()
        if not etapa_id:
            QMessageBox.information(self, "Aviso", "Selecione uma etapa.")
            return
        if QMessageBox.question(self, "Confirmar",
                                "Remover esta etapa do caso?") == QMessageBox.Yes:
            try:
                CasoEtapaRepositorio.remover(etapa_id)
            except Exception:
                _log_erro()
                QMessageBox.critical(self, "Erro",
                                     "Falha ao remover. Veja erros.log")
                return
            self._carregar_etapas()