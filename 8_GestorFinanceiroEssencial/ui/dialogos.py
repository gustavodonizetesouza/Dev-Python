"""Diálogos de cadastro: contas, categorias, lançamentos, recorrências e usuários.

DialogoRecorrencia (v2): frequência mensal/semanal/trimestral/anual,
primeira ocorrência (data completa) e término opcional por data ou por
quantidade de vezes (ex.: 280 parcelas de um financiamento).
"""
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDateEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QRadioButton, QSpinBox, QVBoxLayout,
                             QWidget)

from core.seguranca import validar_senha_forte
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
        self.botoes.button(
            QDialogButtonBox.StandardButton.Save).setText("Salvar")
        self.botoes.button(
            QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
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
            self.cb_tipo.setCurrentIndex(
                1 if categoria.tipo == "entrada" else 0)
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
    """Lançamento com controle de contas a pagar/receber.

    O checkbox 'Já pago / Já recebido' vem MARCADO por padrão (entrada
    rápida mantém o comportamento anterior); desmarque para registrar
    uma pendência. O texto do checkbox se adapta ao tipo: saída = pago,
    entrada = recebido.
    """

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
        self.cb_tipo.currentIndexChanged.connect(
            lambda _: self._recarregar_categorias())

        if lancamento:
            self.cb_tipo.setCurrentIndex(
                self.cb_tipo.findData(lancamento.tipo))
            self._recarregar_categorias(lancamento.categoria_id)
            self.cb_conta.setCurrentIndex(
                self.cb_conta.findData(lancamento.conta_id))
            self.cb_valor.setValue(lancamento.valor)
            a, m, d = (int(x) for x in lancamento.data_mov.split("-"))
            self.ed_data.setDate(QDate(a, m, d))
            self.ed_descricao.setText(lancamento.descricao)
            self.ck_pago.setChecked(bool(lancamento.pago))
        else:
            self._recarregar_categorias()
        self._atualizar_texto_pago()

    def _atualizar_texto_pago(self):
        """Adapta o texto do checkbox ao tipo (saída = pago, entrada = recebido)."""
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
    """Linha do formulário com os 3 modos de término e seus campos.

    - 'Sem fim': gera para sempre (comportamento clássico).
    - 'Até a data': gera enquanto a ocorrência <= data de término.
    - 'Por quantidade': gera até atingir N ocorrências (ex.: 280 parcelas).
    """

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
    """Recorrência v2: frequência + primeira ocorrência + término opcional.

    A frequência define o passo entre ocorrências (mensal = 1 mês,
    semanal = 7 dias, trimestral = 3 meses, anual = 12 meses). O dia do mês
    e o dia da semana derivam da primeira ocorrência. O término pode ser
    por data ou por quantidade de vezes (ex.: 280 parcelas); sem término,
    gera para sempre.
    """

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

        self.cb_tipo.currentIndexChanged.connect(
            lambda _: self._recarregar_categorias())

        if recorrencia:
            self.ed_descricao.setText(recorrencia.descricao)
            self.cb_tipo.setCurrentIndex(
                self.cb_tipo.findData(recorrencia.tipo))
            self._recarregar_categorias(recorrencia.categoria_id)
            self.cb_conta.setCurrentIndex(
                self.cb_conta.findData(recorrencia.conta_id))
            self.sp_valor.setValue(recorrencia.valor)
            i = self.cb_frequencia.findData(recorrencia.frequencia)
            self.cb_frequencia.setCurrentIndex(max(0, i))
            if recorrencia.data_inicio:
                a, m, d = (int(x)
                           for x in recorrencia.data_inicio[:10].split("-"))
                self.ed_inicio.setDate(QDate(a, m, d))
            if recorrencia.data_fim:
                a, m, d = (int(x)
                           for x in recorrencia.data_fim[:10].split("-"))
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
        if linha.rb_qtd.isChecked() and linha.sp_qtd.value() <= 0:
            return "Informe uma quantidade de ocorrências maior que zero."
        if linha.rb_data.isChecked():
            dt_fim = linha.ed_data.date()
            if dt_fim < self.ed_inicio.date():
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


class DialogoNovoUsuario(DialogoBase):
    """Cadastro de usuário pelo admin. O novo usuário nasce com papel
    'usuario' e recebe suas categorias padrão; o admin pode promovê-lo
    depois pela página Usuários."""

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
