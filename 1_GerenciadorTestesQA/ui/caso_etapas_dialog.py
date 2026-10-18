"""Diálogo 'Etapas do Ciclo' — CADASTRO de etapas do caso (estrutura).

- Seção 1: lista de rotinas do ciclo com checkboxes (marcar e 'Vincular Selecionadas');
- Seção 2: grade de etapas do caso — vínculo, desvínculo, etapa manual, remoção;
  Status, % e Horas são SOMENTE LEITURA: são informados na ABA EXECUÇÃO.
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
    status = _STATUS_ROTINA_LABEL.get(
        r.get("status"), r.get("status") or "Pendente")
    base = f"{cod} — {nome}" if cod else nome
    return f"{base}  [{status}]"


def _carregar_rotinas_combo(combo, ciclo_id):
    """Popula um QComboBox com as rotinas do ciclo (código + nome + status)."""
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
    return rotinas


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
        self.setWindowTitle(
            "Etapas do Caso — cadastro (execução na aba Execução)")
        self.resize(800, 640)

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

        # ---------- SEÇÃO 1: rotinas do ciclo (checkboxes) ----------
        layout.addWidget(QLabel(
            "<b>1. Rotinas do ciclo</b> — marque as que farão parte deste caso "
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

        # ---------- SEÇÃO 2: etapas do caso (leitura de execução) ----------
        layout.addWidget(QLabel(
            "<b>2. Etapas deste caso</b> — Status, % e Horas são informados "
            "na ABA EXECUÇÃO (aqui é só cadastro/estrutura):"))
        self.grade = QTableWidget(0, 6)
        self.grade.setHorizontalHeaderLabels(
            ["Ordem", "Etapa (validação)", "Rotina vinculada", "Status", "%", "Horas"])
        self.grade.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.grade.setColumnWidth(0, 50)
        self.grade.setColumnWidth(2, 200)
        self.grade.setColumnWidth(3, 110)
        self.grade.setColumnWidth(4, 60)
        self.grade.setColumnWidth(5, 70)
        self.grade.setSelectionBehavior(QTableWidget.SelectRows)
        self.grade.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.grade, 3)

        # Linha: vincular rotina à etapa SELECIONADA
        linha_vinc = QHBoxLayout()
        linha_vinc.addWidget(QLabel("Vincular rotina à etapa selecionada:"))
        self.cb_rotinas_etapa = QComboBox()
        _carregar_rotinas_combo(self.cb_rotinas_etapa, ciclo_id)
        linha_vinc.addWidget(self.cb_rotinas_etapa, 1)
        btn_vinc_etapa = QPushButton("Vincular na Etapa")
        btn_vinc_etapa.setToolTip(
            "Associa a rotina escolhida à etapa selecionada na grade (inclusive etapa manual).")
        btn_vinc_etapa.clicked.connect(self._vincular_rotina_na_etapa)
        btn_desc = QPushButton("Desvincular")
        btn_desc.setToolTip(
            "Remove o vínculo da etapa selecionada com a rotina.")
        btn_desc.clicked.connect(self._desvincular_rotina_etapa)
        linha_vinc.addWidget(btn_vinc_etapa)
        linha_vinc.addWidget(btn_desc)
        layout.addLayout(linha_vinc)

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
        # Também atualiza o combo de vínculo à etapa selecionada
        _carregar_rotinas_combo(self.cb_rotinas_etapa, self.ciclo_id)

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
            QMessageBox.information(
                self, "Aviso", "Selecione um caso primeiro.")
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

    # ---------- Etapas do caso (leitura) ----------
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
            self.grade.setItem(i, 3, QTableWidgetItem(e.get("status") or ""))
            self.grade.setItem(i, 4, QTableWidgetItem(
                f"{int(e.get('percentual') or 0)}%"))
            self.grade.setItem(i, 5, QTableWidgetItem(
                str(e.get("horas_reais") or 0)))

    def _etapa_selecionada(self):
        linha = self.grade.currentRow()
        if linha < 0:
            return None
        item = self.grade.item(linha, 0)
        return item.data(Qt.UserRole) if item else None

    def _vincular_rotina_na_etapa(self):
        """Vincula a rotina escolhida no combo à etapa selecionada (manual ou não)."""
        etapa_id = self._etapa_selecionada()
        if not etapa_id:
            QMessageBox.information(
                self, "Aviso", "Selecione uma etapa na grade (2) primeiro.")
            return
        rotina_id = self.cb_rotinas_etapa.currentData()
        if not rotina_id:
            QMessageBox.information(
                self, "Aviso",
                "O ciclo não tem rotinas disponíveis.\n"
                "Cadastre em 'Detalhes do Ciclo → Rotinas'.")
            return
        try:
            ok, msg = CasoEtapaRepositorio.vincular_rotina(etapa_id, rotina_id)
        except Exception:
            _log_erro()
            QMessageBox.critical(
                self, "Erro", "Falha ao vincular. Veja erros.log")
            return
        self._carregar_etapas()
        if ok:
            QMessageBox.information(self, "Sucesso", msg)
        else:
            QMessageBox.warning(self, "Atenção", msg)

    def _desvincular_rotina_etapa(self):
        etapa_id = self._etapa_selecionada()
        if not etapa_id:
            QMessageBox.information(
                self, "Aviso", "Selecione uma etapa na grade (2) primeiro.")
            return
        if QMessageBox.question(
                self, "Confirmar",
                "Desvincular a rotina desta etapa? A etapa manual será mantida.") \
                == QMessageBox.Yes:
            try:
                CasoEtapaRepositorio.desvincular_rotina(etapa_id)
            except Exception:
                _log_erro()
                QMessageBox.critical(
                    self, "Erro", "Falha ao desvincular. Veja erros.log")
                return
            self._carregar_etapas()

    def _adicionar_manual(self):
        if not self.caso_id:
            return
        nome, ok = QInputDialog.getText(
            self, "Etapa Manual", "Descreva a validação técnica desta etapa:")
        if ok and nome.strip():
            try:
                ok2, msg = CasoEtapaRepositorio.adicionar_manual(
                    self.caso_id, nome)
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
