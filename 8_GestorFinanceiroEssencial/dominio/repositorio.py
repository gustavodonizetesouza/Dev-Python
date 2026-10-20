"""Modelos + repositórios — SQL portável (SQLite e SQL Server) com isolamento
multiusuário, contas a pagar/receber, recorrências v2 e cartão de crédito.

Repositórios:
- RepositorioUsuarios: cadastro, autenticação e administração de usuários.
- Repositorio: acesso a dados do usuário logado — recebe o usuario_id no
  construtor e TODAS as consultas filtram por ele.

Contas a pagar/receber: flag `pago` nos lançamentos; saldo efetivo considera
apenas pagos; saldo previsto considera tudo. Ciclo da recorrência: a BAIXA
é o gatilho — ao pagar uma parcela, a próxima ocorrência nasce
automaticamente (máx. 1 pendência futura por recorrência).

Cartão de crédito: o cartão é um "livro próprio" — as compras vivem em
compras_cartao (1 linha por PARCELA) e NÃO geram lançamentos. A única
saída que toca o caixa é o PAGAMENTO DA FATURA: um único lançamento de
saída pago na conta vinculada, que quita as parcelas da fatura. Enquanto
não paga, a compra é débito previsto (entra no saldo previsto, não no
saldo efetivo) e consome o limite do cartão.

Regra da fatura (nomeada pelo mês de VENCIMENTO 'YYYY-MM'):
- compra com dia <= fechamento -> vence no dia de vencimento do mês seguinte;
- compra com dia >  fechamento -> vence no mês seguinte ao seguinte;
- cada parcela avança exatamente 1 fatura por mês a partir da primeira;
- o usuário pode escolher uma fatura diferente no ato do lançamento.

O isolamento por usuario_id vale para todos, inclusive admins.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

from core.conexao import BancoDados
from core.schema import CATEGORIAS_INICIAIS
from core.seguranca import hash_senha, validar_senha_forte, verificar_senha
from core.util import (avancar_mes, dias_no_mes, fmt_mes_curto, mes_anterior,
                       primeiro_dia, ultimo_dia)

FREQUENCIAS = ("mensal", "semanal", "trimestral", "anual")


class ErroRegraNegocio(Exception):
    """Violação de regra de negócio (e-mail duplicado, categoria em uso etc.)."""


# ----------------------------- modelos -----------------------------
@dataclass
class Usuario:
    id: Optional[int] = None
    nome: str = ""
    email: str = ""
    senha_hash: str = ""
    papel: str = "usuario"
    plano: str = "gratuito"
    ativo: int = 1
    total_lancamentos: int = 0
    criado_em: Any = None


@dataclass
class Conta:
    id: Optional[int] = None
    nome: str = ""
    tipo: str = "Corrente"
    saldo_inicial: float = 0.0
    ativo: int = 1
    saldo_atual: float = 0.0
    criado_em: Any = None


@dataclass
class Categoria:
    id: Optional[int] = None
    nome: str = ""
    tipo: str = "saida"
    cor: str = "#607d8b"
    ativo: int = 1
    uso: int = 0
    criado_em: Any = None


@dataclass
class Lancamento:
    id: Optional[int] = None
    conta_id: Optional[int] = None
    conta_nome: str = ""
    categoria_id: Optional[int] = None
    categoria_nome: str = ""
    categoria_cor: str = ""
    tipo: str = "saida"
    valor: float = 0.0
    data_mov: str = ""
    descricao: str = ""
    pago: int = 1
    recorrencia_id: Optional[int] = None


@dataclass
class Recorrencia:
    id: Optional[int] = None
    descricao: str = ""
    conta_id: Optional[int] = None
    conta_nome: str = ""
    categoria_id: Optional[int] = None
    categoria_nome: str = ""
    tipo: str = "saida"
    valor: float = 0.0
    frequencia: str = "mensal"
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    qtd_vezes: Optional[int] = None
    geradas: int = 0
    ultimo_gerado: Optional[str] = None
    ativo: int = 1
    proxima_data: Optional[str] = None
    concluida: bool = False


@dataclass
class CartaoCredito:
    id: Optional[int] = None
    nome: str = ""
    conta_id: Optional[int] = None     # conta que paga a fatura
    conta_nome: str = ""
    dia_fechamento: int = 1
    dia_vencimento: int = 10
    limite_total: float = 0.0
    ativo: int = 1
    # calculados:
    total_aberto: float = 0.0          # soma das parcelas não pagas
    limite_disponivel: float = 0.0     # limite_total - total_aberto


@dataclass
class CompraCartao:
    id: Optional[int] = None
    cartao_id: Optional[int] = None
    cartao_nome: str = ""
    categoria_id: Optional[int] = None
    categoria_nome: str = ""
    categoria_cor: str = ""
    grupo_id: Optional[int] = None     # agrupa as parcelas de uma mesma compra
    descricao: str = ""
    data_compra: str = ""
    valor: float = 0.0                 # valor da PARCELA
    parcela: int = 1
    total_parcelas: int = 1
    fatura: str = ""                   # 'YYYY-MM' — mês de VENCIMENTO
    vencimento: str = ""               # data ISO calculada
    pago: int = 0
    lancamento_id: Optional[int] = None


@dataclass
class KpiMes:
    saldo_total: float = 0.0
    saldo_previsto: float = 0.0        # inclui pendências + faturas em aberto
    receitas_mes: float = 0.0
    despesas_mes: float = 0.0
    a_pagar_mes: float = 0.0
    a_receber_mes: float = 0.0
    faturas_mes: float = 0.0           # faturas de cartão vencendo no mês (aberto)
    lancamentos_mes: int = 0
    pendentes_mes: int = 0


def _num(valor) -> float:
    return float(valor) if valor is not None else 0.0


def _para_iso(valor) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()[:10]
    return valor or ""


def _para_data(valor) -> Optional[date]:
    iso = _para_iso(valor)
    if not iso:
        return None
    try:
        return date.fromisoformat(iso[:10])
    except ValueError:
        return None


def _mesmo_dia_proximo_mes(d: date, meses: int) -> date:
    """Avança N meses mantendo o dia (ajustado ao tamanho real do mês)."""
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, dias_no_mes(ano, mes))
    return date(ano, mes, dia)


def _avancar_ocorrencia(data: date, frequencia: str) -> date:
    if frequencia == "semanal":
        return data + timedelta(days=7)
    if frequencia == "trimestral":
        return _mesmo_dia_proximo_mes(data, 3)
    if frequencia == "anual":
        return _mesmo_dia_proximo_mes(data, 12)
    return _mesmo_dia_proximo_mes(data, 1)


# ----------------------- repositório de usuários -----------------------
class RepositorioUsuarios:
    """Cadastro, autenticação e administração de usuários."""

    def __init__(self, db: BancoDados):
        self.db = db

    @staticmethod
    def _mapear(r) -> Usuario:
        u = Usuario(id=r["id"], nome=r["nome"], email=r["email"],
                    senha_hash=r.get("senha_hash") or "",
                    papel=r["papel"], plano=r["plano"])
        u.ativo = 1 if r["ativo"] in (1, True) else 0
        u.total_lancamentos = int(r.get("total_lancamentos") or 0)
        u.criado_em = r.get("criado_em")
        return u

    def contar_usuarios(self) -> int:
        return int(self.db.consultar(
            "SELECT COUNT(*) AS total FROM usuarios")[0]["total"])

    def buscar_por_id(self, usuario_id: int) -> Optional[Usuario]:
        linhas = self.db.consultar(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        return self._mapear(linhas[0]) if linhas else None

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        linhas = self.db.consultar(
            "SELECT * FROM usuarios WHERE email = ?", ((email or "").strip().lower(),))
        return self._mapear(linhas[0]) if linhas else None

    def semear_categorias(self, usuario_id: int):
        for nome, tipo, cor in CATEGORIAS_INICIAIS:
            self.db.executar(
                "INSERT INTO categorias (usuario_id, nome, tipo, cor) VALUES (?, ?, ?, ?)",
                (usuario_id, nome, tipo, cor), commitar=False)

    def criar_usuario(self, nome: str, email: str, senha: str) -> Usuario:
        nome = (nome or "").strip()
        email = (email or "").strip().lower()
        if not nome:
            raise ErroRegraNegocio("Informe o nome.")
        if not email or "@" not in email:
            raise ErroRegraNegocio("Informe um e-mail válido.")
        erro = validar_senha_forte(senha)
        if erro:
            raise ErroRegraNegocio(erro)
        if self.buscar_por_email(email):
            raise ErroRegraNegocio("Já existe uma conta com este e-mail.")

        papel = "admin" if self.contar_usuarios() == 0 else "usuario"
        with self.db.transacao():
            novo_id = self.db.inserir(
                """INSERT INTO usuarios (nome, email, senha_hash, papel)
                   VALUES (?, ?, ?, ?)""",
                (nome, email, hash_senha(senha), papel), commitar=False)
            self.semear_categorias(novo_id)
        return self.buscar_por_id(novo_id)

    def autenticar(self, email: str, senha: str) -> Optional[Usuario]:
        u = self.buscar_por_email(email)
        if u is None or not verificar_senha(senha, u.senha_hash):
            return None
        if not u.ativo:
            raise ErroRegraNegocio(
                "Esta conta está desativada. Procure o administrador do sistema.")
        return u

    def listar_usuarios(self):
        sql = """
            SELECT u.id, u.nome, u.email, u.papel, u.plano, u.ativo, u.criado_em,
                   (SELECT COUNT(*) FROM lancamentos l WHERE l.usuario_id = u.id)
                       AS total_lancamentos
            FROM usuarios u
            ORDER BY u.id
        """
        return [self._mapear(r) for r in self.db.consultar(sql)]

    def _outros_admins_ativos(self, usuario_id: int) -> int:
        return int(self.db.consultar(
            """SELECT COUNT(*) AS t FROM usuarios
               WHERE papel = 'admin' AND ativo = 1 AND id != ?""",
            (usuario_id,))[0]["t"])

    def alternar_ativo(self, usuario_id: int, solicitante_id: int) -> int:
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if usuario_id == solicitante_id:
            raise ErroRegraNegocio("Você não pode desativar a sua própria conta.")
        if u.papel == "admin" and u.ativo and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível desativar o último administrador ativo do sistema.")
        novo = 0 if u.ativo else 1
        self.db.executar("UPDATE usuarios SET ativo = ? WHERE id = ?",
                         (novo, usuario_id))
        return novo

    def definir_papel(self, usuario_id: int, papel: str, solicitante_id: int):
        if papel not in ("admin", "usuario"):
            raise ErroRegraNegocio("Papel inválido.")
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if usuario_id == solicitante_id and papel != "admin":
            raise ErroRegraNegocio("Você não pode remover o seu próprio papel de admin.")
        if u.papel == "admin" and papel != "admin" and u.ativo \
                and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível rebaixar o último administrador ativo do sistema.")
        self.db.executar("UPDATE usuarios SET papel = ? WHERE id = ?",
                         (papel, usuario_id))

    def definir_plano(self, usuario_id: int, plano: str):
        self.db.executar("UPDATE usuarios SET plano = ? WHERE id = ?",
                         (plano, usuario_id))

    def resetar_senha(self, usuario_id: int, nova_senha: str):
        erro = validar_senha_forte(nova_senha)
        if erro:
            raise ErroRegraNegocio(erro)
        if not self.buscar_por_id(usuario_id):
            raise ErroRegraNegocio("Usuário não encontrado.")
        self.db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                         (hash_senha(nova_senha), usuario_id))

    def excluir_usuario(self, usuario_id: int, solicitante_id: int):
        if usuario_id == solicitante_id:
            raise ErroRegraNegocio("Você não pode excluir a própria conta logada.")
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if u.papel == "admin" and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível excluir o último administrador do sistema.")
        with self.db.transacao():
            for tabela in ("compras_cartao", "cartoes_credito", "lancamentos",
                           "recorrencias", "contas", "categorias", "usuarios"):
                self.db.executar(f"DELETE FROM {tabela} WHERE usuario_id = ?",
                                 (usuario_id,), commitar=False)


# --------------------- repositório do usuário logado ---------------------
class Repositorio:
    """Acesso a dados do usuário logado — todas as operações filtram por
    usuario_id (multi-tenancy lógico)."""

    def __init__(self, db: BancoDados, usuario_id: int):
        self.db = db
        self.usuario_id = usuario_id

    # ===================== CONTAS =====================
    def listar_contas(self, apenas_ativas: bool = False):
        sql = """
            SELECT c.id, c.nome, c.tipo, c.saldo_inicial, c.ativo,
                   c.saldo_inicial + COALESCE(SUM(
                       CASE WHEN l.tipo = 'entrada' THEN l.valor ELSE -l.valor END), 0) AS saldo_atual
            FROM contas c
            LEFT JOIN lancamentos l ON l.conta_id = c.id AND l.pago = 1
            WHERE c.usuario_id = ?
        """
        if apenas_ativas:
            sql += " AND c.ativo = 1"
        sql += " GROUP BY c.id, c.nome, c.tipo, c.saldo_inicial, c.ativo ORDER BY c.nome"

        contas = []
        for linha in self.db.consultar(sql, (self.usuario_id,)):
            conta = Conta(id=linha["id"], nome=linha["nome"], tipo=linha["tipo"])
            conta.saldo_inicial = _num(linha["saldo_inicial"])
            conta.saldo_atual = _num(linha["saldo_atual"])
            conta.ativo = 1 if linha["ativo"] in (1, True) else 0
            contas.append(conta)
        return contas

    def salvar_conta(self, nome, tipo, saldo_inicial, ativo, id=None):
        if id:
            self.db.executar(
                """UPDATE contas SET nome = ?, tipo = ?, saldo_inicial = ?, ativo = ?
                   WHERE id = ? AND usuario_id = ?""",
                (nome, tipo, saldo_inicial, int(ativo), id, self.usuario_id))
            return id
        return self.db.inserir(
            """INSERT INTO contas (usuario_id, nome, tipo, saldo_inicial, ativo)
               VALUES (?, ?, ?, ?, ?)""",
            (self.usuario_id, nome, tipo, saldo_inicial, int(ativo)))

    def excluir_conta(self, id):
        """Exclui a conta e o histórico vinculado. Bloqueia se houver cartão
        de crédito usando esta conta para pagar faturas."""
        n_cart = self.db.consultar(
            "SELECT COUNT(*) AS t FROM cartoes_credito WHERE conta_id = ? AND usuario_id = ?",
            (id, self.usuario_id))[0]["t"]
        if n_cart:
            raise ErroRegraNegocio(
                "A conta é usada por {n} cartão(ões) de crédito — redefina a "
                "conta de débito do(s) cartão(ões) antes de excluí-la.".format(n=n_cart))
        with self.db.transacao():
            self.db.executar(
                "DELETE FROM lancamentos WHERE conta_id = ? AND usuario_id = ?",
                (id, self.usuario_id), commitar=False)
            self.db.executar(
                "DELETE FROM recorrencias WHERE conta_id = ? AND usuario_id = ?",
                (id, self.usuario_id), commitar=False)
            self.db.executar(
                "DELETE FROM contas WHERE id = ? AND usuario_id = ?",
                (id, self.usuario_id), commitar=False)

    # ===================== CATEGORIAS =====================
    def listar_categorias(self, tipo=None, apenas_ativas=False):
        where, params = ["g.usuario_id = ?"], [self.usuario_id]
        if tipo:
            where.append("g.tipo = ?")
            params.append(tipo)
        if apenas_ativas:
            where.append("g.ativo = 1")
        sql = """
            SELECT g.id, g.nome, g.tipo, g.cor, g.ativo,
                   (SELECT COUNT(*) FROM lancamentos l
                     WHERE l.categoria_id = g.id AND l.usuario_id = g.usuario_id) AS uso
            FROM categorias g
        """ + " WHERE " + " AND ".join(where) + " ORDER BY g.nome"

        categorias = []
        for linha in self.db.consultar(sql, params):
            cat = Categoria(id=linha["id"], nome=linha["nome"], tipo=linha["tipo"],
                            cor=linha["cor"], uso=int(linha["uso"]))
            cat.ativo = 1 if linha["ativo"] in (1, True) else 0
            categorias.append(cat)
        return categorias

    def salvar_categoria(self, nome, tipo, cor, ativo=1, id=None):
        if id:
            self.db.executar(
                """UPDATE categorias SET nome = ?, tipo = ?, cor = ?, ativo = ?
                   WHERE id = ? AND usuario_id = ?""",
                (nome, tipo, cor, int(ativo), id, self.usuario_id))
            return id
        return self.db.inserir(
            """INSERT INTO categorias (usuario_id, nome, tipo, cor, ativo)
               VALUES (?, ?, ?, ?, ?)""",
            (self.usuario_id, nome, tipo, cor, int(ativo)))

    def excluir_categoria(self, id):
        n_lanc = self.db.consultar(
            """SELECT COUNT(*) AS t FROM lancamentos
               WHERE categoria_id = ? AND usuario_id = ?""",
            (id, self.usuario_id))[0]["t"]
        n_cc = self.db.consultar(
            """SELECT COUNT(*) AS t FROM compras_cartao
               WHERE categoria_id = ? AND usuario_id = ?""",
            (id, self.usuario_id))[0]["t"]
        if n_lanc or n_cc:
            raise ErroRegraNegocio(
                f"A categoria está em uso por {n_lanc} lançamento(s) e {n_cc} "
                "compra(s) no cartão.")
        self.db.executar("DELETE FROM categorias WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    # ===================== LANÇAMENTOS =====================
    def _filtros_sql(self, filtros: dict):
        where = ["l.usuario_id = ?"]
        params = [self.usuario_id]
        if filtros.get("conta_id"):
            where.append("l.conta_id = ?")
            params.append(filtros["conta_id"])
        if filtros.get("categoria_id"):
            where.append("l.categoria_id = ?")
            params.append(filtros["categoria_id"])
        if filtros.get("tipo"):
            where.append("l.tipo = ?")
            params.append(filtros["tipo"])
        if filtros.get("data_ini"):
            where.append("l.data_mov >= ?")
            params.append(filtros["data_ini"])
        if filtros.get("data_fim"):
            where.append("l.data_mov <= ?")
            params.append(filtros["data_fim"])
        if filtros.get("pago") is not None:
            where.append("l.pago = ?")
            params.append(1 if filtros["pago"] in (1, True) else 0)
        if filtros.get("busca"):
            where.append("l.descricao LIKE ?")
            params.append(f"%{filtros['busca']}%")
        return " AND ".join(where), params

    def listar_lancamentos(self, filtros: dict = None):
        filtros = filtros or {}
        where, params = self._filtros_sql(filtros)
        sql = f"""
            SELECT l.id, l.conta_id, c.nome AS conta_nome, l.categoria_id,
                   g.nome AS categoria_nome, g.cor AS categoria_cor,
                   l.tipo, l.valor, l.data_mov, l.descricao, l.pago, l.recorrencia_id
            FROM lancamentos l
            JOIN contas c ON c.id = l.conta_id
            JOIN categorias g ON g.id = l.categoria_id
            WHERE {where}
            ORDER BY l.data_mov DESC, l.id DESC
        """
        return [Lancamento(
                    id=r["id"], conta_id=r["conta_id"], conta_nome=r["conta_nome"],
                    categoria_id=r["categoria_id"], categoria_nome=r["categoria_nome"],
                    categoria_cor=r["categoria_cor"], tipo=r["tipo"],
                    valor=_num(r["valor"]), data_mov=_para_iso(r["data_mov"]),
                    descricao=r["descricao"] or "",
                    pago=1 if r["pago"] in (1, True) else 0,
                    recorrencia_id=r["recorrencia_id"])
                for r in self.db.consultar(sql, params)]

    def salvar_lancamento(self, conta_id, categoria_id, tipo, valor, data_mov,
                          descricao="", id=None, pago=None):
        if id:
            if pago is None:
                self.db.executar(
                    """UPDATE lancamentos SET conta_id = ?, categoria_id = ?, tipo = ?,
                       valor = ?, data_mov = ?, descricao = ?
                       WHERE id = ? AND usuario_id = ?""",
                    (conta_id, categoria_id, tipo, valor, data_mov, descricao,
                     id, self.usuario_id))
            else:
                self.db.executar(
                    """UPDATE lancamentos SET conta_id = ?, categoria_id = ?, tipo = ?,
                       valor = ?, data_mov = ?, descricao = ?, pago = ?
                       WHERE id = ? AND usuario_id = ?""",
                    (conta_id, categoria_id, tipo, valor, data_mov, descricao,
                     1 if pago in (1, True) else 0, id, self.usuario_id))
                if pago in (1, True):
                    linhas = self.db.consultar(
                        "SELECT recorrencia_id FROM lancamentos "
                        "WHERE id = ? AND usuario_id = ?",
                        (id, self.usuario_id))
                    if linhas and linhas[0]["recorrencia_id"]:
                        rec = self._carregar_recorrencia(linhas[0]["recorrencia_id"])
                        if rec:
                            self._processar_ocorrencias(rec, date.today())
            return id
        return self.db.inserir(
            """INSERT INTO lancamentos
               (usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
                descricao, pago)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
             descricao, 1 if pago in (1, True) else 0 if pago is not None else 1))

    def alternar_pago(self, id):
        self.db.executar(
            """UPDATE lancamentos SET pago = CASE WHEN pago = 1 THEN 0 ELSE 1 END
               WHERE id = ? AND usuario_id = ?""",
            (id, self.usuario_id))
        linhas = self.db.consultar(
            "SELECT pago, recorrencia_id FROM lancamentos WHERE id = ? AND usuario_id = ?",
            (id, self.usuario_id))
        novo = 1 if linhas and linhas[0]["pago"] in (1, True) else 0
        if novo == 1 and linhas[0]["recorrencia_id"]:
            rec = self._carregar_recorrencia(linhas[0]["recorrencia_id"])
            if rec:
                self._processar_ocorrencias(rec, date.today())
        return novo

    def baixar_em_lote(self, ids):
        baixados = ignorados = 0
        recs_disparadas = set()
        for lanc_id in ids:
            linhas = self.db.consultar(
                """SELECT pago, recorrencia_id FROM lancamentos
                   WHERE id = ? AND usuario_id = ?""",
                (lanc_id, self.usuario_id))
            if not linhas or linhas[0]["pago"] in (1, True):
                ignorados += 1
                continue
            self.db.executar(
                "UPDATE lancamentos SET pago = 1 WHERE id = ? AND usuario_id = ?",
                (lanc_id, self.usuario_id))
            baixados += 1
            rec_id = linhas[0]["recorrencia_id"]
            if rec_id and rec_id not in recs_disparadas:
                recs_disparadas.add(rec_id)
                rec = self._carregar_recorrencia(rec_id)
                if rec:
                    self._processar_ocorrencias(rec, date.today())
        return baixados, ignorados

    def excluir_lancamento(self, id):
        self.db.executar("DELETE FROM lancamentos WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    # ===================== DASHBOARD / RELATÓRIOS =====================
    def _total_faturas_aberto(self) -> float:
        """Soma de TODAS as parcelas em aberto de todos os cartões."""
        r = self.db.consultar(
            """SELECT COALESCE(SUM(valor), 0) AS t FROM compras_cartao
               WHERE usuario_id = ? AND pago = 0""",
            (self.usuario_id,))[0]
        return _num(r["t"])

    def kpis_mes(self, ano, mes):
        ini, fim = primeiro_dia(ano, mes), ultimo_dia(ano, mes)
        u = self.usuario_id
        sql = """
            SELECT
              (SELECT COALESCE(SUM(saldo_inicial), 0) FROM contas
                 WHERE usuario_id = ?) AS base,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE 0 END), 0)
                 FROM lancamentos WHERE usuario_id = ?) AS ent_todas,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END), 0)
                 FROM lancamentos WHERE usuario_id = ?) AS sai_todas,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE 0 END), 0)
                 FROM lancamentos WHERE usuario_id = ? AND pago = 1) AS ent_pagas,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END), 0)
                 FROM lancamentos WHERE usuario_id = ? AND pago = 1) AS sai_pagas,
              (SELECT COALESCE(SUM(valor), 0) FROM lancamentos
                 WHERE usuario_id = ? AND pago = 0 AND tipo = 'entrada'
                 AND data_mov BETWEEN ? AND ?) AS a_receber_mes,
              (SELECT COALESCE(SUM(valor), 0) FROM lancamentos
                 WHERE usuario_id = ? AND pago = 0 AND tipo = 'saida'
                 AND data_mov BETWEEN ? AND ?) AS a_pagar_mes,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'entrada' THEN valor ELSE 0 END), 0)
                 FROM lancamentos
                 WHERE usuario_id = ? AND pago = 1 AND data_mov BETWEEN ? AND ?) AS receitas_mes,
              (SELECT COALESCE(SUM(CASE WHEN tipo = 'saida' THEN valor ELSE 0 END), 0)
                 FROM lancamentos
                 WHERE usuario_id = ? AND pago = 1 AND data_mov BETWEEN ? AND ?) AS despesas_mes,
              (SELECT COUNT(*) FROM lancamentos
                 WHERE usuario_id = ? AND data_mov BETWEEN ? AND ?) AS qtd_mes,
              (SELECT COUNT(*) FROM lancamentos
                 WHERE usuario_id = ? AND pago = 0 AND data_mov BETWEEN ? AND ?) AS pend_mes
        """
        r = self.db.consultar(
            sql, (u, u, u, u, u,
                  u, ini, fim,
                  u, ini, fim,
                  u, ini, fim,
                  u, ini, fim,
                  u, ini, fim,
                  u, ini, fim))[0]
        base = _num(r["base"])
        saldo_total = base + _num(r["ent_pagas"]) - _num(r["sai_pagas"])
        # O saldo previsto absorve também as faturas de cartão em aberto:
        # é o "onde vou parar" com todas as dívidas futuras liquidadas.
        faturas_aberto = self._total_faturas_aberto()
        saldo_previsto = (base + _num(r["ent_todas"]) - _num(r["sai_todas"])
                          - faturas_aberto)
        return KpiMes(
            saldo_total=saldo_total,
            saldo_previsto=saldo_previsto,
            receitas_mes=_num(r["receitas_mes"]),
            despesas_mes=_num(r["despesas_mes"]),
            a_pagar_mes=_num(r["a_pagar_mes"]),
            a_receber_mes=_num(r["a_receber_mes"]),
            faturas_mes=self.faturas_vencendo_mes(ano, mes),
            lancamentos_mes=int(r["qtd_mes"]),
            pendentes_mes=int(r["pend_mes"]))

    def gastos_por_categoria(self, ano, mes, tipo="saida", somente_pagos=True):
        ini, fim = primeiro_dia(ano, mes), ultimo_dia(ano, mes)
        sql = """
            SELECT g.nome, g.cor, SUM(l.valor) AS total
            FROM lancamentos l
            JOIN categorias g ON g.id = l.categoria_id
            WHERE l.usuario_id = ? AND l.tipo = ? AND l.data_mov BETWEEN ? AND ?
        """
        params = [self.usuario_id, tipo, ini, fim]
        if somente_pagos:
            sql += " AND l.pago = 1"
        sql += " GROUP BY g.nome, g.cor ORDER BY total DESC"
        return [{"nome": r["nome"], "cor": r["cor"], "total": _num(r["total"])}
                for r in self.db.consultar(sql, params)]

    def resumo_mensal(self, filtros: dict = None):
        filtros = filtros or {}
        where, params = self._filtros_sql(filtros)
        expr = self.db.expr_mes("l.data_mov")
        sql = f"""
            SELECT {expr} AS mes,
                   COALESCE(SUM(CASE WHEN l.tipo = 'entrada' THEN l.valor ELSE 0 END), 0) AS entradas,
                   COALESCE(SUM(CASE WHEN l.tipo = 'saida' THEN l.valor ELSE 0 END), 0) AS saidas
            FROM lancamentos l
            WHERE {where}
            GROUP BY {expr}
            ORDER BY mes
        """
        return [{"mes": r["mes"], "entradas": _num(r["entradas"]), "saidas": _num(r["saidas"])}
                for r in self.db.consultar(sql, params)]

    def evolucao_mensal(self, qtde_meses=6, ref_ano=None, ref_mes=None):
        hoje = date.today()
        ano_ref = ref_ano or hoje.year
        mes_ref = ref_mes or hoje.month
        fim = ultimo_dia(ano_ref, mes_ref)
        ano, mes = ano_ref, mes_ref
        for _ in range(qtde_meses - 1):
            ano, mes = mes_anterior(ano, mes)
        ini = primeiro_dia(ano, mes)
        por_mes = {r["mes"]: r for r in self.resumo_mensal(
            {"data_ini": ini, "data_fim": fim, "pago": 1})}
        serie = []
        ya, ma = ano, mes
        for _ in range(qtde_meses):
            chave = f"{ya:04d}-{ma:02d}"
            r = por_mes.get(chave, {"entradas": 0.0, "saidas": 0.0})
            serie.append((fmt_mes_curto(chave), r["entradas"], r["saidas"]))
            ya, ma = avancar_mes(ya, ma)
        return serie

    # ===================== RECORRÊNCIAS (v2) =====================
    def listar_recorrencias(self, apenas_ativas=False):
        sql = """
            SELECT r.id, r.descricao, r.conta_id, c.nome AS conta_nome,
                   r.categoria_id, g.nome AS categoria_nome,
                   r.tipo, r.valor, r.frequencia, r.data_inicio, r.data_fim,
                   r.qtd_vezes, r.geradas, r.ultimo_gerado_data, r.ativo
            FROM recorrencias r
            JOIN contas c ON c.id = r.conta_id
            JOIN categorias g ON g.id = r.categoria_id
            WHERE r.usuario_id = ?
        """
        if apenas_ativas:
            sql += " AND r.ativo = 1"
        sql += " ORDER BY r.descricao"

        recs = []
        for r in self.db.consultar(sql, (self.usuario_id,)):
            frequencia = r["frequencia"] or "mensal"
            if frequencia not in FREQUENCIAS:
                frequencia = "mensal"
            data_inicio = _para_iso(r["data_inicio"]) if r["data_inicio"] else None
            data_fim = _para_iso(r["data_fim"]) if r["data_fim"] else None
            ultimo = _para_iso(r["ultimo_gerado_data"]) if r["ultimo_gerado_data"] else None
            qtd_vezes = int(r["qtd_vezes"]) if r["qtd_vezes"] is not None else None
            geradas = int(r["geradas"] or 0)

            if ultimo:
                proxima = _avancar_ocorrencia(_para_data(ultimo), frequencia)
            else:
                proxima = _para_data(data_inicio)
            proxima_iso = proxima.isoformat() if proxima else None

            concluida = False
            if data_fim and proxima and proxima > _para_data(data_fim):
                concluida = True
            if qtd_vezes is not None and geradas >= qtd_vezes:
                concluida = True

            rec = Recorrencia(
                id=r["id"], descricao=r["descricao"], conta_id=r["conta_id"],
                conta_nome=r["conta_nome"], categoria_id=r["categoria_id"],
                categoria_nome=r["categoria_nome"], tipo=r["tipo"],
                valor=_num(r["valor"]), frequencia=frequencia,
                data_inicio=data_inicio, data_fim=data_fim,
                qtd_vezes=qtd_vezes, geradas=geradas, ultimo_gerado=ultimo,
                proxima_data=proxima_iso, concluida=concluida)
            rec.ativo = 1 if r["ativo"] in (1, True) else 0
            recs.append(rec)
        return recs

    def progresso_recorrencias(self):
        linhas = self.db.consultar(
            """SELECT r.id, r.qtd_vezes, r.geradas,
                      (SELECT COUNT(*) FROM lancamentos l
                        WHERE l.recorrencia_id = r.id AND l.pago = 1) AS pagas
               FROM recorrencias r
               WHERE r.usuario_id = ?""",
            (self.usuario_id,))
        progresso = {}
        for r in linhas:
            geradas = int(r["geradas"] or 0)
            qtd = int(r["qtd_vezes"]) if r["qtd_vezes"] is not None else None
            restantes = max(0, qtd - geradas) if qtd is not None else None
            progresso[r["id"]] = {"geradas": geradas,
                                  "pagas": int(r["pagas"] or 0),
                                  "restantes": restantes}
        return progresso

    def _carregar_recorrencia(self, recorrencia_id: int) -> Optional[Recorrencia]:
        for rec in self.listar_recorrencias():
            if rec.id == recorrencia_id:
                return rec
        return None

    def _inserir_ocorrencia(self, rec: Recorrencia, data: date):
        self.db.executar(
            """INSERT INTO lancamentos
               (usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
                descricao, pago, recorrencia_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (self.usuario_id, rec.conta_id, rec.categoria_id, rec.tipo,
             rec.valor, data.isoformat(),
             f"{rec.descricao} (recorrente)", rec.id), commitar=False)
        self.db.executar(
            """UPDATE recorrencias
               SET ultimo_gerado_data = ?, geradas = geradas + 1
               WHERE id = ?""",
            (data.isoformat(), rec.id), commitar=False)

    def _processar_ocorrencias(self, rec: Recorrencia, hoje: date) -> int:
        if not rec.ativo or rec.concluida or not rec.data_inicio:
            return 0
        inicio = _para_data(rec.data_inicio)
        if not inicio:
            return 0
        data_fim = _para_data(rec.data_fim) if rec.data_fim else None
        qtd_vezes = rec.qtd_vezes
        ultima = _para_data(rec.ultimo_gerado) if rec.ultimo_gerado else None

        data = _avancar_ocorrencia(ultima, rec.frequencia) if ultima else inicio
        gerados = 0
        while True:
            if data_fim and data > data_fim:
                break
            if qtd_vezes is not None and rec.geradas >= qtd_vezes:
                break
            if data > hoje:
                if ultima and ultima > hoje:
                    break
                self._inserir_ocorrencia(rec, data)
                gerados += 1
                break
            self._inserir_ocorrencia(rec, data)
            gerados += 1
            ultima = data
            data = _avancar_ocorrencia(data, rec.frequencia)
        self.db.confirmar()
        return gerados

    def salvar_recorrencia(self, descricao, conta_id, categoria_id, tipo, valor,
                           frequencia="mensal", data_inicio=None, data_fim=None,
                           qtd_vezes=None, ativo=1, id=None):
        if frequencia not in FREQUENCIAS:
            frequencia = "mensal"
        if data_inicio and len(data_inicio) >= 10:
            mes_inicio_legado = data_inicio[:7]
            dia_legado = int(data_inicio[8:10])
        else:
            mes_inicio_legado = ""
            dia_legado = 1
        if id:
            self.db.executar(
                """UPDATE recorrencias SET descricao = ?, conta_id = ?, categoria_id = ?,
                   tipo = ?, valor = ?, frequencia = ?, data_inicio = ?,
                   data_fim = ?, qtd_vezes = ?, ativo = ?,
                   mes_inicio = ?, dia_do_mes = ?
                   WHERE id = ? AND usuario_id = ?""",
                (descricao, conta_id, categoria_id, tipo, valor, frequencia,
                 data_inicio or None, data_fim or None,
                 int(qtd_vezes) if qtd_vezes else None,
                 int(ativo), mes_inicio_legado, dia_legado,
                 id, self.usuario_id))
            return id
        return self.db.inserir(
            """INSERT INTO recorrencias
               (usuario_id, descricao, conta_id, categoria_id, tipo, valor,
                frequencia, data_inicio, data_fim, qtd_vezes, geradas, ativo,
                mes_inicio, dia_do_mes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
            (self.usuario_id, descricao, conta_id, categoria_id, tipo, valor,
             frequencia, data_inicio or None, data_fim or None,
             int(qtd_vezes) if qtd_vezes else None, int(ativo),
             mes_inicio_legado, dia_legado))

    def excluir_recorrencia(self, id):
        self.db.executar("DELETE FROM recorrencias WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    def gerar_pendentes(self, hoje=None):
        hoje = hoje or date.today()
        gerados = 0
        puladas = []
        for rec in self.listar_recorrencias(apenas_ativas=True):
            n = self._processar_ocorrencias(rec, hoje)
            if n == 0 and (not rec.ativo or rec.concluida or not rec.data_inicio
                           or not _para_data(rec.data_inicio)):
                puladas.append(rec.descricao)
            gerados += n
        self.db.confirmar()
        return gerados, puladas

    # ===================== CARTÃO DE CRÉDITO =====================
    @staticmethod
    def fatura_de(data_compra: str, dia_fechamento: int) -> str:
        """Fatura ('YYYY-MM', mês de VENCIMENTO) em que a compra cai.

        Regra de ouro: compra com dia <= fechamento fecha no mês corrente e
        vence no mês seguinte (fatura = compra + 1 mês); dia > fechamento
        vence no mês seguinte ao seguinte (fatura = compra + 2 meses).
        """
        d = _para_data(data_compra)
        if not d:
            return ""
        meses = 1 if d.day <= dia_fechamento else 2
        v = _mesmo_dia_proximo_mes(d, meses)
        return f"{v.year:04d}-{v.month:02d}"

    @staticmethod
    def vencimento_de_fatura(fatura: str, dia_vencimento: int) -> str:
        """Data ISO do vencimento da fatura 'YYYY-MM' (dia ajustado ao mês)."""
        if not fatura or len(fatura) < 7:
            return ""
        ano, mes = int(fatura[:4]), int(fatura[5:7])
        dia = max(1, min(int(dia_vencimento), dias_no_mes(ano, mes)))
        return f"{ano:04d}-{mes:02d}-{dia:02d}"

    def listar_cartoes(self, apenas_ativas=False):
        """Lista os cartões do usuário com total em aberto e limite disponível."""
        sql = """
            SELECT k.id, k.nome, k.conta_id, c.nome AS conta_nome,
                   k.dia_fechamento, k.dia_vencimento, k.limite_total, k.ativo,
                   (SELECT COALESCE(SUM(p.valor), 0) FROM compras_cartao p
                     WHERE p.cartao_id = k.id AND p.pago = 0) AS total_aberto
            FROM cartoes_credito k
            JOIN contas c ON c.id = k.conta_id
            WHERE k.usuario_id = ?
        """
        if apenas_ativas:
            sql += " AND k.ativo = 1"
        sql += " ORDER BY k.nome"

        cartoes = []
        for r in self.db.consultar(sql, (self.usuario_id,)):
            cartao = CartaoCredito(
                id=r["id"], nome=r["nome"], conta_id=r["conta_id"],
                conta_nome=r["conta_nome"],
                dia_fechamento=int(r["dia_fechamento"]),
                dia_vencimento=int(r["dia_vencimento"]),
                limite_total=_num(r["limite_total"]))
            cartao.total_aberto = _num(r["total_aberto"])
            cartao.limite_disponivel = cartao.limite_total - cartao.total_aberto
            cartao.ativo = 1 if r["ativo"] in (1, True) else 0
            cartoes.append(cartao)
        return cartoes

    def salvar_cartao(self, nome, conta_id, dia_fechamento, dia_vencimento,
                      limite_total, ativo=1, id=None):
        if id:
            self.db.executar(
                """UPDATE cartoes_credito SET nome = ?, conta_id = ?,
                   dia_fechamento = ?, dia_vencimento = ?, limite_total = ?, ativo = ?
                   WHERE id = ? AND usuario_id = ?""",
                (nome, conta_id, int(dia_fechamento), int(dia_vencimento),
                 limite_total, int(ativo), id, self.usuario_id))
            return id
        return self.db.inserir(
            """INSERT INTO cartoes_credito
               (usuario_id, nome, conta_id, dia_fechamento, dia_vencimento,
                limite_total, ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (self.usuario_id, nome, conta_id, int(dia_fechamento),
             int(dia_vencimento), limite_total, int(ativo)))

    def excluir_cartao(self, id):
        """Exclui o cartão — bloqueado se houver parcelas em aberto (a
        obrigação existe e precisa ser paga ou transferida primeiro)."""
        n = self.db.consultar(
            """SELECT COUNT(*) AS t FROM compras_cartao
               WHERE cartao_id = ? AND usuario_id = ? AND pago = 0""",
            (id, self.usuario_id))[0]["t"]
        if n:
            raise ErroRegraNegocio(
                f"O cartão tem {n} parcela(s) em aberto. Quite ou exclua as "
                "compras pendentes antes de excluir o cartão.")
        self.db.executar("DELETE FROM compras_cartao WHERE cartao_id = ? AND usuario_id = ?",
                         (id, self.usuario_id))
        self.db.executar("DELETE FROM cartoes_credito WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    def criar_compra(self, cartao_id, categoria_id, descricao, data_compra,
                     valor_total, total_parcelas=1, fatura=None):
        """Registra uma compra no cartão, gerando 1 linha por PARCELA.

        A fatura padrão é calculada pela regra do fechamento (fatura_de);
        o parâmetro fatura permite escolher outra (casos excepcionais) e
        vale para a PRIMEIRA parcela — as seguintes avançam 1 fatura/mês.
        O valor por parcela é valor_total / total_parcelas (a diferença de
        centavos da divisão fica na 1ª parcela, para fechar o total).
        Retorna o nº de parcelas gravadas.
        """
        cartoes = [c for c in self.listar_cartoes() if c.id == cartao_id]
        if not cartoes:
            raise ErroRegraNegocio("Cartão não encontrado.")
        cartao = cartoes[0]
        total_parcelas = max(1, int(total_parcelas))
        if valor_total <= 0:
            raise ErroRegraNegocio("Informe um valor maior que zero.")

        fatura_base = fatura or self.fatura_de(data_compra, cartao.dia_fechamento)
        if not fatura_base or len(fatura_base) < 7:
            raise ErroRegraNegocio("Não foi possível determinar a fatura da compra.")

        valor_base = round(float(valor_total) / total_parcelas, 2)
        primeira = round(valor_total - valor_base * (total_parcelas - 1), 2)

        grupo_id = int(date.today().strftime("%Y%m%d%H%M%S")) % 10_000_000_000
        with self.db.transacao():
            for i in range(total_parcelas):
                # Avança i faturas a partir da base (1 fatura por mês).
                ano, mes = int(fatura_base[:4]), int(fatura_base[5:7])
                for _ in range(i):
                    ano, mes = avancar_mes(ano, mes)
                fatura_i = f"{ano:04d}-{mes:02d}"
                self.db.executar(
                    """INSERT INTO compras_cartao
                       (usuario_id, cartao_id, categoria_id, grupo_id, descricao,
                        data_compra, valor, parcela, total_parcelas, fatura, pago)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (self.usuario_id, cartao_id, categoria_id, grupo_id,
                     descricao, data_compra,
                     primeira if i == 0 else valor_base,
                     i + 1, total_parcelas, fatura_i), commitar=False)
        return total_parcelas

    def listar_compras(self, filtros: dict = None):
        """Lista parcelas do usuário. Filtros: cartao_id, fatura, pago,
        busca, categoria_id."""
        filtros = filtros or {}
        where = ["p.usuario_id = ?"]
        params = [self.usuario_id]
        if filtros.get("cartao_id"):
            where.append("p.cartao_id = ?")
            params.append(filtros["cartao_id"])
        if filtros.get("categoria_id"):
            where.append("p.categoria_id = ?")
            params.append(filtros["categoria_id"])
        if filtros.get("fatura"):
            where.append("p.fatura = ?")
            params.append(filtros["fatura"])
        if filtros.get("pago") is not None:
            where.append("p.pago = ?")
            params.append(1 if filtros["pago"] in (1, True) else 0)
        if filtros.get("busca"):
            where.append("p.descricao LIKE ?")
            params.append(f"%{filtros['busca']}%")
        sql = f"""
            SELECT p.id, p.cartao_id, k.nome AS cartao_nome, p.categoria_id,
                   g.nome AS categoria_nome, g.cor AS categoria_cor,
                   p.grupo_id, p.descricao, p.data_compra, p.valor,
                   p.parcela, p.total_parcelas, p.fatura, p.pago, p.lancamento_id
            FROM compras_cartao p
            JOIN cartoes_credito k ON k.id = p.cartao_id
            JOIN categorias g ON g.id = p.categoria_id
            WHERE {" AND ".join(where)}
            ORDER BY p.fatura, p.parcela
        """
        compras = []
        for r in self.db.consultar(sql, params):
            c = CompraCartao(
                id=r["id"], cartao_id=r["cartao_id"], cartao_nome=r["cartao_nome"],
                categoria_id=r["categoria_id"], categoria_nome=r["categoria_nome"],
                categoria_cor=r["categoria_cor"], grupo_id=r["grupo_id"],
                descricao=r["descricao"] or "",
                data_compra=_para_iso(r["data_compra"]), valor=_num(r["valor"]),
                parcela=int(r["parcela"]), total_parcelas=int(r["total_parcelas"]),
                fatura=r["fatura"],
                pago=1 if r["pago"] in (1, True) else 0,
                lancamento_id=r["lancamento_id"])
            compras.append(c)
        return compras

    def excluir_compra(self, grupo_id):
        """Exclui TODAS as parcelas NÃO PAGAS de uma compra (pelo grupo).
        Parcelas já pagas (faturas quitadas) permanecem no histórico."""
        n = self.db.consultar(
            """SELECT COUNT(*) AS t FROM compras_cartao
               WHERE grupo_id = ? AND usuario_id = ? AND pago = 0""",
            (grupo_id, self.usuario_id))[0]["t"]
        if not n:
            raise ErroRegraNegocio(
                "Não há parcelas em aberto nesta compra para excluir.")
        self.db.executar(
            """DELETE FROM compras_cartao
               WHERE grupo_id = ? AND usuario_id = ? AND pago = 0""",
            (grupo_id, self.usuario_id))
        return n

    def resumo_faturas(self, cartao_id=None, apenas_abertas=True):
        """Faturas com saldo em aberto (mais antigas primeiro).

        Retorna [{fatura, vencimento, total, cartao_id, cartao_nome, qtde}] —
        alimenta o diálogo de pagamento e o card 'Faturas a pagar (mês)'.
        """
        where = ["p.usuario_id = ?", "p.pago = 0"]
        params = [self.usuario_id]
        if cartao_id:
            where.append("p.cartao_id = ?")
            params.append(cartao_id)
        sql = f"""
            SELECT p.cartao_id, k.nome AS cartao_nome, p.fatura,
                   k.dia_vencimento,
                   SUM(p.valor) AS total, COUNT(*) AS qtde
            FROM compras_cartao p
            JOIN cartoes_credito k ON k.id = p.cartao_id
            WHERE {" AND ".join(where)}
            GROUP BY p.cartao_id, k.nome, p.fatura, k.dia_vencimento
            ORDER BY p.fatura
        """
        faturas = []
        for r in self.db.consultar(sql, params):
            faturas.append({
                "cartao_id": r["cartao_id"], "cartao_nome": r["cartao_nome"],
                "fatura": r["fatura"],
                "vencimento": self.vencimento_de_fatura(
                    r["fatura"], int(r["dia_vencimento"])),
                "total": _num(r["total"]), "qtde": int(r["qtde"])})
        return faturas

    def faturas_vencendo_mes(self, ano, mes) -> float:
        """Total em aberto das faturas que VENCEM no mês informado —
        alimenta o card do dashboard (previsão de caixa do mês)."""
        ini, fim = primeiro_dia(ano, mes), ultimo_dia(ano, mes)
        total = 0.0
        for f in self.resumo_faturas(apenas_abertas=True):
            venc = _para_data(f["vencimento"])
            if venc and ini <= f["vencimento"] <= fim:
                total += f["total"]
        return total

    def pagar_fatura(self, cartao_id, fatura, conta_id, categoria_id, data_mov,
                     descricao=""):
        """Paga UMA fatura do cartão (atômico):

        1. Gera UM lançamento de saída PAGO na conta informada (o caixa
           se move uma única vez).
        2. Marca as parcelas em aberto da fatura como pagas, com link ao
           lançamento (rastreabilidade completa).

        Retorna (id do lançamento, total pago, parcelas quitadas).
        """
        pendentes = self.db.consultar(
            """SELECT id, COALESCE(SUM(valor), 0) AS total FROM compras_cartao
               WHERE cartao_id = ? AND fatura = ? AND usuario_id = ? AND pago = 0""",
            (cartao_id, fatura, self.usuario_id))
        if not pendentes:
            raise ErroRegraNegocio("Não há parcelas em aberto nesta fatura.")
        total = _num(pendentes[0]["total"])
        if total <= 0:
            raise ErroRegraNegocio("Não há valor a pagar nesta fatura.")

        cartoes = [c for c in self.listar_cartoes() if c.id == cartao_id]
        cartao_nome = cartoes[0].nome if cartoes else "Cartão"
        desc = (descricao.strip()
                or f"Fatura {cartao_nome} — {fmt_mes_curto(fatura)}")
        lanc_id = self.db.inserir(
            """INSERT INTO lancamentos
               (usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
                descricao, pago)
               VALUES (?, ?, ?, 'saida', ?, ?, ?, 1)""",
            (self.usuario_id, conta_id, categoria_id, total, data_mov, desc))
        self.db.executar(
            """UPDATE compras_cartao SET pago = 1, lancamento_id = ?
               WHERE cartao_id = ? AND fatura = ? AND usuario_id = ? AND pago = 0""",
            (lanc_id, cartao_id, fatura, self.usuario_id))
        return lanc_id, total, len(pendentes)