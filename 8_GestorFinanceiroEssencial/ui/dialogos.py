"""Diálogos de cadastro: contas, categorias, lançamentos, recorrências,
cartão de crédito e usuários.

DialogoRecorrencia (v2): frequência, primeira ocorrência e término por
data ou quantidade. DialogoCartao/DialogoCompra/DialogoPagarFatura: o
ciclo do cartão — o diálogo de compra mostra a FATURA CALCULADA pela regra
do fechamento (editável para casos excepcionais) e a progressão das
parcelas; o pagamento da fatura gera UM lançamento de saída na conta.
"""
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDateEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QRadioButton, QSpinBox,
                             QVBoxLayout, QWidget)

from core.seguranca import validar_senha_forte
from core.util import fmt_data, fmt_mes_curto, fmt_moeda
from dominio.repositorio import Repositorio

TIPOS_CONTA = ["Corrente", "Poupança", "Cartão", "Dinheiro", "Investimento"]

FREQUENCIAS = [("Mensal", "mensal"), ("Semanal", "semanal"),
               ("Trimestral", "trimestral"), ("Anual", "anual")]


class DialogoBase(QDialog):
    """Base com formulário, aviso de validação e botões Salvar/Cancelar."""

    def __init__(self, titulo: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(430)
        raiz = QVBoxLayout(self)
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        raiz.addLayout(self.form)
        self.aviso = QLabel("")
        self.aviso.setObjectName("aviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        raiz.addWidget(self.aviso)
        self.botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel)
        self.botoes.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
        self.botoes.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.botoes.accepted.connect(self._tentar_aceitar)
        self.botoes.rejected.connect(self.reject)
        raiz.addWidget(self.botoes)

    def _tentar_aceitar(self):
        erro = self.validar()
        if erro:
            self.aviso.setText(erro)
            self.aviso.show()
        else:
            self.accept()

    def validar(self):
        """Retorna mensagem de erro ou None se o formulário está válido."""
        return None

    @staticmethod
    def _spin_moeda(minimo=0.01):
        sp = QDoubleSpinBox()
        sp.setRange(minimo, 999_999_999.99)
        sp.setDecimals(2)
        sp.setGroupSeparatorShown(True)
        sp.setPrefix("R$ ")
        return sp

    @staticmethod
    def _email_valido(email: str) -> bool:
        return "@" in (email or "") and "." in email.split("@")[-1]


class DialogoConta(DialogoBase):
    def __init__(self, repo: Repositorio, conta=None, parent=None):
        super().__init__("Editar conta" if conta else "Nova conta", parent)
        self.repo = repo
        self.conta = conta

        self.ed_nome = QLineEdit()
        self.ed_nome.setMaxLength(120)
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItems(TIPOS_CONTA)
        self.sp_saldo = DialogoBase._spin_moeda(minimo=-999_999_999.99)
        self.sp_saldo.setPrefix("")
        self.ck_ativo = QCheckBox("Conta ativa")
        self.ck_ativo.setChecked(True)

        self.form.addRow("Nome*", self.ed_nome)
        self.form.addRow("Tipo", self.cb_tipo)
        self.form.addRow("Saldo inicial", self.sp_saldo)
        self.form.addRow("", self.ck_ativo)

        if conta:
            self.ed_nome.setText(conta.nome)
            self.cb_tipo.setCurrentText(conta.tipo)
            self.sp_saldo.setValue(conta.saldo_inicial)
            self.ck_ativo.setChecked(bool(conta.ativo))

    def validar(self):
        if not self.ed_nome.text().strip():
            return "Informe o nome da conta."
        return None

    def dados(self):
        return dict(nome=self.ed_nome.text().strip(), tipo=self.cb_tipo.currentText(),
                    saldo_inicial=self.sp_saldo.value(),
                    ativo=1 if self.ck_ativo.isChecked() else 0)


class DialogoCategoria(DialogoBase):
    def __init__(self, repo: Repositorio, categoria=None, parent=None):
        super().__init__("Editar categoria" if categoria else "Nova categoria", parent)
        self.repo = repo
        self.categoria = categoria
        self.cor = "#607d8b"

        self.ed_nome = QLineEdit()
        self.ed_nome.setMaxLength(120)
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItem("Saída", "saida")
        self.cb_tipo.addItem("Entrada", "entrada")
        self.bt_cor = QPushButton(self.cor)
        self.bt_cor.clicked.connect(self._escolher_cor)
        self.ck_ativo = QCheckBox("Categoria ativa")
        self.ck_ativo.setChecked(True)

        self.form.addRow("Nome*", self.ed_nome)
        self.form.addRow("Tipo", self.cb_tipo)
        self.form.addRow("Cor", self.bt_cor)
        self.form.addRow("", self.ck_ativo)

        if categoria:
            self.ed_nome.setText(categoria.nome)
            self.cb_tipo.setCurrentIndex(1 if categoria.tipo == "entrada" else 0)
            self.cor = categoria.cor or self.cor
            self.ck_ativo.setChecked(bool(categoria.ativo))
        self._pintar_botao_cor()

    def _escolher_cor(self):
        c = QColorDialog.getColor(QColor(self.cor), self, "Cor da categoria")
        if c.isValid():
            self.cor = c.name()
            self._pintar_botao_cor()

    def _pintar_botao_cor(self):
        self.bt_cor.setText(self.cor)
        self.bt_cor.setStyleSheet(
            f"background-color: {self.cor}; color: #ffffff; font-weight: 700;")

    def validar(self):
        if not self.ed_nome.text().strip():
            return "Informe o nome da categoria."
        return None

    def dados(self):
        return dict(nome=self.ed_nome.text().strip(), tipo=self.cb_tipo.currentData(),
                    cor=self.cor, ativo=1 if self.ck_ativo.isChecked() else 0)


class DialogoLancamento(DialogoBase):
    """Lançamento com controle de contas a pagar/receber."""

    def __init__(self, repo: Repositorio, lancamento=None, parent=None):
        super().__init__("Editar lançamento" if lancamento else "Novo lançamento", parent)
        self.repo = repo
        self.lancamento = lancamento

        self.cb_tipo = QComboBox()
        self.cb_tipo.addItem("Saída", "saida")
        self.cb_tipo.addItem("Entrada", "entrada")
        self.cb_conta = QComboBox()
        for conta in repo.listar_contas():
            self.cb_conta.addItem(conta.nome, conta.id)
        self.cb_categoria = QComboBox()
        self.cb_valor = DialogoBase._spin_moeda()
        self.ed_data = QDateEdit(QDate.currentDate())
        self.ed_data.setDisplayFormat("dd/MM/yyyy")
        self.ed_data.setCalendarPopup(True)
        self.ed_descricao = QLineEdit()
        self.ed_descricao.setMaxLength(200)
        self.ck_pago = QCheckBox("Já pago")
        self.ck_pago.setChecked(True)

        self.form.addRow("Tipo", self.cb_tipo)
        self.form.addRow("Conta*", self.cb_conta)
        self.form.addRow("Categoria*", self.cb_categoria)
        self.form.addRow("Valor*", self.cb_valor)
        self.form.addRow("Data", self.ed_data)
        self.form.addRow("Descrição", self.ed_descricao)
        self.form.addRow("", self.ck_pago)

        self.cb_tipo.currentIndexChanged.connect(self._atualizar_texto_pago)
        self.cb_tipo.currentIndexChanged.connect(lambda _: self._recarregar_categorias())

        if lancamento:
            self.cb_tipo.setCurrentIndex(self.cb_tipo.findData(lancamento.tipo))
            self._recarregar_categorias(lancamento.categoria_id)
            self.cb_conta.setCurrentIndex(self.cb_conta.findData(lancamento.conta_id))
            self.cb_valor.setValue(lancamento.valor)
            a, m, d = (int(x) for x in lancamento.data_mov.split("-"))
            self.ed_data.setDate(QDate(a, m, d))
            self.ed_descricao.setText(lancamento.descricao)
            self.ck_pago.setChecked(bool(lancamento.pago))
        else:
            self._recarregar_categorias()
        self._atualizar_texto_pago()

    def _atualizar_texto_pago(self):
        if self.cb_tipo.currentData() == "entrada":
            self.ck_pago.setText("Já recebido")
        else:
            self.ck_pago.setText("Já pago")

    def _recarregar_categorias(self, manter_id=None):
        tipo = self.cb_tipo.currentData()
        self.cb_categoria.clear()
        for cat in self.repo.listar_categorias(tipo=tipo, apenas_ativas=True):
            self.cb_categoria.addItem(cat.nome, cat.id)
        if manter_id is not None:
            i = self.cb_categoria.findData(manter_id)
            if i >= 0:
                self.cb_categoria.setCurrentIndex(i)

    def validar(self):
        if self.cb_conta.currentData() is None:
            return "Cadastre uma conta antes de lançar."
        if self.cb_categoria.currentData() is None:
            return ("Cadastre uma categoria de entrada"
                    if self.cb_tipo.currentData() == "entrada"
                    else "Cadastre uma categoria de saída.")
        if self.cb_valor.value() <= 0:
            return "Informe um valor maior que zero."
        return None

    def dados(self):
        return dict(conta_id=self.cb_conta.currentData(),
                    categoria_id=self.cb_categoria.currentData(),
                    tipo=self.cb_tipo.currentData(), valor=self.cb_valor.value(),
                    data_mov=self.ed_data.date().toString("yyyy-MM-dd"),
                    descricao=self.ed_descricao.text().strip(),
                    pago=1 if self.ck_pago.isChecked() else 0)


class _LinhaTérmino(QWidget):
    """Linha do formulário com os 3 modos de término das recorrências."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.rb_sem_fim = QRadioButton("Sem fim")
        self.rb_data = QRadioButton("Até a data:")
        self.rb_qtd = QRadioButton("Por quantidade:")
        self.rb_sem_fim.setChecked(True)

        self.ed_data = QDateEdit(QDate.currentDate().addMonths(12))
        self.ed_data.setDisplayFormat("dd/MM/yyyy")
        self.ed_data.setCalendarPopup(True)

        self.sp_qtd = QSpinBox()
        self.sp_qtd.setRange(1, 999_999)
        self.sp_qtd.setValue(12)

        layout.addWidget(self.rb_sem_fim)
        layout.addWidget(self.rb_data)
        layout.addWidget(self.ed_data)
        layout.addWidget(self.rb_qtd)
        layout.addWidget(self.sp_qtd)
        layout.addStretch()

        self.rb_sem_fim.toggled.connect(self._atualizar_habilitados)
        self.rb_data.toggled.connect(self._atualizar_habilitados)
        self.rb_qtd.toggled.connect(self._atualizar_habilitados)
        self._atualizar_habilitados()

    def _atualizar_habilitados(self):
        self.ed_data.setEnabled(self.rb_data.isChecked())
        self.sp_qtd.setEnabled(self.rb_qtd.isChecked())


class DialogoRecorrencia(DialogoBase):
    """Recorrência v2: frequência + primeira ocorrência + término opcional."""

    def __init__(self, repo: Repositorio, recorrencia=None, parent=None):
        super().__init__("Editar recorrência" if recorrencia else "Nova recorrência", parent)
        self.repo = repo
        self.recorrencia = recorrencia

        self.ed_descricao = QLineEdit()
        self.ed_descricao.setMaxLength(160)
        self.cb_tipo = QComboBox()
        self.cb_tipo.addItem("Saída", "saida")
        self.cb_tipo.addItem("Entrada", "entrada")
        self.cb_conta = QComboBox()
        for conta in repo.listar_contas(apenas_ativas=True):
            self.cb_conta.addItem(conta.nome, conta.id)
        self.cb_categoria = QComboBox()
        self.sp_valor = DialogoBase._spin_moeda()

        self.cb_frequencia = QComboBox()
        for rotulo, valor in FREQUENCIAS:
            self.cb_frequencia.addItem(rotulo, valor)

        hoje = QDate.currentDate()
        self.ed_inicio = QDateEdit(hoje)
        self.ed_inicio.setDisplayFormat("dd/MM/yyyy")
        self.ed_inicio.setCalendarPopup(True)

        self.linha_termino = _LinhaTérmino()

        self.ck_ativo = QCheckBox("Recorrência ativa")
        self.ck_ativo.setChecked(True)

        self.form.addRow("Descrição*", self.ed_descricao)
        self.form.addRow("Tipo", self.cb_tipo)
        self.form.addRow("Conta*", self.cb_conta)
        self.form.addRow("Categoria*", self.cb_categoria)
        self.form.addRow("Valor*", self.sp_valor)
        self.form.addRow("Frequência", self.cb_frequencia)
        self.form.addRow("1ª ocorrência", self.ed_inicio)
        self.form.addRow("Término", self.linha_termino)
        self.form.addRow("", self.ck_ativo)

        self.cb_tipo.currentIndexChanged.connect(lambda _: self._recarregar_categorias())

        if recorrencia:
            self.ed_descricao.setText(recorrencia.descricao)
            self.cb_tipo.setCurrentIndex(self.cb_tipo.findData(recorrencia.tipo))
            self._recarregar_categorias(recorrencia.categoria_id)
            self.cb_conta.setCurrentIndex(self.cb_conta.findData(recorrencia.conta_id))
            self.sp_valor.setValue(recorrencia.valor)
            i = self.cb_frequencia.findData(recorrencia.frequencia)
            self.cb_frequencia.setCurrentIndex(max(0, i))
            if recorrencia.data_inicio:
                a, m, d = (int(x) for x in recorrencia.data_inicio[:10].split("-"))
                self.ed_inicio.setDate(QDate(a, m, d))
            if recorrencia.data_fim:
                a, m, d = (int(x) for x in recorrencia.data_fim[:10].split("-"))
                self.linha_termino.rb_data.setChecked(True)
                self.linha_termino.ed_data.setDate(QDate(a, m, d))
            elif recorrencia.qtd_vezes is not None:
                self.linha_termino.rb_qtd.setChecked(True)
                self.linha_termino.sp_qtd.setValue(recorrencia.qtd_vezes)
            self.ck_ativo.setChecked(bool(recorrencia.ativo))
        else:
            self._recarregar_categorias()

    def _recarregar_categorias(self, manter_id=None):
        tipo = self.cb_tipo.currentData()
        self.cb_categoria.clear()
        for cat in self.repo.listar_categorias(tipo=tipo, apenas_ativas=True):
            self.cb_categoria.addItem(cat.nome, cat.id)
        if manter_id is not None:
            i = self.cb_categoria.findData(manter_id)
            if i >= 0:
                self.cb_categoria.setCurrentIndex(i)

    def validar(self):
        if not self.ed_descricao.text().strip():
            return "Informe a descrição da recorrência."
        if self.cb_conta.currentData() is None:
            return "Cadastre uma conta antes."
        if self.cb_categoria.currentData() is None:
            return "Cadastre uma categoria antes."
        if self.sp_valor.value() <= 0:
            return "Informe um valor maior que zero."
        linha = self.linha_termino
        if linha.rb_data.isChecked():
            if linha.ed_data.date() < self.ed_inicio.date():
                return "A data de término não pode ser anterior à 1ª ocorrência."
        return None

    def dados(self):
        linha = self.linha_termino
        data_fim = linha.ed_data.date().toString("yyyy-MM-dd") \
            if linha.rb_data.isChecked() else None
        qtd_vezes = linha.sp_qtd.value() if linha.rb_qtd.isChecked() else None
        return dict(descricao=self.ed_descricao.text().strip(),
                    conta_id=self.cb_conta.currentData(),
                    categoria_id=self.cb_categoria.currentData(),
                    tipo=self.cb_tipo.currentData(), valor=self.sp_valor.value(),
                    frequencia=self.cb_frequencia.currentData(),
                    data_inicio=self.ed_inicio.date().toString("yyyy-MM-dd"),
                    data_fim=data_fim,
                    qtd_vezes=qtd_vezes,
                    ativo=1 if self.ck_ativo.isChecked() else 0)


class DialogoCartao(DialogoBase):
    """Cadastro de cartão de crédito: conta de débito, fechamento,
    vencimento e limite."""

    def __init__(self, repo: Repositorio, cartao=None, parent=None):
        super().__init__("Editar cartão" if cartao else "Novo cartão de crédito", parent)
        self.repo = repo
        self.cartao = cartao

        self.ed_nome = QLineEdit()
        self.ed_nome.setMaxLength(120)
        self.cb_conta = QComboBox()
        for conta in repo.listar_contas(apenas_ativas=True):
            self.cb_conta.addItem(conta.nome, conta.id)
        self.sp_fechamento = QSpinBox()
        self.sp_fechamento.setRange(1, 31)
        self.sp_fechamento.setValue(20)
        self.sp_vencimento = QSpinBox()
        self.sp_vencimento.setRange(1, 31)
        self.sp_vencimento.setValue(10)
        self.sp_limite = DialogoBase._spin_moeda()
        self.sp_limite.setPrefix("")
        self.ck_ativo = QCheckBox("Cartão ativo")
        self.ck_ativo.setChecked(True)

        self.form.addRow("Nome*", self.ed_nome)
        self.form.addRow("Conta que paga a fatura*", self.cb_conta)
        self.form.addRow("Dia do fechamento", self.sp_fechamento)
        self.form.addRow("Dia do vencimento", self.sp_vencimento)
        self.form.addRow("Limite total", self.sp_limite)
        self.form.addRow("", self.ck_ativo)

        if cartao:
            self.ed_nome.setText(cartao.nome)
            self.cb_conta.setCurrentIndex(self.cb_conta.findData(cartao.conta_id))
            self.sp_fechamento.setValue(cartao.dia_fechamento)
            self.sp_vencimento.setValue(cartao.dia_vencimento)
            self.sp_limite.setValue(cartao.limite_total)
            self.ck_ativo.setChecked(bool(cartao.ativo))

    def validar(self):
        if not self.ed_nome.text().strip():
            return "Informe o nome do cartão."
        if self.cb_conta.currentData() is None:
            return "Cadastre uma conta antes (é ela que paga a fatura)."
        return None

    def dados(self):
        return dict(nome=self.ed_nome.text().strip(),
                    conta_id=self.cb_conta.currentData(),
                    dia_fechamento=self.sp_fechamento.value(),
                    dia_vencimento=self.sp_vencimento.value(),
                    limite_total=self.sp_limite.value(),
                    ativo=1 if self.ck_ativo.isChecked() else 0)


class DialogoCompra(DialogoBase):
    """Nova compra no cartão — à vista ou parcelada.

    Calcula e exibe a FATURA resultante pela regra do fechamento
    (editável para casos excepcionais) e a progressão das parcelas
    (avança 1 fatura por mês a partir da escolhida).
    """

    def __init__(self, repo: Repositorio, cartao, parent=None):
        super().__init__(f"Nova compra — {cartao.nome}", parent)
        self.repo = repo
        self.cartao = cartao

        self.cb_categoria = QComboBox()
        for cat in repo.listar_categorias(tipo="saida", apenas_ativas=True):
            self.cb_categoria.addItem(cat.nome, cat.id)
        self.ed_descricao = QLineEdit()
        self.ed_descricao.setMaxLength(200)
        self.ed_data = QDateEdit(QDate.currentDate())
        self.ed_data.setDisplayFormat("dd/MM/yyyy")
        self.ed_data.setCalendarPopup(True)
        self.sp_valor_total = DialogoBase._spin_moeda()
        self.sp_parcelas = QSpinBox()
        self.sp_parcelas.setRange(1, 120)
        self.sp_parcelas.setValue(1)
        self.cb_fatura = QComboBox()
        # 60 faturas à frente é suficiente para 120x semal? não: 120x = 120
        # faturas. Gera 144 opções (12 anos).
        hoje = QDate.currentDate()
        ano, mes = hoje.year(), hoje.month()
        for _ in range(144):
            self.cb_fatura.addItem(fmt_mes_curto(f"{ano:04d}-{mes:02d}"),
                                   f"{ano:04d}-{mes:02d}")
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        self.lb_preview = QLabel("")
        self.lb_preview.setWordWrap(True)

        self.form.addRow("Categoria*", self.cb_categoria)
        self.form.addRow("Descrição", self.ed_descricao)
        self.form.addRow("Data da compra", self.ed_data)
        self.form.addRow("Valor total*", self.sp_valor_total)
        self.form.addRow("Parcelas", self.sp_parcelas)
        self.form.addRow("Fatura de entrada*", self.cb_fatura)
        self.form.addRow("", self.lb_preview)

        self._recalcular()
        self.ed_data.dateChanged.connect(self._recalcular)
        self.sp_valor_total.valueChanged.connect(self._recalcular)
        self.sp_parcelas.valueChanged.connect(self._recalcular)
        self.cb_fatura.currentIndexChanged.connect(self._recalcular)

    def _fatura_calculada(self) -> str:
        """Fatura pela regra do fechamento do cartão."""
        d = self.ed_data.date()
        dia = d.day()
        meses = 1 if dia <= self.cartao.dia_fechamento else 2
        ano, mes = d.year(), d.month()
        for _ in range(meses):
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        return f"{ano:04d}-{mes:02d}"

    def _recalcular(self):
        """Recalcula a fatura sugerida e o preview das parcelas.

        Não sobrescreve uma escolha manual: se a fatura calculada mudou
        (ex.: usuário mexeu na data), atualiza a seleção do combo.
        """
        calculada = self._fatura_calculada()
        i = self.cb_fatura.findData(calculada)
        if i >= 0 and self.cb_fatura.currentData() != calculada:
            self.cb_fatura.setCurrentIndex(i)
        fatura = self.cb_fatura.currentData() or calculada
        venc_iso = Repositorio.vencimento_de_fatura(
            fatura, self.cartao.dia_vencimento)
        n = self.sp_parcelas.value()
        valor = self.sp_valor_total.value()
        if n > 1 and valor > 0:
            por = round(valor / n, 2)
            anos = [self._fatura_deslocada(fatura, k) for k in range(n)]
            ultima = anos[-1]
            self.lb_preview.setText(
                f"{n}× de {fmt_moeda(por)} (1ª {fmt_moeda(valor - por * (n - 1))})\n"
                f"Faturas: {fmt_mes_curto(fatura)} a {fmt_mes_curto(ultima)} · "
                f"1º vencimento: {fmt_data(venc_iso)}")
        else:
            self.lb_preview.setText(
                f"Vence em {fmt_data(venc_iso)} "
                f"(fatura {fmt_mes_curto(fatura)})")

    @staticmethod
    def _fatura_deslocada(fatura: str, meses: int) -> str:
        ano, mes = int(fatura[:4]), int(fatura[5:7])
        for _ in range(meses):
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        return f"{ano:04d}-{mes:02d}"

    def validar(self):
        if self.cb_categoria.currentData() is None:
            return "Cadastre uma categoria de saída antes."
        if self.sp_valor_total.value() <= 0:
            return "Informe um valor maior que zero."
        if self.cb_fatura.currentData() is None:
            return "Escolha a fatura de entrada."
        return None

    def dados(self):
        return dict(cartao_id=self.cartao.id,
                    categoria_id=self.cb_categoria.currentData(),
                    descricao=self.ed_descricao.text().strip(),
                    data_compra=self.ed_data.date().toString("yyyy-MM-dd"),
                    valor_total=self.sp_valor_total.value(),
                    total_parcelas=self.sp_parcelas.value(),
                    fatura=self.cb_fatura.currentData())


class DialogoPagarFatura(DialogoBase):
    """Pagamento de UMA fatura: gera 1 lançamento de saída pago na conta
    escolhida e quita as parcelas em aberto da fatura."""

    def __init__(self, repo: Repositorio, fatura_info: dict, parent=None):
        # fatura_info: {cartao_id, cartao_nome, fatura, vencimento, total, qtde}
        super().__init__(
            f"Pagar fatura {fmt_mes_curto(fatura_info['fatura'])} — "
            f"{fatura_info['cartao_nome']}", parent)
        self.repo = repo
        self.info = fatura_info

        self.lb_total = QLabel(
            f"Total em aberto: {fmt_moeda(fatura_info['total'])} · "
            f"{fatura_info['qtde']} parcela(s) · vencimento "
            f"{fmt_data(fatura_info['vencimento'])}")
        self.lb_total.setObjectName("tituloCard")
        self.lb_total.setWordWrap(True)

        self.cb_conta = QComboBox()
        self.conta_padrao = None
        for conta in repo.listar_contas(apenas_ativas=True):
            self.cb_conta.addItem(conta.nome, conta.id)
        # Pré-seleciona a conta vinculada ao cartão, se ativa.
        cartoes = [c for c in repo.listar_cartoes()
                   if c.id == fatura_info["cartao_id"]]
        if cartoes:
            self.conta_padrao = cartoes[0].conta_id
            i = self.cb_conta.findData(self.conta_padrao)
            if i >= 0:
                self.cb_conta.setCurrentIndex(i)

        self.cb_categoria = QComboBox()
        for cat in repo.listar_categorias(tipo="saida", apenas_ativas=True):
            self.cb_categoria.addItem(cat.nome, cat.id)

        self.ed_data = QDateEdit(QDate.currentDate())
        self.ed_data.setDisplayFormat("dd/MM/yyyy")
        self.ed_data.setCalendarPopup(True)

        self.ed_descricao = QLineEdit(
            f"Fatura {fatura_info['cartao_nome']} — "
            f"{fmt_mes_curto(fatura_info['fatura'])}")
        self.ed_descricao.setMaxLength(200)

        self.form.addRow("", self.lb_total)
        self.form.addRow("Conta debitada*", self.cb_conta)
        self.form.addRow("Categoria*", self.cb_categoria)
        self.form.addRow("Data do pagamento", self.ed_data)
        self.form.addRow("Descrição", self.ed_descricao)

    def validar(self):
        if self.cb_conta.currentData() is None:
            return "Selecione a conta que paga a fatura."
        if self.cb_categoria.currentData() is None:
            return "Selecione a categoria do pagamento."
        return None

    def dados(self):
        return dict(cartao_id=self.info["cartao_id"], fatura=self.info["fatura"],
                    conta_id=self.cb_conta.currentData(),
                    categoria_id=self.cb_categoria.currentData(),
                    data_mov=self.ed_data.date().toString("yyyy-MM-dd"),
                    descricao=self.ed_descricao.text().strip())


class DialogoNovoUsuario(DialogoBase):
    """Cadastro de usuário pelo admin."""

    def __init__(self, parent=None):
        super().__init__("Novo usuário", parent)

        self.ed_nome = QLineEdit()
        self.ed_nome.setMaxLength(120)
        self.ed_email = QLineEdit()
        self.ed_email.setPlaceholderText("novo@email.com")
        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_confirma = QLineEdit()
        self.ed_confirma.setEchoMode(QLineEdit.EchoMode.Password)

        self.form.addRow("Nome*", self.ed_nome)
        self.form.addRow("E-mail*", self.ed_email)
        self.form.addRow("Senha*", self.ed_senha)
        self.form.addRow("Confirmar*", self.ed_confirma)

    def validar(self):
        if not self.ed_nome.text().strip():
            return "Informe o nome do usuário."
        if not self._email_valido(self.ed_email.text().strip().lower()):
            return "Informe um e-mail válido."
        erro = validar_senha_forte(self.ed_senha.text())
        if erro:
            return erro
        if self.ed_senha.text() != self.ed_confirma.text():
            return "As senhas não conferem."
        return None

    def dados(self):
        """Retorna a tupla (nome, email, senha)."""
        return (self.ed_nome.text().strip(),
                self.ed_email.text().strip().lower(),
                self.ed_senha.text())


class DialogoNovaSenha(DialogoBase):
    """Redefinição de senha pelo admin."""

    def __init__(self, nome_usuario: str, parent=None):
        super().__init__(f"Resetar senha — {nome_usuario}", parent)

        self.ed_senha = QLineEdit()
        self.ed_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_confirma = QLineEdit()
        self.ed_confirma.setEchoMode(QLineEdit.EchoMode.Password)

        self.form.addRow("Nova senha*", self.ed_senha)
        self.form.addRow("Confirmar*", self.ed_confirma)

    def validar(self):
        erro = validar_senha_forte(self.ed_senha.text())
        if erro:
            return erro
        if self.ed_senha.text() != self.ed_confirma.text():
            return "As senhas não conferem."
        return None

    def dados(self):
        """Retorna a nova senha em texto puro (o hash acontece no repositório)."""
        return self.ed_senha.text()