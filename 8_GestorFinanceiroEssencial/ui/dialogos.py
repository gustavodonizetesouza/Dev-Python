"""Diálogos de cadastro: contas, categorias, lançamentos, recorrências e usuários."""
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDateEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFormLayout, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QVBoxLayout)

from core.seguranca import validar_senha_forte
from dominio.repositorio import Repositorio

TIPOS_CONTA = ["Corrente", "Poupança", "Cartão", "Dinheiro", "Investimento"]


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


class DialogoRecorrencia(DialogoBase):
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
        self.sp_dia = QSpinBox()
        self.sp_dia.setRange(1, 31)
        hoje = QDate.currentDate()
        self.ed_inicio = QDateEdit(QDate(hoje.year(), hoje.month(), 1))
        self.ed_inicio.setDisplayFormat("MM/yyyy")
        self.ed_inicio.setCalendarPopup(True)
        self.ck_ativo = QCheckBox("Recorrência ativa")
        self.ck_ativo.setChecked(True)

        self.form.addRow("Descrição*", self.ed_descricao)
        self.form.addRow("Tipo", self.cb_tipo)
        self.form.addRow("Conta*", self.cb_conta)
        self.form.addRow("Categoria*", self.cb_categoria)
        self.form.addRow("Valor*", self.sp_valor)
        self.form.addRow("Dia do mês", self.sp_dia)
        self.form.addRow("Início em", self.ed_inicio)
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
            self.sp_dia.setValue(recorrencia.dia_do_mes)
            a, m = (int(x) for x in recorrencia.mes_inicio.split("-")[:2])
            self.ed_inicio.setDate(QDate(a, m, 1))
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
        return None

    def dados(self):
        return dict(descricao=self.ed_descricao.text().strip(),
                    conta_id=self.cb_conta.currentData(),
                    categoria_id=self.cb_categoria.currentData(),
                    tipo=self.cb_tipo.currentData(), valor=self.sp_valor.value(),
                    dia_do_mes=self.sp_dia.value(),
                    mes_inicio=self.ed_inicio.date().toString("yyyy-MM"),
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
