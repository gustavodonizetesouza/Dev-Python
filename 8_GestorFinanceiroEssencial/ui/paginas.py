"""Páginas do aplicativo: Dashboard, Lançamentos, Contas, Categorias,
Recorrências, Cartões, Relatórios e Usuários (painel do admin).

Dashboard separa REALIZADO (pagos) de PREVISÃO (pendências + faturas de
cartão em aberto). Lançamentos suportam seleção múltipla com baixa em
lote. Recorrências v2 com progresso. Cartões: layout de contexto —
filtros no topo, tabela de cartões como painel de resumo (a soma por
cartão fica nas colunas 'Em aberto' e 'Disponível') e UM grid detalhado
com as compras do cartão filtrado. 'Pagar fatura' abre direto quando só
há 1 fatura em aberto e mostra seletor quando há várias.
"""
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (QComboBox, QDateEdit, QFrame, QGridLayout,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                             QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from core.util import (avancar_mes, dias_no_mes, fmt_data, fmt_mes_curto,
                       fmt_moeda, mes_anterior, nome_mes)
from dominio.repositorio import ErroRegraNegocio, Repositorio
from ui.dialogos import (DialogoCategoria, DialogoCompra, DialogoConta,
                         DialogoCartao, DialogoLancamento, DialogoNovaSenha,
                         DialogoNovoUsuario, DialogoPagarFatura,
                         DialogoRecorrencia)
from ui.graficos import GraficoBarras, GraficoPizza

VERDE, VERMELHO, AMBAR, CINZA = "#43a047", "#e53935", "#ff9800", "#9aa0a6"

ROTULOS_FREQUENCIA = {"mensal": "Mensal", "semanal": "Semanal",
                      "trimestral": "Trimestral", "anual": "Anual"}


def _estilo_valor(cor: str) -> str:
    return f"font-size: 20px; font-weight: 700; color: {cor};"


def _fim_do_mes(qdate: QDate) -> QDate:
    """Último dia do mês da data informada (para o filtro 'Até')."""
    return QDate(qdate.year(), qdate.month(),
                 dias_no_mes(qdate.year(), qdate.month()))


class PaginaBase(QWidget):
    """Base comum às páginas: referência ao repositório e helpers de UI."""

    dados_alterados = pyqtSignal()

    def __init__(self, repo):
        super().__init__()
        self.repo = repo

    def refrescar(self):
        pass

    # ---------- helpers ----------
    def _montar_tabela(self, colunas, multi_selecao=False):
        t = QTableWidget()
        t.setColumnCount(len(colunas))
        t.setHorizontalHeaderLabels(colunas)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        if multi_selecao:
            t.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        else:
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
    """KPIs separados em REALIZADO (pagos) e PREVISÃO (pendências + faturas)."""

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
        _criar_card("faturas", "Faturas a pagar (mês)", linha_prev)
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

        self.cards["previsto"].setText(fmt_moeda(k.saldo_previsto))
        self.cards["previsto"].setStyleSheet(
            _estilo_valor(VERDE if k.saldo_previsto >= 0 else VERMELHO))
        self.cards["a_receber"].setText(fmt_moeda(k.a_receber_mes))
        self.cards["a_receber"].setStyleSheet(_estilo_valor(VERDE))
        self.cards["a_pagar"].setText(fmt_moeda(k.a_pagar_mes))
        self.cards["a_pagar"].setStyleSheet(_estilo_valor(VERMELHO))
        self.cards["faturas"].setText(fmt_moeda(k.faturas_mes))
        self.cards["faturas"].setStyleSheet(
            _estilo_valor(AMBAR if k.faturas_mes else CINZA))
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
    """Entradas e saídas com filtros, baixa em lote e alternância de 1 clique."""

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        bt_novo = QPushButton("Novo lançamento")
        bt_novo.setProperty("variacao", "primaria")
        bt_editar = QPushButton("Editar")
        bt_baixar = QPushButton("Baixar selecionados")
        bt_baixar.setProperty("variacao", "sucesso")
        bt_pago = QPushButton("Marcar pago/pendente")
        bt_excluir = QPushButton("Excluir")
        bt_excluir.setProperty("variacao", "perigo")
        bt_atualizar = QPushButton("Atualizar")

        topo = QHBoxLayout()
        t = QLabel("Lançamentos")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        topo.addWidget(bt_novo)
        topo.addWidget(bt_editar)
        topo.addWidget(bt_baixar)
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
        self.dt_fim = QDateEdit(_fim_do_mes(hoje))
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
            ["Data", "Descrição", "Conta", "Categoria", "Tipo", "Valor", "Status"],
            multi_selecao=True)
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_baixar.clicked.connect(self._baixar_lote)
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

    def _linhas_selecionadas(self):
        return [self._linhas[i] for i in sorted({idx.row() for idx in
                                                 self.tabela.selectedIndexes()})
                if 0 <= i < len(self._linhas)]

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

    def _baixar_lote(self):
        selecionadas = self._linhas_selecionadas()
        pendentes = [l for l in selecionadas if not l.pago]
        if not pendentes:
            QMessageBox.information(
                self, "Baixa em lote",
                "Selecione ao menos um lançamento PENDENTE para baixar "
                "(já pagos são ignorados).")
            return
        total = sum(l.valor for l in pendentes if l.tipo == "saida")
        total += sum(l.valor for l in pendentes if l.tipo == "entrada")
        if not self._confirmar(
                "Baixa em lote",
                f"Marcar como PAGO/RECEBIDO o(s) {len(pendentes)} lançamento(s) "
                f"selecionado(s)?\n\nValor total envolvido: {fmt_moeda(total)}\n\n"
                "Se houver parcelas de recorrência, a próxima ocorrência de "
                "cada uma será gerada automaticamente."):
            return
        try:
            baixados, ignorados = self.repo.baixar_em_lote(
                [l.id for l in pendentes])
        except Exception as e:
            self._exibir_erro(e)
            return
        self.dados_alterados.emit()
        self.refrescar()
        QMessageBox.information(
            self, "Baixa em lote",
            f"{baixados} lançamento(s) baixado(s)."
            + (f"\n{ignorados} já pago(s) ignorado(s)." if ignorados else ""))

    def _alternar_pago(self):
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
    """Cadastro de contas/carteiras — saldo atual considera apenas pagos."""

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
    """Contas fixas v2 com progresso e ciclo automático na baixa."""

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
            ["Descrição", "Conta", "Categoria", "Tipo", "Valor", "Frequência",
             "1ª ocorrência", "Próxima", "Término", "Progresso", "Status"])
        raiz.addWidget(self.tabela, 1)

        bt_novo.clicked.connect(self._novo)
        bt_editar.clicked.connect(self._editar)
        bt_excluir.clicked.connect(self._excluir)
        bt_gerar.clicked.connect(self._gerar)
        self.tabela.cellDoubleClicked.connect(lambda *_: self._editar())
        self._linhas = []
        self.refrescar()

    @staticmethod
    def _fmt_termino(r):
        if r.data_fim:
            return fmt_data(r.data_fim)
        if r.qtd_vezes is not None:
            return f"{r.qtd_vezes}x"
        return "Sem fim"

    @staticmethod
    def _fmt_progresso(r, prog):
        if not prog:
            return "—"
        texto = f"{prog['geradas']} geradas · {prog['pagas']} paga(s)"
        if prog["restantes"] is not None:
            texto += f" · {prog['restantes']} restantes"
        return texto

    def refrescar(self):
        self._linhas = self.repo.listar_recorrencias()
        progresso = self.repo.progresso_recorrencias()
        t = self.tabela
        t.setRowCount(0)
        for r in self._linhas:
            cor = VERDE if r.tipo == "entrada" else VERMELHO
            if r.concluida:
                status, cor_status = "Concluída", CINZA
            else:
                status = "Ativa" if r.ativo else "Inativa"
                cor_status = None if r.ativo else CINZA
            prog = progresso.get(r.id)
            cor_prog = AMBAR if (prog and prog["restantes"] == 0
                                 and not r.concluida) else None
            self._adicionar_linha(
                t,
                [r.descricao, r.conta_nome, r.categoria_nome,
                 "Entrada" if r.tipo == "entrada" else "Saída",
                 fmt_moeda(r.valor),
                 ROTULOS_FREQUENCIA.get(r.frequencia, r.frequencia),
                 fmt_data(r.data_inicio) if r.data_inicio else "—",
                 fmt_data(r.proxima_data) if (
                     r.proxima_data and not r.concluida) else "—",
                 self._fmt_termino(r),
                 self._fmt_progresso(r, prog),
                 status],
                cor_por_col={4: cor, 9: cor_prog, 10: cor_status},
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
        msg = (f"{gerados} lançamento(s) gerado(s).\n\n"
               "A geração cria as ocorrências já vencidas até hoje e, quando "
               "houver, a PRÓXIMA parcela a vencer. Os lançamentos gerados "
               "nascem como PENDENTES — marque-os como pagos em Lançamentos "
               "quando efetivar (a baixa também gera a próxima automaticamente).")
        if puladas:
            msg += "\n\nNão puderam ser geradas: " + ", ".join(puladas)
        if gerados:
            self.dados_alterados.emit()
        self.refrescar()
        QMessageBox.information(self, "Recorrências", msg)


class PaginaCartoes(PaginaBase):
    """Controle do cartão de crédito — layout de contexto em 3 zonas.

    1. Ações (cartões à esquerda; compra/fatura à direita).
    2. Filtros no topo (cartão, fatura, status).
    3. Tabela de cartões = painel de resumo: a SOMA por cartão fica nas
       colunas 'Em aberto' e 'Disponível' (não há grid de faturas — o
       resumo é o cadastro do cartão). Clicar num cartão sincroniza o
       filtro e refiltra as compras abaixo (guard anti-loop).
    4. Grid único de compras do cartão filtrado, com título dinâmico.
       'Pagar fatura': 1 fatura em aberto abre direto; várias → seletor.
    """

    def __init__(self, repo):
        super().__init__(repo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(10)

        # ---------- zona 1: ações ----------
        topo = QHBoxLayout()
        t = QLabel("Cartões de crédito")
        t.setObjectName("tituloPagina")
        topo.addWidget(t)
        bt_cartao = QPushButton("Novo cartão")
        bt_cartao.setProperty("variacao", "primaria")
        bt_editar_cartao = QPushButton("Editar cartão")
        bt_excluir_cartao = QPushButton("Excluir cartão")
        bt_excluir_cartao.setProperty("variacao", "perigo")
        topo.addWidget(bt_cartao)
        topo.addWidget(bt_editar_cartao)
        topo.addWidget(bt_excluir_cartao)
        topo.addStretch()
        bt_compra = QPushButton("Nova compra")
        bt_compra.setProperty("variacao", "primaria")
        bt_excluir_compra = QPushButton("Excluir compra pendente")
        bt_excluir_compra.setProperty("variacao", "perigo")
        bt_pagar = QPushButton("Pagar fatura")
        bt_pagar.setProperty("variacao", "sucesso")
        topo.addWidget(bt_compra)
        topo.addWidget(bt_excluir_compra)
        topo.addWidget(bt_pagar)
        raiz.addLayout(topo)

        # ---------- zona 2: filtros no topo ----------
        card_f = QFrame()
        card_f.setObjectName("card")
        lf = QHBoxLayout(card_f)
        lf.setContentsMargins(12, 8, 12, 8)
        lf.setSpacing(6)
        lf.addWidget(QLabel("Cartão"))
        self.cb_cartao_f = QComboBox()
        lf.addWidget(self.cb_cartao_f)
        lf.addWidget(QLabel("Fatura"))
        self.cb_fatura_f = QComboBox()
        lf.addWidget(self.cb_fatura_f)
        lf.addWidget(QLabel("Status"))
        self.cb_status_f = QComboBox()
        self.cb_status_f.addItem("Todos", None)
        self.cb_status_f.addItem("Em aberto", 0)
        self.cb_status_f.addItem("Pagos", 1)
        lf.addWidget(self.cb_status_f)
        lf.addStretch()
        raiz.addWidget(card_f)

        # ---------- zona 3: cartões cadastrados (painel de resumo) ----------
        self.tabela_cartoes = self._montar_tabela(
            ["Cartão", "Conta de débito", "Fechamento", "Vencimento",
             "Limite", "Em aberto", "Disponível", "Status"])
        raiz.addWidget(self.tabela_cartoes)

        # ---------- zona 4: compras do cartão filtrado (grid único) ----------
        self.lb_compras = QLabel("Compras")
        self.lb_compras.setObjectName("tituloCard")
        raiz.addWidget(self.lb_compras)
        self.tabela_compras = self._montar_tabela(
            ["Fatura", "Vencimento", "Descrição", "Cartão", "Categoria",
             "Parcela", "Valor", "Status"])
        raiz.addWidget(self.tabela_compras, 1)

        bt_cartao.clicked.connect(self._novo_cartao)
        bt_editar_cartao.clicked.connect(self._editar_cartao)
        bt_excluir_cartao.clicked.connect(self._excluir_cartao)
        bt_compra.clicked.connect(self._nova_compra)
        bt_excluir_compra.clicked.connect(self._excluir_compra)
        bt_pagar.clicked.connect(self._pagar_fatura)
        self.tabela_cartoes.itemSelectionChanged.connect(
            self._ao_selecionar_cartao)
        self.cb_cartao_f.currentIndexChanged.connect(self.refrescar)
        self.cb_fatura_f.currentIndexChanged.connect(self.refrescar)
        self.cb_status_f.currentIndexChanged.connect(self.refrescar)

        self._cartoes = []
        self._compras = []
        self._sincronizando = False   # guard anti-loop (seleção <-> filtro)
        self.refrescar()

    # ---------- cartões ----------
    def _cartao_selecionado(self):
        i = self.tabela_cartoes.currentRow()
        if 0 <= i < len(self._cartoes):
            return self._cartoes[i]
        return None

    def _ao_selecionar_cartao(self):
        """Clique na tabela de cartões sincroniza o filtro e refiltra tudo."""
        if self._sincronizando:
            return
        c = self._cartao_selecionado()
        novo_id = c.id if c else None
        if self.cb_cartao_f.currentData() != novo_id:
            self.cb_cartao_f.blockSignals(True)
            self.cb_cartao_f.setCurrentIndex(
                max(0, self.cb_cartao_f.findData(novo_id)))
            self.cb_cartao_f.blockSignals(False)
            self.refrescar()

    def _cartao_filtrado(self):
        sel_id = self.cb_cartao_f.currentData()
        if sel_id is not None:
            for c in self._cartoes:
                if c.id == sel_id:
                    return c
        return None

    def _cartao_para_compra(self):
        """Cartão para a nova compra: seleção na tabela, senão o do filtro,
        senão o primeiro ativo."""
        c = self._cartao_selecionado() or self._cartao_filtrado()
        if c:
            return c
        ativos = [c for c in self._cartoes if c.ativo]
        return ativos[0] if ativos else None

    def _novo_cartao(self):
        dlg = DialogoCartao(self.repo, None, self)
        if dlg.exec():
            self.repo.salvar_cartao(**dlg.dados())
            self.dados_alterados.emit()
            self.refrescar()

    def _editar_cartao(self):
        c = self._cartao_selecionado()
        if not c:
            QMessageBox.information(
                self, "Atenção", "Selecione um cartão na tabela.")
            return
        dlg = DialogoCartao(self.repo, c, self)
        if dlg.exec():
            self.repo.salvar_cartao(**dlg.dados(), id=c.id)
            self.dados_alterados.emit()
            self.refrescar()

    def _excluir_cartao(self):
        c = self._cartao_selecionado()
        if not c:
            QMessageBox.information(
                self, "Atenção", "Selecione um cartão na tabela.")
            return
        if not self._confirmar(
                "Excluir cartão",
                f"Excluir o cartão '{c.nome}'?\n\n"
                "O histórico pago das faturas permanece nos lançamentos."):
            return
        try:
            self.repo.excluir_cartao(c.id)
            self.dados_alterados.emit()
            self.refrescar()
        except ErroRegraNegocio as e:
            QMessageBox.warning(self, "Cartão com pendências", str(e))
        except Exception as e:
            self._exibir_erro(e)

    # ---------- compras ----------
    def _nova_compra(self):
        cartao = self._cartao_para_compra()
        if not cartao:
            QMessageBox.information(self, "Atenção",
                                    "Cadastre um cartão ativo antes de lançar compras.")
            return
        dlg = DialogoCompra(self.repo, cartao, self)
        if dlg.exec():
            try:
                n = self.repo.criar_compra(**dlg.dados())
                self.dados_alterados.emit()
                self.refrescar()
                QMessageBox.information(
                    self, "Compra registrada",
                    f"{n} parcela(s) gravada(s). Elas aparecem nas faturas "
                    "como débito previsto — o caixa só se move no pagamento "
                    "da fatura.")
            except ErroRegraNegocio as e:
                QMessageBox.warning(self, "Não foi possível registrar", str(e))
            except Exception as e:
                self._exibir_erro(e)

    def _excluir_compra(self):
        i = self.tabela_compras.currentRow()
        if i < 0 or i >= len(self._compras):
            QMessageBox.information(
                self, "Atenção", "Selecione uma parcela na tabela.")
            return
        compra = self._compras[i]
        if compra.pago:
            QMessageBox.information(
                self, "Compra paga",
                "Esta parcela já foi paga (fatura quitada) — histórico "
                "imutável. Exclua apenas parcelas em aberto.")
            return
        if not self._confirmar(
                "Excluir compra",
                f"Excluir TODAS as parcelas em aberto de "
                f"'{compra.descricao or 'compra sem descrição'}' "
                f"(a partir da {compra.parcela}/{compra.total_parcelas})?\n\n"
                "Parcelas já pagas permanecem no histórico."):
            return
        try:
            n = self.repo.excluir_compra(compra.grupo_id)
            self.dados_alterados.emit()
            self.refrescar()
            QMessageBox.information(self, "Compra excluída",
                                    f"{n} parcela(s) em aberto excluída(s).")
        except Exception as e:
            self._exibir_erro(e)

    # ---------- faturas ----------
    def _pagar_fatura(self):
        """Pagamento da fatura no escopo do filtro atual.

        1 fatura em aberto → abre o diálogo direto; várias → seletor
        nativo (a mais antiga vem por padrão).
        """
        sel_id = self.cb_cartao_f.currentData()
        faturas = self.repo.resumo_faturas(cartao_id=sel_id)
        if not faturas:
            QMessageBox.information(
                self, "Pagar fatura",
                "Nenhuma fatura com saldo em aberto"
                + (" para o cartão filtrado." if sel_id is not None else "."))
            return
        if len(faturas) == 1:
            fatura_info = faturas[0]
        else:
            opcoes = [f"{fmt_mes_curto(f['fatura'])} — {f['cartao_nome']}"
                      f" · {fmt_moeda(f['total'])}" for f in faturas]
            escolha, ok = QInputDialog.getItem(
                self, "Pagar fatura",
                "Escolha a fatura (mais antigas primeiro):",
                opcoes, 0, False)
            if not ok:
                return
            fatura_info = faturas[opcoes.index(escolha)]
        dlg = DialogoPagarFatura(self.repo, fatura_info, self)
        if dlg.exec():
            try:
                lanc_id, total, qtde = self.repo.pagar_fatura(**dlg.dados())
            except ErroRegraNegocio as e:
                QMessageBox.warning(self, "Não foi possível pagar", str(e))
                return
            except Exception as e:
                self._exibir_erro(e)
                return
            self.dados_alterados.emit()
            self.refrescar()
            QMessageBox.information(
                self, "Fatura paga",
                f"Lançamento de saída de {fmt_moeda(total)} gerado — "
                f"{qtde} parcela(s) quitada(s).")

    # ---------- refresh ----------
    def _recarregar_filtros(self):
        sel_cartao = self.cb_cartao_f.currentData()
        sel_fatura = self.cb_fatura_f.currentData()
        self.cb_cartao_f.blockSignals(True)
        self.cb_fatura_f.blockSignals(True)
        self.cb_cartao_f.clear()
        self.cb_cartao_f.addItem("Todos os cartões", None)
        for c in self._cartoes:
            self.cb_cartao_f.addItem(c.nome, c.id)
        self.cb_cartao_f.setCurrentIndex(
            max(0, self.cb_cartao_f.findData(sel_cartao)))
        self.cb_fatura_f.clear()
        self.cb_fatura_f.addItem("Todas as faturas", None)
        for f in self.repo.resumo_faturas(cartao_id=sel_cartao):
            rotulo = f"{fmt_mes_curto(f['fatura'])} — {f['cartao_nome']}"
            self.cb_fatura_f.addItem(rotulo, f["fatura"])
        self.cb_fatura_f.setCurrentIndex(
            max(0, self.cb_fatura_f.findData(sel_fatura)))
        self.cb_cartao_f.blockSignals(False)
        self.cb_fatura_f.blockSignals(False)

    def refrescar(self):
        self._cartoes = self.repo.listar_cartoes()
        sel_id = self.cb_cartao_f.currentData()
        cartao_filtrado = self._cartao_filtrado()
        nome_filtro = cartao_filtrado.nome if cartao_filtrado else "todos os cartões"
        self._recarregar_filtros()

        self._sincronizando = True
        try:
            # --- zona 3: cartões + restaurar seleção do filtro ---
            t = self.tabela_cartoes
            t.setRowCount(0)
            linha_sel = -1
            for idx, c in enumerate(self._cartoes):
                cor_disp = VERDE if c.limite_disponivel >= 0 else VERMELHO
                self._adicionar_linha(
                    t,
                    [c.nome, c.conta_nome, f"dia {c.dia_fechamento}",
                     f"dia {c.dia_vencimento}", fmt_moeda(c.limite_total),
                     fmt_moeda(c.total_aberto), fmt_moeda(c.limite_disponivel),
                     "Ativo" if c.ativo else "Inativo"],
                    cor_por_col={6: cor_disp},
                    alinhar_direita=(4, 5, 6))
                if c.id == sel_id:
                    linha_sel = idx
            if linha_sel >= 0:
                t.selectRow(linha_sel)

            # --- zona 4: compras do cartão filtrado (grid único) ---
            self.lb_compras.setText(f"Compras — {nome_filtro}")
            self._compras = self.repo.listar_compras(dict(
                cartao_id=sel_id,
                fatura=self.cb_fatura_f.currentData(),
                pago=self.cb_status_f.currentData()))
            t2 = self.tabela_compras
            t2.setRowCount(0)
            for p in self._compras:
                pago = bool(p.pago)
                cor_status = VERDE if pago else AMBAR
                parcela_txt = (f"{p.parcela}/{p.total_parcelas}"
                               if p.total_parcelas > 1 else "—")
                self._adicionar_linha(
                    t2,
                    [fmt_mes_curto(p.fatura),
                     fmt_data(Repositorio.vencimento_de_fatura(
                         p.fatura, next((c.dia_vencimento for c in self._cartoes
                                         if c.id == p.cartao_id), 10))),
                     p.descricao or "—", p.cartao_nome, p.categoria_nome,
                     parcela_txt, fmt_moeda(p.valor),
                     "Paga" if pago else "Em aberto"],
                    cor_por_col={6: VERMELHO, 7: cor_status},
                    alinhar_direita=(6,))
        finally:
            self._sincronizando = False


class PaginaRelatorios(PaginaBase):
    """Relatórios por período: resumo mensal e consolidação por categoria."""

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
        self.dt_fim = QDateEdit(_fim_do_mes(hoje))
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
        fonte = tabela.font()
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
    """Painel administrativo de cadastros — visível apenas para admins."""

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
        detalhe = ("O usuário não poderá mais fazer login até ser reativado."
                   if u.ativo else
                   "O usuário voltará a poder fazer login normalmente.")
        if not self._confirmar(
                "Alterar status",
                f"{acao} a conta de '{u.nome}' ({u.email})?\n\n{detalhe}"):
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
                "recorrências, contas, cartões e categorias. Essa ação não "
                "pode ser desfeita."):
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
