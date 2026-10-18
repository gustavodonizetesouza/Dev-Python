"""Páginas do aplicativo: Dashboard, Lançamentos, Contas, Categorias,
Recorrências, Relatórios e Usuários (painel do admin).

Dashboard separa REALIZADO (pagos) de PREVISÃO (pendentes). Lançamentos
exibem coluna de status com filtro e alternância de 1 clique.
"""
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QComboBox, QDateEdit, QFrame, QGridLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from core.util import (avancar_mes, fmt_data, fmt_mes_curto, fmt_moeda,
                       mes_anterior, nome_mes)
from dominio.repositorio import ErroRegraNegocio
from ui.dialogos import (DialogoCategoria, DialogoConta, DialogoLancamento,
                         DialogoNovaSenha, DialogoNovoUsuario,
                         DialogoRecorrencia)
from ui.graficos import GraficoBarras, GraficoPizza

VERDE, VERMELHO, AMBAR, CINZA = "#43a047", "#e53935", "#ff9800", "#9aa0a6"


def _estilo_valor(cor: str) -> str:
    return f"font-size: 20px; font-weight: 700; color: {cor};"


class PaginaBase(QWidget):
    """Base comum às páginas: referência ao repositório e helpers de UI."""

    dados_alterados = pyqtSignal()

    def __init__(self, repo):
        super().__init__()
        self.repo = repo

    def refrescar(self):
        pass

    # ---------- helpers ----------
    def _montar_tabela(self, colunas):
        t = QTableWidget()
        t.setColumnCount(len(colunas))
        t.setHorizontalHeaderLabels(colunas)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return t

    def _adicionar_linha(self, tabela, valores, cor_por_col=None, alinhar_direita=()):
        r = tabela.rowCount()
        tabela.insertRow(r)
        for col, texto in enumerate(valores):
            it = QTableWidgetItem(str(texto))
            if col in alinhar_direita:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                    Qt.AlignmentFlag.AlignVCenter)
            if cor_por_col and cor_por_col.get(col) is not None:
                it.setForeground(QColor(cor_por_col[col]))
            tabela.setItem(r, col, it)

    def _confirmar(self, titulo, texto):
        r = QMessageBox.question(
            self, titulo, texto,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return r == QMessageBox.StandardButton.Yes

    def _exibir_erro(self, e):
        QMessageBox.critical(self, "Erro", str(e))


class PaginaDashboard(PaginaBase):
    """KPIs separados em REALIZADO (pagos) e PREVISÃO (pendentes).

    Linha 1 — realizado: saldo efetivo, receitas e despesas pagas do mês,
    resultado do mês. Linha 2 — previsão: saldo previsto (todas as pendências
    liquidadas), a receber e a pagar no mês, contagem de pendências.
    Gráficos mostram realizado.
    """

    def __init__(self, repo):
        super().__init__(repo)
        hoje = QDate.currentDate()
        self.ano, self.mes = hoje.year(), hoje.month()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(12)

        topo = QHBoxLayout()
        t = QLabel("Dashboard")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addStretch()
        bt_anterior = QPushButton("◀")
        bt_anterior.setFixedWidth(44)
        bt_proximo = QPushButton("▶")
        bt_proximo.setFixedWidth(44)
        bt_hoje = QPushButton("Hoje")
        self.lb_mes = QLabel("")
        self.lb_mes.setObjectName("tituloPagina")
        topo.addWidget(bt_anterior)
        topo.addWidget(self.lb_mes)
        topo.addWidget(bt_proximo)
        topo.addWidget(bt_hoje)
        raiz.addLayout(topo)

        bt_anterior.clicked.connect(self._mes_anterior)
        bt_proximo.clicked.connect(self._mes_proximo)
        bt_hoje.clicked.connect(self._voltar_hoje)

        self.cards = {}

        def _criar_card(chave, titulo, layout):
            card = QFrame()
            card.setObjectName("card")
            v = QVBoxLayout(card)
            v.setContentsMargins(14, 12, 14, 12)
            lb = QLabel(titulo)
            lb.setObjectName("tituloCard")
            valor = QLabel("—")
            valor.setObjectName("kpiValor")
            v.addWidget(lb)
            v.addWidget(valor)
            self.cards[chave] = valor
            layout.addWidget(card)

        linha_kpi = QHBoxLayout()
        linha_kpi.setSpacing(12)
        _criar_card("saldo", "Saldo total", linha_kpi)
        _criar_card("receitas", "Receitas do mês", linha_kpi)
        _criar_card("despesas", "Despesas do mês", linha_kpi)
        _criar_card("resultado", "Resultado do mês", linha_kpi)
        raiz.addLayout(linha_kpi)

        linha_prev = QHBoxLayout()
        linha_prev.setSpacing(12)
        _criar_card("previsto", "Saldo previsto", linha_prev)
        _criar_card("a_receber", "A receber (mês)", linha_prev)
        _criar_card("a_pagar", "A pagar (mês)", linha_prev)
        _criar_card("pendencias", "Pendências (mês)", linha_prev)
        raiz.addLayout(linha_prev)
        self.lb_qtd = QLabel("")
        raiz.addWidget(self.lb_qtd)

        linha_graf = QHBoxLayout()
        linha_graf.setSpacing(12)
        card_p = QFrame()
        card_p.setObjectName("card")
        vp = QVBoxLayout(card_p)
        vp.setContentsMargins(14, 12, 14, 12)
        tp = QLabel("Despesas por categoria (realizado)")
        tp.setObjectName("tituloCard")
        self.g_pizza = GraficoPizza()
        vp.addWidget(tp)
        vp.addWidget(self.g_pizza)
        card_b = QFrame()
        card_b.setObjectName("card")
        vb = QVBoxLayout(card_b)
        vb.setContentsMargins(14, 12, 14, 12)
        tb = QLabel("Entradas x Saídas — últimos 6 meses (realizado)")
        tb.setObjectName("tituloCard")
        self.g_barras = GraficoBarras()
        vb.addWidget(tb)
        vb.addWidget(self.g_barras)
        linha_graf.addWidget(card_p, 1)
        linha_graf.addWidget(card_b, 1)
        raiz.addLayout(linha_graf)
        self.refrescar()

    def _mes_anterior(self):
        self.ano, self.mes = mes_anterior(self.ano, self.mes)
        self.refrescar()

    def _mes_proximo(self):
        self.ano, self.mes = avancar_mes(self.ano, self.mes)
        self.refrescar()

    def _voltar_hoje(self):
        hoje = QDate.currentDate()
        self.ano, self.mes = hoje.year(), hoje.month()
        self.refrescar()

    def refrescar(self):
        k = self.repo.kpis_mes(self.ano, self.mes)
        self.lb_mes.setText(nome_mes(self.ano, self.mes))

        # --- linha 1: realizado ---
        self.cards["saldo"].setText(fmt_moeda(k.saldo_total))
        self.cards["saldo"].setStyleSheet(
            _estilo_valor(VERDE if k.saldo_total >= 0 else VERMELHO))
        self.cards["receitas"].setText(fmt_moeda(k.receitas_mes))
        self.cards["receitas"].setStyleSheet(_estilo_valor(VERDE))
        self.cards["despesas"].setText(fmt_moeda(k.despesas_mes))
        self.cards["despesas"].setStyleSheet(_estilo_valor(VERMELHO))
        resultado = k.receitas_mes - k.despesas_mes
        self.cards["resultado"].setText(fmt_moeda(resultado))
        self.cards["resultado"].setStyleSheet(
            _estilo_valor(VERDE if resultado >= 0 else VERMELHO))

        # --- linha 2: previsão ---
        self.cards["previsto"].setText(fmt_moeda(k.saldo_previsto))
        self.cards["previsto"].setStyleSheet(
            _estilo_valor(VERDE if k.saldo_previsto >= 0 else VERMELHO))
        self.cards["a_receber"].setText(fmt_moeda(k.a_receber_mes))
        self.cards["a_receber"].setStyleSheet(_estilo_valor(VERDE))
        self.cards["a_pagar"].setText(fmt_moeda(k.a_pagar_mes))
        self.cards["a_pagar"].setStyleSheet(_estilo_valor(VERMELHO))
        self.cards["pendencias"].setText(str(k.pendentes_mes))
        self.cards["pendencias"].setStyleSheet(
            _estilo_valor(AMBAR if k.pendentes_mes else CINZA))

        self.lb_qtd.setText(
            f"{k.lancamentos_mes} lançamento(s) em {nome_mes(self.ano, self.mes)}"
            f" · {k.pendentes_mes} pendência(s) no mês")
        self.g_pizza.set_dados(
            self.repo.gastos_por_categoria(self.ano, self.mes))
        self.g_barras.set_serie(
            self.repo.evolucao_mensal(6, self.ano, self.mes))


class PaginaLancamentos(PaginaBase):
    """Entradas e saídas com filtros (conta, categoria, tipo, status,
    período e busca) e alternância pago/pendente em 1 clique."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Novo lançamento")
        bt_novo.setProperty("variacao", "primaria")
        bt_editar = QPushButton("Editar")
        bt_pago = QPushButton("Marcar pago/pendente")
        bt_pago.setProperty("variacao", "sucesso")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")
        bt_atualizar = QPushButton("Atualizar")

        topo = QHBoxLayout()
        t = QLabel("Lançamentos")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_editar)
        topo.addWidget(bt_pago)
        topo.addWidget(bt_excluir)
        topo.addStretch()
        topo.addWidget(bt_atualizar)
        raiz.addLayout(topo)

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.cb_conta_f = QComboBox()
        self.cb_cat_f = QComboBox()
        self.cb_tipo_f = QComboBox()
        self.cb_tipo_f.addItem("Entradas e saídas", None)
        self.cb_tipo_f.addItem("Somente entradas", "entrada")
        self.cb_tipo_f.addItem("Somente saídas", "saida")
        self.cb_status_f = QComboBox()
        self.cb_status_f.addItem("Todos os status", None)
        self.cb_status_f.addItem("Pagos / recebidos", 1)
        self.cb_status_f.addItem("Pendentes", 0)
        hoje = QDate.currentDate()
        self.dt_ini = QDateEdit(QDate(hoje.year(), hoje.month(), 1))
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setCalendarPopup(True)
        self.dt_fim = QDateEdit(hoje)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setCalendarPopup(True)
        self.ed_busca = QLineEdit()
        self.ed_busca.setPlaceholderText("Buscar na descrição…")

        grid.addWidget(QLabel("Conta"), 0, 0)
        grid.addWidget(self.cb_conta_f, 0, 1)
        grid.addWidget(QLabel("Categoria"), 0, 2)
        grid.addWidget(self.cb_cat_f, 0, 3)
        grid.addWidget(QLabel("Tipo"), 0, 4)
        grid.addWidget(self.cb_tipo_f, 0, 5)
        grid.addWidget(QLabel("Status"), 1, 0)
        grid.addWidget(self.cb_status_f, 1, 1)
        grid.addWidget(QLabel("De"), 1, 2)
        grid.addWidget(self.dt_ini, 1, 3)
        grid.addWidget(QLabel("Até"), 1, 4)
        grid.addWidget(self.dt_fim, 1, 5)
        grid.addWidget(QLabel("Buscar"), 2, 0)
        grid.addWidget(self.ed_busca, 2, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(5, 1)
        raiz.addWidget(card)

        self.tabela = self._montar_tabela(
            ["Data", "Descrição", "Conta", "Categoria", "Tipo", "Valor", "Status"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_pago.clicked.connect(self._alternar_pago)
        bt_excluir.clicked.connect(self._excluir)
        bt_atualizar.clicked.connect(self.refrescar)
        self.tabela.cellDoubleClicked.connect(lambda *_: self._editar())
        self.cb_conta_f.currentIndexChanged.connect(self.refrescar)
        self.cb_cat_f.currentIndexChanged.connect(self.refrescar)
        self.cb_tipo_f.currentIndexChanged.connect(self.refrescar)
        self.cb_status_f.currentIndexChanged.connect(self.refrescar)
        self.dt_ini.dateChanged.connect(self.refrescar)
        self.dt_fim.dateChanged.connect(self.refrescar)
        self.ed_busca.returnPressed.connect(self.refrescar)

        self._linhas = []
        self.refrescar()

    def _recarregar_filtros(self):
        sel_conta = self.cb_conta_f.currentData()
        sel_cat = self.cb_cat_f.currentData()
        self.cb_conta_f.blockSignals(True)
        self.cb_cat_f.blockSignals(True)
        self.cb_conta_f.clear()
        self.cb_conta_f.addItem("Todas as contas", None)
        for c in self.repo.listar_contas():
            self.cb_conta_f.addItem(c.nome, c.id)
        self.cb_conta_f.setCurrentIndex(
            max(0, self.cb_conta_f.findData(sel_conta)))
        self.cb_cat_f.clear()
        self.cb_cat_f.addItem("Todas as categorias", None)
        for g in self.repo.listar_categorias():
            self.cb_cat_f.addItem(g.nome, g.id)
        self.cb_cat_f.setCurrentIndex(max(0, self.cb_cat_f.findData(sel_cat)))
        self.cb_conta_f.blockSignals(False)
        self.cb_cat_f.blockSignals(False)

    def _filtros_atuais(self):
        return dict(
            conta_id=self.cb_conta_f.currentData(),
            categoria_id=self.cb_cat_f.currentData(),
            tipo=self.cb_tipo_f.currentData(),
            pago=self.cb_status_f.currentData(),
            data_ini=self.dt_ini.date().toString("yyyy-MM-dd"),
            data_fim=self.dt_fim.date().toString("yyyy-MM-dd"),
            busca=self.ed_busca.text().strip() or None)

    def refrescar(self):
        self._recarregar_filtros()
        self._linhas = self.repo.listar_lancamentos(self._filtros_atuais())
        t = self.tabela
        t.setRowCount(0)
        for l in self._linhas:
            cor = VERDE if l.tipo == "entrada" else VERMELHO
            pago = bool(l.pago)
            cor_status = VERDE if pago else AMBAR
            self._adicionar_linha(
                t,
                [fmt_data(l.data_mov), l.descricao or "—", l.conta_nome,
                 l.categoria_nome, "Entrada" if l.tipo == "entrada" else "Saída",
                 fmt_moeda(l.valor), "Pago" if pago else "Pendente"],
                cor_por_col={4: cor, 5: cor, 6: cor_status},
                alinhar_direita=(5, 6))

    def _selecionado(self):
        i = self.tabela.currentRow()
        if i < 0 or i >= len(self._linhas):
            QMessageBox.information(
                self, "Atenção", "Selecione um lançamento na tabela.")
            return None
        return self._linhas[i]

    def _novo(self):
        dlg = DialogoLancamento(self.repo, None, self)
        if dlg.exec():
            self.repo.salvar_lancamento(**dlg.dados())
            self.dados_alterados.emit()
            self.refrescar()

    def _editar(self):
        l = self._selecionado()
        if not l:
            return
        dlg = DialogoLancamento(self.repo, l, self)
        if dlg.exec():
            self.repo.salvar_lancamento(**dlg.dados(), id=l.id)
            self.dados_alterados.emit()
            self.refrescar()

    def _alternar_pago(self):
        """Alterna pago <-> pendente no lançamento selecionado."""
        l = self._selecionado()
        if not l:
            return
        try:
            self.repo.alternar_pago(l.id)
            self.dados_alterados.emit()
            self.refrescar()
        except Exception as e:
            self._exibir_erro(e)

    def _excluir(self):
        l = self._selecionado()
        if not l:
            return
        extra = ("\n\nEste lançamento foi gerado por uma recorrência — "
                 "excluí-lo não afeta as próximas gerações.") if l.recorrencia_id else ""
        if not self._confirmar("Excluir lançamento",
                               f"Excluir o lançamento de {fmt_data(l.data_mov)} "
                               f"({fmt_moeda(l.valor)})?{extra}"):
            return
        try:
            self.repo.excluir_lancamento(l.id)
            self.dados_alterados.emit()
            self.refrescar()
        except Exception as e:
            self._exibir_erro(e)


class PaginaContas(PaginaBase):
    """Cadastro de contas/carteiras. O saldo atual considera apenas
    lançamentos pagos/recebidos (contas a pagar não movimentam o caixa)."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Nova conta")
        bt_novo.setProperty("variacao", "primaria")
        bt_editar = QPushButton("Editar")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")

        topo = QHBoxLayout()
        t = QLabel("Contas")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_editar)
        topo.addWidget(bt_excluir)
        topo.addStretch()
        raiz.addLayout(topo)

        self.tabela = self._montar_tabela(
            ["Nome", "Tipo", "Saldo inicial", "Saldo atual (pagos)", "Status"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_excluir.clicked.connect(self._excluir)
        self.tabela.cellDoubleClicked.connect(lambda *_: self._editar())
        self.refrescar()

    def refrescar(self):
        t = self.tabela
        t.setRowCount(0)
        for c in self.repo.listar_contas():
            cor = VERDE if c.saldo_atual >= 0 else VERMELHO
            self._adicionar_linha(
                t,
                [c.nome, c.tipo, fmt_moeda(c.saldo_inicial),
                 fmt_moeda(c.saldo_atual), "Ativa" if c.ativo else "Inativa"],
                cor_por_col={2: cor, 3: cor},
                alinhar_direita=(2, 3))

    def _selecionado(self):
        i = self.tabela.currentRow()
        if i < 0:
            QMessageBox.information(
                self, "Atenção", "Selecione uma conta na tabela.")
            return None
        return self.repo.listar_contas()[i]

    def _novo(self):
        dlg = DialogoConta(self.repo, None, self)
        if dlg.exec():
            self.repo.salvar_conta(**dlg.dados())
            self.dados_alterados.emit()
            self.refrescar()

    def _editar(self):
        c = self._selecionado()
        if not c:
            return
        dlg = DialogoConta(self.repo, c, self)
        if dlg.exec():
            self.repo.salvar_conta(**dlg.dados(), id=c.id)
            self.dados_alterados.emit()
            self.refrescar()

    def _excluir(self):
        c = self._selecionado()
        if not c:
            return
        if not self._confirmar(
                "Excluir conta",
                f"Excluir a conta '{c.nome}'?\n\nTambém serão excluídos TODOS os "
                "lançamentos e recorrências vinculados a ela. Essa ação não pode ser desfeita."):
            return
        try:
            self.repo.excluir_conta(c.id)
            self.dados_alterados.emit()
            self.refrescar()
        except Exception as e:
            self._exibir_erro(e)


class PaginaCategorias(PaginaBase):
    """Cadastro de categorias com cor e contagem de uso."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Nova categoria")
        bt_novo.setProperty("variacao", "primaria")
        bt_editar = QPushButton("Editar")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")

        topo = QHBoxLayout()
        t = QLabel("Categorias")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_editar)
        topo.addWidget(bt_excluir)
        topo.addStretch()
        raiz.addLayout(topo)

        self.tabela = self._montar_tabela(
            ["Nome", "Tipo", "Cor", "Uso", "Status"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_excluir.clicked.connect(self._excluir)
        self.tabela.cellDoubleClicked.connect(lambda *_: self._editar())
        self.refrescar()

    def refrescar(self):
        t = self.tabela
        t.setRowCount(0)
        for g in self.repo.listar_categorias():
            r = t.rowCount()
            t.insertRow(r)
            valores = [g.nome, "Saída" if g.tipo == "saida" else "Entrada",
                       "", f"{g.uso} lançamento(s)",
                       "Ativa" if g.ativo else "Inativa"]
            for col, texto in enumerate(valores):
                it = QTableWidgetItem(texto)
                if col == 2:
                    it.setBackground(QColor(g.cor or "#607d8b"))
                if col == 4 and not g.ativo:
                    it.setForeground(QColor(CINZA))
                t.setItem(r, col, it)

    def _selecionado(self):
        i = self.tabela.currentRow()
        if i < 0:
            QMessageBox.information(
                self, "Atenção", "Selecione uma categoria na tabela.")
            return None
        return self.repo.listar_categorias()[i]

    def _novo(self):
        dlg = DialogoCategoria(self.repo, None, self)
        if dlg.exec():
            self.repo.salvar_categoria(**dlg.dados())
            self.dados_alterados.emit()
            self.refrescar()

    def _editar(self):
        g = self._selecionado()
        if not g:
            return
        dlg = DialogoCategoria(self.repo, g, self)
        if dlg.exec():
            self.repo.salvar_categoria(**dlg.dados(), id=g.id)
            self.dados_alterados.emit()
            self.refrescar()

    def _excluir(self):
        g = self._selecionado()
        if not g:
            return
        if not self._confirmar("Excluir categoria",
                               f"Excluir a categoria '{g.nome}'?"):
            return
        try:
            self.repo.excluir_categoria(g.id)
            self.dados_alterados.emit()
            self.refrescar()
        except ErroRegraNegocio as e:
            QMessageBox.warning(self, "Categoria em uso", str(e))
        except Exception as e:
            self._exibir_erro(e)


class PaginaRecorrencias(PaginaBase):
    """Contas fixas mensais. Os lançamentos gerados nascem PENDENTES
    (conta a pagar/receber) e são efetivados ao marcar como pago."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Nova recorrência")
        bt_novo.setProperty("variacao", "primaria")
        bt_editar = QPushButton("Editar")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")
        bt_gerar = QPushButton("Gerar pendentes agora")

        topo = QHBoxLayout()
        t = QLabel("Recorrências")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_editar)
        topo.addWidget(bt_excluir)
        topo.addStretch()
        topo.addWidget(bt_gerar)
        raiz.addLayout(topo)

        self.tabela = self._montar_tabela(
            ["Descrição", "Conta", "Categoria", "Tipo", "Valor",
             "Dia", "Início", "Último gerado", "Status"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_excluir.clicked.connect(self._excluir)
        bt_gerar.clicked.connect(self._gerar)
        self.tabela.cellDoubleClicked.connect(lambda *_: self._editar())
        self._linhas = []
        self.refrescar()

    @staticmethod
    def _fmt_mes(ym):
        if not ym or len(ym) < 7:
            return "—"
        return f"{ym[5:7]}/{ym[:4]}"

    def refrescar(self):
        self._linhas = self.repo.listar_recorrencias()
        t = self.tabela
        t.setRowCount(0)
        for r in self._linhas:
            cor = VERDE if r.tipo == "entrada" else VERMELHO
            self._adicionar_linha(
                t,
                [r.descricao, r.conta_nome, r.categoria_nome,
                 "Entrada" if r.tipo == "entrada" else "Saída",
                 fmt_moeda(r.valor), str(r.dia_do_mes),
                 self._fmt_mes(r.mes_inicio), self._fmt_mes(
                     r.ultimo_gerado or ""),
                 "Ativa" if r.ativo else "Inativa"],
                cor_por_col={4: cor},
                alinhar_direita=(4,))

    def _selecionado(self):
        i = self.tabela.currentRow()
        if i < 0 or i >= len(self._linhas):
            QMessageBox.information(
                self, "Atenção", "Selecione uma recorrência na tabela.")
            return None
        return self._linhas[i]

    def _novo(self):
        dlg = DialogoRecorrencia(self.repo, None, self)
        if dlg.exec():
            self.repo.salvar_recorrencia(**dlg.dados())
            self.dados_alterados.emit()
            self.refrescar()

    def _editar(self):
        r = self._selecionado()
        if not r:
            return
        dlg = DialogoRecorrencia(self.repo, r, self)
        if dlg.exec():
            self.repo.salvar_recorrencia(**dlg.dados(), id=r.id)
            self.dados_alterados.emit()
            self.refrescar()

    def _excluir(self):
        r = self._selecionado()
        if not r:
            return
        if not self._confirmar(
                "Excluir recorrência",
                f"Excluir a recorrência '{r.descricao}'?\n\n"
                "Os lançamentos já gerados permanecem no histórico."):
            return
        try:
            self.repo.excluir_recorrencia(r.id)
            self.dados_alterados.emit()
            self.refrescar()
        except Exception as e:
            self._exibir_erro(e)

    def _gerar(self):
        try:
            gerados, puladas = self.repo.gerar_pendentes()
        except Exception as e:
            self._exibir_erro(e)
            return
        msg = (f"{gerados} lançamento(s) gerado(s) até o mês corrente.\n\n"
               "Os lançamentos gerados nascem como PENDENTES — marque-os como "
               "pagos em Lançamentos quando efetivar.")
        if puladas:
            msg += "\n\nNão puderam ser geradas: " + ", ".join(puladas)
        if gerados:
            self.dados_alterados.emit()
        self.refrescar()
        QMessageBox.information(self, "Recorrências", msg)


class PaginaRelatorios(PaginaBase):
    """Relatórios por período: resumo mensal e consolidação por categoria,
    com filtro de status (todos / pagos / pendentes)."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_atualizar = QPushButton("Atualizar")
        bt_atualizar.setProperty("variacao", "primaria")

        topo = QHBoxLayout()
        t = QLabel("Relatórios")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addStretch()
        topo.addWidget(bt_atualizar)
        raiz.addLayout(topo)

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        hoje = QDate.currentDate()
        ano, mes = hoje.year(), hoje.month()
        for _ in range(11):
            ano, mes = mes_anterior(ano, mes)
        self.dt_ini = QDateEdit(QDate(ano, mes, 1))
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setCalendarPopup(True)
        self.dt_fim = QDateEdit(hoje)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setCalendarPopup(True)
        self.cb_conta_f = QComboBox()
        self.cb_cat_f = QComboBox()
        self.cb_tipo_f = QComboBox()
        self.cb_tipo_f.addItem("Entradas e saídas", None)
        self.cb_tipo_f.addItem("Somente entradas", "entrada")
        self.cb_tipo_f.addItem("Somente saídas", "saida")
        self.cb_status_f = QComboBox()
        self.cb_status_f.addItem("Todos os status", None)
        self.cb_status_f.addItem("Pagos / recebidos", 1)
        self.cb_status_f.addItem("Pendentes", 0)

        grid.addWidget(QLabel("De"), 0, 0)
        grid.addWidget(self.dt_ini, 0, 1)
        grid.addWidget(QLabel("Até"), 0, 2)
        grid.addWidget(self.dt_fim, 0, 3)
        grid.addWidget(QLabel("Conta"), 0, 4)
        grid.addWidget(self.cb_conta_f, 0, 5)
        grid.addWidget(QLabel("Categoria"), 1, 0)
        grid.addWidget(self.cb_cat_f, 1, 1)
        grid.addWidget(QLabel("Tipo"), 1, 2)
        grid.addWidget(self.cb_tipo_f, 1, 3)
        grid.addWidget(QLabel("Status"), 1, 4)
        grid.addWidget(self.cb_status_f, 1, 5)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(5, 1)
        raiz.addWidget(card)

        lb1 = QLabel("Resumo mensal")
        lb1.setObjectName("tituloCard")
        raiz.addWidget(lb1)
        self.tabela_mensal = self._montar_tabela(
            ["Mês", "Entradas", "Saídas", "Resultado"])
        raiz.addWidget(self.tabela_mensal, 1)

        lb2 = QLabel("Por categoria")
        lb2.setObjectName("tituloCard")
        raiz.addWidget(lb2)
        self.tabela_cat = self._montar_tabela(
            ["Categoria", "Entradas", "Saídas", "Resultado"])
        raiz.addWidget(self.tabela_cat, 1)

        bt_atualizar.clicked.connect(self.refrescar)
        self.dt_ini.dateChanged.connect(self.refrescar)
        self.dt_fim.dateChanged.connect(self.refrescar)
        self.cb_tipo_f.currentIndexChanged.connect(self.refrescar)
        self.cb_status_f.currentIndexChanged.connect(self.refrescar)
        self.refrescar()

    def _filtros(self):
        return dict(
            conta_id=self.cb_conta_f.currentData(),
            categoria_id=self.cb_cat_f.currentData(),
            tipo=self.cb_tipo_f.currentData(),
            pago=self.cb_status_f.currentData(),
            data_ini=self.dt_ini.date().toString("yyyy-MM-dd"),
            data_fim=self.dt_fim.date().toString("yyyy-MM-dd"))

    def _recarregar_filtros(self):
        sel_conta = self.cb_conta_f.currentData()
        sel_cat = self.cb_cat_f.currentData()
        self.cb_conta_f.blockSignals(True)
        self.cb_cat_f.blockSignals(True)
        self.cb_conta_f.clear()
        self.cb_conta_f.addItem("Todas as contas", None)
        for c in self.repo.listar_contas():
            self.cb_conta_f.addItem(c.nome, c.id)
        self.cb_conta_f.setCurrentIndex(
            max(0, self.cb_conta_f.findData(sel_conta)))
        self.cb_cat_f.clear()
        self.cb_cat_f.addItem("Todas as categorias", None)
        for g in self.repo.listar_categorias():
            self.cb_cat_f.addItem(g.nome, g.id)
        self.cb_cat_f.setCurrentIndex(max(0, self.cb_cat_f.findData(sel_cat)))
        self.cb_conta_f.blockSignals(False)
        self.cb_cat_f.blockSignals(False)

    @staticmethod
    def _linha_total(tabela, valores):
        r = tabela.rowCount()
        tabela.insertRow(r)
        fonte = QFont()
        fonte.setBold(True)
        for col, texto in enumerate(valores):
            it = QTableWidgetItem(texto)
            it.setFont(fonte)
            if col > 0:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                    Qt.AlignmentFlag.AlignVCenter)
            tabela.setItem(r, col, it)

    def refrescar(self):
        self._recarregar_filtros()
        filtros = self._filtros()
        resumo = self.repo.resumo_mensal(filtros)
        lancs = self.repo.listar_lancamentos(filtros)

        # --- resumo mensal ---
        t = self.tabela_mensal
        t.setRowCount(0)
        tot_ent = tot_sai = 0.0
        for r in resumo:
            tot_ent += r["entradas"]
            tot_sai += r["saidas"]
            resultado = r["entradas"] - r["saidas"]
            self._adicionar_linha(
                t, [fmt_mes_curto(r["mes"]), fmt_moeda(r["entradas"]),
                    fmt_moeda(r["saidas"]), fmt_moeda(resultado)],
                cor_por_col={3: VERDE if resultado >= 0 else VERMELHO},
                alinhar_direita=(1, 2, 3))
        if resumo:
            self._linha_total(t, ["Total", fmt_moeda(tot_ent),
                                  fmt_moeda(tot_sai),
                                  fmt_moeda(tot_ent - tot_sai)])

        # --- consolidação por categoria ---
        agg = {}
        for l in lancs:
            ent, sai = agg.get(l.categoria_nome, (0.0, 0.0))
            if l.tipo == "entrada":
                ent += l.valor
            else:
                sai += l.valor
            agg[l.categoria_nome] = (ent, sai)
        t2 = self.tabela_cat
        t2.setRowCount(0)
        tot_ent, tot_sai = 0.0, 0.0
        for nome, (ent, sai) in sorted(agg.items(),
                                       key=lambda kv: -(kv[1][0] + kv[1][1])):
            tot_ent += ent
            tot_sai += sai
            resultado = ent - sai
            self._adicionar_linha(
                t2, [nome, fmt_moeda(ent), fmt_moeda(sai),
                     fmt_moeda(resultado)],
                cor_por_col={3: VERDE if resultado >= 0 else VERMELHO},
                alinhar_direita=(1, 2, 3))
        if agg:
            self._linha_total(t2, ["Total", fmt_moeda(tot_ent),
                                   fmt_moeda(tot_sai),
                                   fmt_moeda(tot_ent - tot_sai)])


class PaginaUsuarios(PaginaBase):
    """Painel administrativo de cadastros — visível apenas para admins.

    O admin gerencia contas de acesso (ativar/desativar, papel, senha,
    exclusão), mas NÃO acessa dados financeiros de nenhum usuário:
    o repositório financeiro é sempre user-scoped, inclusive para admins.
    """

    def __init__(self, repo_usuarios, sessao):
        super().__init__(repo_usuarios)
        self.repo_usuarios = repo_usuarios
        self.sessao = sessao

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Novo usuário")
        bt_novo.setProperty("variacao", "primaria")
        bt_papel = QPushButton("Promover/Rebaixar")
        bt_senha = QPushButton("Resetar senha")
        bt_ativo = QPushButton("Ativar/Desativar")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")
        bt_atualizar = QPushButton("Atualizar")

        topo = QHBoxLayout()
        t = QLabel("Usuários")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_papel)
        topo.addWidget(bt_senha)
        topo.addWidget(bt_ativo)
        topo.addWidget(bt_excluir)
        topo.addStretch()
        topo.addWidget(bt_atualizar)
        raiz.addLayout(topo)

        nota = QLabel("Este painel gerencia apenas os cadastros de acesso. "
                      "Por privacidade, nenhum usuário — nem admin — acessa "
                      "dados financeiros de outro usuário.")
        nota.setObjectName("tituloCard")
        nota.setWordWrap(True)
        raiz.addWidget(nota)

        self.tabela = self._montar_tabela(
            ["ID", "Nome", "E-mail", "Papel", "Plano", "Lançamentos",
             "Status", "Criado em"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_papel.clicked.connect(self._alternar_papel)
        bt_senha.clicked.connect(self._resetar_senha)
        bt_ativo.clicked.connect(self._alternar_ativo)
        bt_excluir.clicked.connect(self._excluir)
        bt_atualizar.clicked.connect(self.refrescar)
        self._linhas = []
        self.refrescar()

    @staticmethod
    def _fmt_criado(valor):
        if not valor:
            return "—"
        texto = str(valor)
        return fmt_data(texto[:10]) if len(texto) >= 10 else texto

    def refrescar(self):
        try:
            self._linhas = self.repo_usuarios.listar_usuarios()
        except Exception as e:
            self._exibir_erro(e)
            self._linhas = []
        t = self.tabela
        t.setRowCount(0)
        for u in self._linhas:
            cor_por_col = {3: VERDE if u.papel == "admin" else None}
            if not u.ativo:
                cor_por_col[2] = CINZA
                cor_por_col[6] = CINZA
            self._adicionar_linha(
                t,
                [str(u.id), u.nome, u.email,
                 "Admin" if u.papel == "admin" else "Usuário",
                 u.plano, str(u.total_lancamentos),
                 "Ativa" if u.ativo else "Inativa",
                 self._fmt_criado(u.criado_em)],
                cor_por_col=cor_por_col)

    def _selecionado(self):
        i = self.tabela.currentRow()
        if i < 0 or i >= len(self._linhas):
            QMessageBox.information(
                self, "Atenção", "Selecione um usuário na tabela.")
            return None
        return self._linhas[i]

    def _novo(self):
        dlg = DialogoNovoUsuario(self)
        if dlg.exec():
            nome, email, senha = dlg.dados()
            try:
                usuario = self.repo_usuarios.criar_usuario(nome, email, senha)
            except ErroRegraNegocio as e:
                QMessageBox.warning(self, "Não foi possível cadastrar", str(e))
                return
            except Exception as e:
                self._exibir_erro(e)
                return
            QMessageBox.information(
                self, "Usuário cadastrado",
                f"{usuario.nome} foi cadastrado como usuário comum e recebeu "
                "as 11 categorias padrão. Use 'Promover/Rebaixar' para torná-lo admin.")
            self.refrescar()

    def _alternar_papel(self):
        u = self._selecionado()
        if not u:
            return
        novo_papel = "usuario" if u.papel == "admin" else "admin"
        acao = "rebaixar para usuário comum" if novo_papel == "usuario" \
            else "promover a administrador"
        if not self._confirmar(
                "Alterar papel",
                f"{acao} o usuário '{u.nome}' ({u.email})?"):
            return
        try:
            self.repo_usuarios.definir_papel(
                u.id, novo_papel, self.sessao.usuario_id)
            self.refrescar()
        except ErroRegraNegocio as e:
            QMessageBox.warning(self, "Operação bloqueada", str(e))
        except Exception as e:
            self._exibir_erro(e)

    def _resetar_senha(self):
        u = self._selecionado()
        if not u:
            return
        dlg = DialogoNovaSenha(u.nome, self)
        if dlg.exec():
            try:
                self.repo_usuarios.resetar_senha(u.id, dlg.dados())
            except ErroRegraNegocio as e:
                QMessageBox.warning(self, "Senha não alterada", str(e))
                return
            except Exception as e:
                self._exibir_erro(e)
                return
            QMessageBox.information(
                self, "Senha alterada",
                f"A senha de {u.nome} foi redefinida com sucesso.")

    def _alternar_ativo(self):
        u = self._selecionado()
        if not u:
            return
        acao = "desativar" if u.ativo else "reativar"
        if not self._confirmar(
                "Alterar status",
                f"{acao} a conta de '{u.nome}' ({u.email})?\n\n"
                ("O usuário não poderá mais fazer login até ser reativado."
                 if u.ativo else "O usuário voltará a poder fazer login normalmente.")):
            return
        try:
            novo = self.repo_usuarios.alternar_ativo(
                u.id, self.sessao.usuario_id)
            self.refrescar()
            QMessageBox.information(
                self, "Status alterado",
                f"Conta de {u.nome} {'ativada' if novo else 'desativada'}.")
        except ErroRegraNegocio as e:
            QMessageBox.warning(self, "Operação bloqueada", str(e))
        except Exception as e:
            self._exibir_erro(e)

    def _excluir(self):
        u = self._selecionado()
        if not u:
            return
        if not self._confirmar(
                "Excluir usuário",
                f"Excluir PERMANENTEMENTE o usuário '{u.nome}' ({u.email})?\n\n"
                "Serão excluídos também TODOS os dados dele: lançamentos, "
                "recorrências, contas e categorias. Essa ação não pode ser desfeita."):
            return
        try:
            self.repo_usuarios.excluir_usuario(u.id, self.sessao.usuario_id)
            self.refrescar()
            QMessageBox.information(
                self, "Usuário excluído",
                f"{u.nome} e todos os seus dados foram excluídos.")
        except ErroRegraNegocio as e:
            QMessageBox.warning(self, "Operação bloqueada", str(e))
        except Exception as e:
            self._exibir_erro(e)
