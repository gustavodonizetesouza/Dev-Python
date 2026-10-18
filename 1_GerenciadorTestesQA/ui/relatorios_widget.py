"""Widget de Relatórios & KPIs — indicadores de decisão do ciclo.

Estrutura da aba (de cima para baixo):
1. ÍNDICE DE PRONTIDÃO PARA GO-LIVE (KPI composto com semáforo);
2. Cards de Execução (Taxa de Execução, Aprovação, Defeitos, % Médio);
3. Execução por Módulo (ranking de módulos críticos);
4. Cobertura de Rotinas (smoke + rastreabilidade);
5. Horas × Orçamento (estimado vs real, orçado vs realizado);
6. Melhorias por status.

CORES ADAPTATIVAS: todos os cards e linhas definem FUNDO + TEXTO sempre
juntos, ajustados ao tema (claro/escuro) — legível em ambos. Os estilos são
reaplicados a cada showEvent (troca de tema em runtime é refletida).
"""
import os
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from database.models import (
    CicloRepositorio, CicloDetalheRepositorio, KpiRepositorio,
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


def _tema_escuro(widget):
    """Detecta tema escuro pela luminância da cor de fundo da paleta."""
    try:
        cor = widget.palette().color(QPalette.Window)
        return cor.lightness() < 128
    except Exception:
        return False


def _estilo_card(widget):
    """Estilo de card/linha legível em QUALQUER tema.

    Define fundo e texto SEMPRE juntos (par autocontido). O problema do tema
    escuro era fundo claro fixo com texto herdando a cor clara do tema.
    """
    if _tema_escuro(widget):
        return ("background:#31363b; color:#e8e8e8; "
                "border:1px solid #4a4f54; border-radius:6px; padding:8px;")
    return ("background:#eef3f8; color:#1a1a1a; "
            "border:1px solid #c9d6e3; border-radius:6px; padding:8px;")


def _cores_status(widget):
    """(verde, amarelo, vermelho) legíveis no tema atual.

    Tema claro usa tons escuros (contraste sobre fundo claro);
    tema escuro usa tons claros (contraste sobre fundo escuro).
    """
    if _tema_escuro(widget):
        return "#4ade80", "#fbbf24", "#f87171"
    return "#1a7f37", "#b06a00", "#c0392b"


def _fundo_prontidao(widget):
    """Fundo do painel de prontidão, adaptado ao tema."""
    if _tema_escuro(widget):
        return "background:#31363b; border-radius:8px;"
    return "background:#f5f5f5; border-radius:8px;"


class RelatoriosWidget(QWidget):
    """Aba Relatórios & KPIs — painel de decisão do ciclo."""

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._aplicar_estilos()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---------- Seletor de ciclo ----------
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Ciclo:"))
        self.cb_ciclo = QComboBox()
        self.cb_ciclo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cb_ciclo.setMinimumContentsLength(30)
        self.cb_ciclo.currentIndexChanged.connect(self.carregar)
        topo.addWidget(self.cb_ciclo)
        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.clicked.connect(self.carregar)
        topo.addWidget(btn_atualizar)
        topo.addStretch()
        layout.addLayout(topo)

        # ---------- 1. Índice de Prontidão (semáforo) ----------
        self.lbl_prontidao = QLabel("Selecione um ciclo para ver os KPIs.")
        self.lbl_prontidao.setAlignment(Qt.AlignCenter)
        self.lbl_prontidao.setWordWrap(True)
        layout.addWidget(self.lbl_prontidao)

        self.lbl_prontidao_detalhe = QLabel("")
        self.lbl_prontidao_detalhe.setAlignment(Qt.AlignCenter)
        self.lbl_prontidao_detalhe.setWordWrap(True)
        # Sem cor fixa: herda do tema (legível em claro e escuro)
        layout.addWidget(self.lbl_prontidao_detalhe)

        # ---------- 2. Cards de Execução ----------
        linha_cards = QHBoxLayout()
        self.lbl_card_exec = QLabel("—")
        self.lbl_card_aprov = QLabel("—")
        self.lbl_card_def = QLabel("—")
        self.lbl_card_perc = QLabel("—")
        for lbl in (self.lbl_card_exec, self.lbl_card_aprov,
                    self.lbl_card_def, self.lbl_card_perc):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            linha_cards.addWidget(lbl, 1)
        layout.addLayout(linha_cards)

        # ---------- 3. Execução por Módulo ----------
        layout.addWidget(
            QLabel("<b>Execução por Módulo</b> (ranking de módulos críticos):"))
        self.tabela_modulos = QTableWidget(0, 7)
        self.tabela_modulos.setHorizontalHeaderLabels(
            ["Módulo", "Total", "Executados", "Aprovados", "Defeitos",
             "Taxa Aprovação", "Horas Reais"])
        self.tabela_modulos.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabela_modulos.setColumnWidth(1, 60)
        self.tabela_modulos.setColumnWidth(2, 85)
        self.tabela_modulos.setColumnWidth(3, 80)
        self.tabela_modulos.setColumnWidth(4, 75)
        self.tabela_modulos.setColumnWidth(5, 105)
        self.tabela_modulos.setColumnWidth(6, 85)
        self.tabela_modulos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_modulos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_modulos.setFixedHeight(180)
        layout.addWidget(self.tabela_modulos)

        # ---------- 4. Cobertura de Rotinas ----------
        self.lbl_rotinas = QLabel("—")
        self.lbl_rotinas.setWordWrap(True)
        layout.addWidget(self.lbl_rotinas)

        # ---------- 5. Horas × Orçamento ----------
        self.lbl_horas = QLabel("—")
        self.lbl_horas.setWordWrap(True)
        layout.addWidget(self.lbl_horas)

        # ---------- 6. Melhorias por status ----------
        layout.addWidget(QLabel("<b>Melhorias por Status</b> (do ciclo):"))
        self.tabela_melhorias = QTableWidget(0, 2)
        self.tabela_melhorias.setHorizontalHeaderLabels(
            ["Status", "Quantidade"])
        self.tabela_melhorias.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabela_melhorias.setColumnWidth(1, 100)
        self.tabela_melhorias.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_melhorias.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_melhorias.setFixedHeight(140)
        layout.addWidget(self.tabela_melhorias)

        layout.addStretch()

    # ---------- Estilos adaptativos ----------
    def _aplicar_estilos(self):
        """Aplica os estilos adaptativos ao tema atual.

        Chamado no __init__ e a cada showEvent — trocar o tema no menu com o
        app aberto atualiza os cards ao voltar para esta aba.
        """
        estilo_card = _estilo_card(self)
        for lbl in (self.lbl_card_exec, self.lbl_card_aprov,
                    self.lbl_card_def, self.lbl_card_perc,
                    self.lbl_rotinas, self.lbl_horas):
            lbl.setStyleSheet(estilo_card)
        self.lbl_prontidao.setStyleSheet(
            f"font-size: 15pt; font-weight: bold; padding: 10px; {_fundo_prontidao(self)}")

    # ---------- Ciclos ----------
    def carregar_ciclos(self):
        """Popula o combo de ciclos (chamado pelo main_window ao abrir a aba)."""
        try:
            ciclos = CicloRepositorio.listar()
        except Exception:
            _log_erro()
            ciclos = []
        self.cb_ciclo.blockSignals(True)
        self.cb_ciclo.clear()
        for c in ciclos:
            ano = c.get("ano") or "—"
            self.cb_ciclo.addItem(f"{c['nome']} ({ano})", c["id"])
        self.cb_ciclo.blockSignals(False)
        if ciclos:
            self.cb_ciclo.setCurrentIndex(0)  # dispara carregar()
        else:
            self.carregar()

    def _ciclo_atual(self):
        return self.cb_ciclo.currentData()

    def showEvent(self, event):
        """Ao ficar visível: reaplica estilos (tema pode ter mudado) e recarrega."""
        super().showEvent(event)
        self._aplicar_estilos()
        self.carregar()

    # ---------- Carregamento ----------
    def carregar(self):
        ciclo_id = self._ciclo_atual()
        if not ciclo_id:
            self.lbl_prontidao.setText("Selecione um ciclo para ver os KPIs.")
            self.lbl_prontidao.setStyleSheet(
                f"font-size: 15pt; font-weight: bold; padding: 10px; {_fundo_prontidao(self)}")
            self.lbl_prontidao_detalhe.setText("")
            for lbl in (self.lbl_card_exec, self.lbl_card_aprov,
                        self.lbl_card_def, self.lbl_card_perc):
                lbl.setText("—")
            self.lbl_rotinas.setText("—")
            self.lbl_horas.setText("—")
            self.tabela_modulos.setRowCount(0)
            self.tabela_melhorias.setRowCount(0)
            return
        try:
            self._carregar_prontidao(ciclo_id)
            self._carregar_kpis_execucao(ciclo_id)
            self._carregar_por_modulo(ciclo_id)
            self._carregar_rotinas(ciclo_id)
            self._carregar_horas(ciclo_id)
            self._carregar_melhorias(ciclo_id)
        except Exception:
            _log_erro()

    def _carregar_prontidao(self, ciclo_id):
        p = KpiRepositorio.prontidao(ciclo_id)
        verde, amarelo, vermelho = _cores_status(self)
        cor = verde if p["indice"] >= 90 else (
            amarelo if p["indice"] >= 70 else vermelho)
        self.lbl_prontidao.setText(
            f"{p['semaforo']}  ÍNDICE DE PRONTIDÃO: {p['indice']}/100  —  {p['status']}")
        self.lbl_prontidao.setStyleSheet(
            f"font-size: 15pt; font-weight: bold; padding: 10px; "
            f"color:{cor}; {_fundo_prontidao(self)}")
        self.lbl_prontidao_detalhe.setText(
            f"Composição: Execução {p['taxa_execucao']}% × 0,25  +  "
            f"Aprovação {p['taxa_aprovacao']}% × 0,35  +  "
            f"Smoke {p['cobertura_smoke']}% × 0,20  +  "
            f"Compliance {p['compliance']}% × 0,20")

    def _carregar_kpis_execucao(self, ciclo_id):
        k = KpiRepositorio.execucao(ciclo_id)
        self.lbl_card_exec.setText(
            f"<b>Taxa de Execução</b><br>{k['perc_execucao']}%<br>"
            f"<small>{k['executados']} de {k['total']} casos</small>")
        self.lbl_card_aprov.setText(
            f"<b>Taxa de Aprovação</b><br>{k['perc_aprovacao']}%<br>"
            f"<small>{k['aprovados']} aprovados</small>")
        self.lbl_card_def.setText(
            f"<b>Taxa de Defeitos</b><br>"
            f"{round((k['defeitos'] or 0) / k['total'] * 100, 1) if k['total'] else 0}%<br>"
            f"<small>{k['defeitos']} reprovados/bloqueados</small>")
        self.lbl_card_perc.setText(
            f"<b>% Médio de Conclusão</b><br>{k['perc_medio']}%<br>"
            f"<small>progresso granular</small>")

    def _carregar_por_modulo(self, ciclo_id):
        rows = KpiRepositorio.por_modulo(ciclo_id)
        self.tabela_modulos.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tabela_modulos.setItem(
                i, 0, QTableWidgetItem(r.get("modulo") or ""))
            self.tabela_modulos.setItem(
                i, 1, QTableWidgetItem(str(r.get("total") or 0)))
            self.tabela_modulos.setItem(
                i, 2, QTableWidgetItem(str(r.get("executados") or 0)))
            self.tabela_modulos.setItem(
                i, 3, QTableWidgetItem(str(r.get("aprovados") or 0)))
            self.tabela_modulos.setItem(
                i, 4, QTableWidgetItem(str(r.get("defeitos") or 0)))
            self.tabela_modulos.setItem(
                i, 5, QTableWidgetItem(f"{r.get('taxa_aprovacao') or 0}%"))
            self.tabela_modulos.setItem(
                i, 6, QTableWidgetItem(f"{round(r.get('horas_reais') or 0, 2)} h"))

    def _carregar_rotinas(self, ciclo_id):
        r = KpiRepositorio.rotinas(ciclo_id)
        if not r["total"]:
            self.lbl_rotinas.setText(
                "<b>Cobertura de Rotinas:</b> nenhuma rotina cadastrada neste ciclo.")
            return
        self.lbl_rotinas.setText(
            f"<b>Cobertura de Rotinas</b> — Total: {r['total']}  |  "
            f"Smoke OK (Concluídas): {r['concluidas']} → Cobertura: "
            f"{r['cobertura_smoke']}%  |  Com caso gerado: {r['com_caso']} → "
            f"Rastreabilidade: {r['rastreabilidade']}%")

    def _carregar_horas(self, ciclo_id):
        g = CicloDetalheRepositorio.kpis_gestao(ciclo_id)
        desvio = round(g["horas_reais"] - g["horas_estimadas"], 2)
        desvio_pct = (round(desvio / g["horas_estimadas"] * 100, 1)
                      if g["horas_estimadas"] else 0)
        self.lbl_horas.setText(
            f"<b>Horas × Orçamento</b> — Horas estimadas: {g['horas_estimadas']} h  |  "
            f"Reais: {g['horas_reais']} h (desvio {desvio:+} h / {desvio_pct:+}%)  |  "
            f"Custo orçado: R$ {g['custo_orcado']:.2f}  |  Realizado: "
            f"R$ {g['custo_real']:.2f} ({g['perc_orcado_usado']}% do orçado)  |  "
            f"Variação: R$ {g['variacao']:+.2f}")

    def _carregar_melhorias(self, ciclo_id):
        rows = KpiRepositorio.melhorias_resumo(ciclo_id)
        self.tabela_melhorias.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.tabela_melhorias.setItem(
                i, 0, QTableWidgetItem(r.get("status") or ""))
            self.tabela_melhorias.setItem(
                i, 1, QTableWidgetItem(str(r.get("quantidade") or 0)))
