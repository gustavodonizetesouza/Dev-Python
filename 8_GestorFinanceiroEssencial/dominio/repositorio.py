"""Modelos + repositórios — SQL portável (SQLite e SQL Server) com isolamento
multiusuário e controle de contas a pagar/receber.

Dois repositórios:
- RepositorioUsuarios: cadastro, autenticação e administração de usuários.
- Repositorio: acesso a dados do usuário logado — recebe o usuario_id no
  construtor e TODAS as consultas filtram por ele (multi-tenancy lógico).

Contas a pagar/receber: cada lançamento tem a flag `pago` (1 = pago/recebido,
0 = pendente). O saldo efetivo considera apenas lançamentos pagos; o saldo
previsto considera tudo (como se todas as pendências liquidassem). Os KPIs
separam realizado (pagos) de previsto (pendentes do mês). Lançamentos gerados
por recorrência nascem PENDENTES: a recorrência cria a obrigação e o usuário
marca como pago ao efetivar.

O admin gerencia cadastros (RepositorioUsuarios), mas NÃO acessa dados
financeiros de outros usuários: o isolamento por usuario_id vale para todos,
inclusive admins.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from core.conexao import BancoDados
from core.schema import CATEGORIAS_INICIAIS
from core.seguranca import hash_senha, validar_senha_forte, verificar_senha
from core.util import (avancar_mes, dias_no_mes, fmt_mes_curto, mes_anterior,
                       primeiro_dia, ultimo_dia)


class ErroRegraNegocio(Exception):
    """Violação de regra de negócio (e-mail duplicado, categoria em uso etc.)."""


# ----------------------------- modelos -----------------------------
@dataclass
class Usuario:
    id: Optional[int] = None
    nome: str = ""
    email: str = ""
    senha_hash: str = ""
    papel: str = "usuario"       # 'admin' ou 'usuario'
    plano: str = "gratuito"      # dormente até a etapa de planos
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
    # 1 = pago/recebido; 0 = pendente (a pagar/receber)
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
    dia_do_mes: int = 1
    mes_inicio: str = ""
    ativo: int = 1
    ultimo_gerado: Optional[str] = None


@dataclass
class KpiMes:
    # efetivo: base + pagos - recebidos (todo o histórico)
    saldo_total: float = 0.0
    # previsto: base + tudo - tudo (pendências liquidadas)
    saldo_previsto: float = 0.0
    receitas_mes: float = 0.0     # realizadas no mês (pagas)
    despesas_mes: float = 0.0     # realizadas no mês (pagas)
    a_pagar_mes: float = 0.0      # pendentes de saída no mês
    a_receber_mes: float = 0.0    # pendentes de entrada no mês
    lancamentos_mes: int = 0      # total de lançamentos do mês
    pendentes_mes: int = 0        # pendências do mês


def _num(valor) -> float:
    """Normaliza Decimal (SQL Server) / float (SQLite) / None."""
    return float(valor) if valor is not None else 0.0


def _para_iso(valor) -> str:
    """SQL Server devolve datetime.date; SQLite devolve str."""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()[:10]
    return valor or ""


# ----------------------- repositório de usuários -----------------------
class RepositorioUsuarios:
    """Cadastro, autenticação e administração de usuários.

    Regras:
    - O primeiro usuário cadastrado no banco torna-se automaticamente admin.
    - Cada novo usuário recebe suas 11 categorias padrão no cadastro.
    - O admin NUNCA pode se auto-desativar/auto-excluir e o sistema nunca
      fica sem administrador ativo.
    """

    def __init__(self, db: BancoDados):
        self.db = db

    # ---------- helpers ----------
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
        """Cria as 11 categorias padrão para o usuário recém-cadastrado."""
        for nome, tipo, cor in CATEGORIAS_INICIAIS:
            self.db.executar(
                "INSERT INTO categorias (usuario_id, nome, tipo, cor) VALUES (?, ?, ?, ?)",
                (usuario_id, nome, tipo, cor), commitar=False)

    # ---------- cadastro / autenticação ----------
    def criar_usuario(self, nome: str, email: str, senha: str) -> Usuario:
        """Cadastra o usuário e semeia suas categorias (atômico).

        O primeiro usuário do sistema torna-se admin. Erros de negócio
        (e-mail duplicado) levantam ErroRegraNegocio.
        """
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
        """Retorna o Usuario autenticado, None se credenciais inválidas.

        Levanta ErroRegraNegocio se a conta existir mas estiver desativada.
        """
        u = self.buscar_por_email(email)
        if u is None or not verificar_senha(senha, u.senha_hash):
            return None
        if not u.ativo:
            raise ErroRegraNegocio(
                "Esta conta está desativada. Procure o administrador do sistema.")
        return u

    # ---------- administração (página Usuários do admin) ----------
    def listar_usuarios(self):
        """Lista usuários para o painel admin (sem expor senha_hash)."""
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
        """Ativa/desativa um usuário. Retorna o novo estado (0/1)."""
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if usuario_id == solicitante_id:
            raise ErroRegraNegocio(
                "Você não pode desativar a sua própria conta.")
        if u.papel == "admin" and u.ativo and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível desativar o último administrador ativo do sistema.")
        novo = 0 if u.ativo else 1
        self.db.executar("UPDATE usuarios SET ativo = ? WHERE id = ?",
                         (novo, usuario_id))
        return novo

    def definir_papel(self, usuario_id: int, papel: str, solicitante_id: int):
        """Promove a admin ou rebaixa a usuário comum, com proteções."""
        if papel not in ("admin", "usuario"):
            raise ErroRegraNegocio("Papel inválido.")
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if usuario_id == solicitante_id and papel != "admin":
            raise ErroRegraNegocio(
                "Você não pode remover o seu próprio papel de admin.")
        if u.papel == "admin" and papel != "admin" and u.ativo \
                and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível rebaixar o último administrador ativo do sistema.")
        self.db.executar("UPDATE usuarios SET papel = ? WHERE id = ?",
                         (papel, usuario_id))

    def definir_plano(self, usuario_id: int, plano: str):
        """Reservado para a etapa de planos (dormente por ora)."""
        self.db.executar("UPDATE usuarios SET plano = ? WHERE id = ?",
                         (plano, usuario_id))

    def resetar_senha(self, usuario_id: int, nova_senha: str):
        """Redefine a senha de um usuário (ação do admin)."""
        erro = validar_senha_forte(nova_senha)
        if erro:
            raise ErroRegraNegocio(erro)
        if not self.buscar_por_id(usuario_id):
            raise ErroRegraNegocio("Usuário não encontrado.")
        self.db.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                         (hash_senha(nova_senha), usuario_id))

    def excluir_usuario(self, usuario_id: int, solicitante_id: int):
        """Exclui o usuário e TODO o seu mundo de dados (atômico)."""
        if usuario_id == solicitante_id:
            raise ErroRegraNegocio(
                "Você não pode excluir a própria conta logada.")
        u = self.buscar_por_id(usuario_id)
        if not u:
            raise ErroRegraNegocio("Usuário não encontrado.")
        if u.papel == "admin" and not self._outros_admins_ativos(usuario_id):
            raise ErroRegraNegocio(
                "Não é possível excluir o último administrador do sistema.")
        with self.db.transacao():
            self.db.executar(
                "DELETE FROM lancamentos WHERE usuario_id = ?",
                (usuario_id,), commitar=False)
            self.db.executar(
                "DELETE FROM recorrencias WHERE usuario_id = ?",
                (usuario_id,), commitar=False)
            self.db.executar(
                "DELETE FROM contas WHERE usuario_id = ?",
                (usuario_id,), commitar=False)
            self.db.executar(
                "DELETE FROM categorias WHERE usuario_id = ?",
                (usuario_id,), commitar=False)
            self.db.executar(
                "DELETE FROM usuarios WHERE id = ?",
                (usuario_id,), commitar=False)


# --------------------- repositório do usuário logado ---------------------
class Repositorio:
    """Acesso a dados do usuário logado.

    Todas as consultas, inserções, atualizações e exclusões são filtradas
    pelo usuario_id recebido no construtor — é o que garante que um usuário
    jamais veja ou altere dados de outro (inclusive o admin).
    """

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
            conta = Conta(id=linha["id"],
                          nome=linha["nome"], tipo=linha["tipo"])
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
        """Exclui a conta e todo o histórico vinculado do usuário (atômico)."""
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
        n_rec = self.db.consultar(
            """SELECT COUNT(*) AS t FROM recorrencias
               WHERE categoria_id = ? AND usuario_id = ?""",
            (id, self.usuario_id))[0]["t"]
        if n_lanc or n_rec:
            raise ErroRegraNegocio(
                f"A categoria está em uso por {n_lanc} lançamento(s) e {n_rec} recorrência(s).")
        self.db.executar("DELETE FROM categorias WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    # ===================== LANÇAMENTOS =====================
    def _filtros_sql(self, filtros: dict):
        # O filtro de usuário vem SEMPRE em primeiro lugar.
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
        # pago usa "is not None" porque 0 (pendente) é um valor válido.
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
        lancamentos = []
        for r in self.db.consultar(sql, params):
            lancamentos.append(Lancamento(
                id=r["id"], conta_id=r["conta_id"], conta_nome=r["conta_nome"],
                categoria_id=r["categoria_id"], categoria_nome=r["categoria_nome"],
                categoria_cor=r["categoria_cor"], tipo=r["tipo"], valor=_num(
                    r["valor"]),
                data_mov=_para_iso(r["data_mov"]), descricao=r["descricao"] or "",
                pago=1 if r["pago"] in (1, True) else 0,
                recorrencia_id=r["recorrencia_id"]))
        return lancamentos

    def salvar_lancamento(self, conta_id, categoria_id, tipo, valor, data_mov,
                          descricao="", id=None, pago=None):
        """Cria ou edita um lançamento.

        pago=None em edição preserva o status atual (compatibilidade);
        em criação, None equivale a pago=1 (entrada rápida já efetivada).
        """
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
            return id
        return self.db.inserir(
            """INSERT INTO lancamentos
               (usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
                descricao, pago)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
             descricao, 1 if pago in (1, True) else 0 if pago is not None else 1))

    def alternar_pago(self, id):
        """Alterna pago <-> pendente. Retorna o novo estado (1 pago, 0 pendente)."""
        self.db.executar(
            """UPDATE lancamentos SET pago = CASE WHEN pago = 1 THEN 0 ELSE 1 END
               WHERE id = ? AND usuario_id = ?""",
            (id, self.usuario_id))
        linhas = self.db.consultar(
            "SELECT pago FROM lancamentos WHERE id = ? AND usuario_id = ?",
            (id, self.usuario_id))
        return 1 if linhas and linhas[0]["pago"] in (1, True) else 0

    def excluir_lancamento(self, id):
        self.db.executar("DELETE FROM lancamentos WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    # ===================== DASHBOARD / RELATÓRIOS =====================
    def kpis_mes(self, ano, mes):
        """KPIs do mês separando realizado (pago) de previsto (pendente).

        - saldo_total: caixa efetivo = base + entradas pagas - saídas pagas.
        - saldo_previsto: cenário com TODAS as pendências liquidadas.
        - receitas_mes/despesas_mes: apenas pagos no mês (realizado).
        - a_receber_mes/a_pagar_mes: pendentes no mês (previsão de caixa).
        """
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
        saldo_previsto = base + _num(r["ent_todas"]) - _num(r["sai_todas"])
        return KpiMes(
            saldo_total=saldo_total,
            saldo_previsto=saldo_previsto,
            receitas_mes=_num(r["receitas_mes"]),
            despesas_mes=_num(r["despesas_mes"]),
            a_pagar_mes=_num(r["a_pagar_mes"]),
            a_receber_mes=_num(r["a_receber_mes"]),
            lancamentos_mes=int(r["qtd_mes"]),
            pendentes_mes=int(r["pend_mes"]))

    def gastos_por_categoria(self, ano, mes, tipo="saida", somente_pagos=True):
        """Total do mês por categoria. Por padrão, apenas realizados (pagos)."""
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
        """Série dos últimos N meses (realizado/pago): [(rótulo, entradas, saídas), ...]"""
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

    # ===================== RECORRÊNCIAS =====================
    def listar_recorrencias(self, apenas_ativas=False):
        sql = """
            SELECT r.id, r.descricao, r.conta_id, c.nome AS conta_nome,
                   r.categoria_id, g.nome AS categoria_nome,
                   r.tipo, r.valor, r.dia_do_mes, r.mes_inicio, r.ativo, r.ultimo_gerado
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
            rec = Recorrencia(
                id=r["id"], descricao=r["descricao"], conta_id=r["conta_id"],
                conta_nome=r["conta_nome"], categoria_id=r["categoria_id"],
                categoria_nome=r["categoria_nome"], tipo=r["tipo"], valor=_num(
                    r["valor"]),
                dia_do_mes=int(r["dia_do_mes"]),
                mes_inicio=str(r["mes_inicio"]).strip(),
                ultimo_gerado=str(r["ultimo_gerado"]).strip() if r["ultimo_gerado"] else None)
            rec.ativo = 1 if r["ativo"] in (1, True) else 0
            recs.append(rec)
        return recs

    def salvar_recorrencia(self, descricao, conta_id, categoria_id, tipo, valor,
                           dia_do_mes, mes_inicio, ativo=1, id=None):
        if id:
            self.db.executar(
                """UPDATE recorrencias SET descricao = ?, conta_id = ?, categoria_id = ?,
                   tipo = ?, valor = ?, dia_do_mes = ?, mes_inicio = ?, ativo = ?
                   WHERE id = ? AND usuario_id = ?""",
                (descricao, conta_id, categoria_id, tipo, valor, dia_do_mes,
                 mes_inicio, int(ativo), id, self.usuario_id))
            return id
        return self.db.inserir(
            """INSERT INTO recorrencias
               (usuario_id, descricao, conta_id, categoria_id, tipo, valor,
                dia_do_mes, mes_inicio, ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.usuario_id, descricao, conta_id, categoria_id, tipo, valor,
             dia_do_mes, mes_inicio, int(ativo)))

    def excluir_recorrencia(self, id):
        self.db.executar("DELETE FROM recorrencias WHERE id = ? AND usuario_id = ?",
                         (id, self.usuario_id))

    def gerar_pendentes(self, hoje=None):
        """Gera lançamentos das recorrências ATIVAS DO USUÁRIO até o mês corrente.

        Os lançamentos gerados nascem PENDENTES (pago = 0): a recorrência cria
        a obrigação (conta a pagar/receber) e o usuário marca como pago ao
        efetivar. Preenche os meses entre max(mes_inicio, ultimo_gerado + 1) e
        o mês corrente, ajustando o dia quando o mês é mais curto (ex.: dia 31
        em fev). Retorna (gerados, puladas).
        """
        hoje = hoje or date.today()
        mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"
        gerados = 0
        puladas = []
        for rec in self.listar_recorrencias(apenas_ativas=True):
            if not rec.ativo:
                continue
            inicio = str(rec.mes_inicio or "")[:7]
            if not inicio:
                puladas.append(rec.descricao)
                continue
            if rec.ultimo_gerado and rec.ultimo_gerado[:7] >= mes_atual:
                puladas.append(rec.descricao)
                continue
            partindo = max(inicio, (rec.ultimo_gerado or "")[:7])
            try:
                ya, ma = int(partindo[:4]), int(partindo[5:7])
            except ValueError:
                puladas.append(rec.descricao)
                continue
            if rec.ultimo_gerado:
                ya, ma = avancar_mes(ya, ma)
            while f"{ya:04d}-{ma:02d}" <= mes_atual:
                chave = f"{ya:04d}-{ma:02d}"
                dia = min(rec.dia_do_mes, dias_no_mes(ya, ma))
                data_mov = f"{ya:04d}-{ma:02d}-{dia:02d}"
                self.db.executar(
                    """INSERT INTO lancamentos
                       (usuario_id, conta_id, categoria_id, tipo, valor, data_mov,
                        descricao, pago, recorrencia_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (self.usuario_id, rec.conta_id, rec.categoria_id, rec.tipo,
                     rec.valor, data_mov, f"{rec.descricao} (recorrente)", rec.id),
                    commitar=False)
                self.db.executar(
                    "UPDATE recorrencias SET ultimo_gerado = ? WHERE id = ?",
                    (chave, rec.id), commitar=False)
                gerados += 1
                ya, ma = avancar_mes(ya, ma)
        self.db.confirmar()
        return gerados, puladas
