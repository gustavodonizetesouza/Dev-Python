"""Camada de conexão com o banco — abstração multi-banco.

Fase 1: SQLite (arquivo local). Fase 2: SQL Server (pyodbc).
Trocar de banco é só mudar a chave "banco" no config.json —
o restante da aplicação usa sempre a mesma interface.

Caminhos: o config.json e o arquivo do SQLite são resolvidos contra a
raiz do projeto (core.util.DIR_BASE), nunca contra o CWD — o banco
nasce sempre dentro da pasta do projeto.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.util import CAMINHO_CONFIG, DIR_BASE

DIALETO_SQLITE = "sqlite"
DIALETO_SQLSERVER = "mssql"


class BancoDados:
    """Encapsula a conexão ativa e expõe helpers portáveis de SQL."""

    def __init__(self, conn, dialeto: str, descricao: str = ""):
        self.conn = conn
        self.dialeto = dialeto
        self.descricao = descricao

    # ---------- helpers portáveis ----------
    def expr_mes(self, coluna: str) -> str:
        """Expressão SQL que extrai 'YYYY-MM' de uma coluna de data."""
        if self.dialeto == DIALETO_SQLITE:
            return f"substr({coluna}, 1, 7)"
        return f"FORMAT({coluna}, 'yyyy-MM')"

    # ---------- operações básicas ----------
    def consultar(self, sql, params=()):
        """SELECT → lista de dicionários."""
        cur = self.conn.cursor()
        cur.execute(sql, params)
        colunas = [d[0] for d in cur.description] if cur.description else []
        linhas = [dict(zip(colunas, linha)) for linha in cur.fetchall()]
        cur.close()
        return linhas

    def executar(self, sql, params=(), commitar=True):
        """INSERT/UPDATE/DELETE simples."""
        cur = self.conn.cursor()
        cur.execute(sql, params)
        afetadas = cur.rowcount
        cur.close()
        if commitar:
            self.conn.commit()
        return afetadas

    def inserir(self, sql, params=(), commitar=True):
        """INSERT retornando o id gerado (portável entre os dois bancos)."""
        cur = self.conn.cursor()
        if self.dialeto == DIALETO_SQLSERVER:
            cur.execute("SET NOCOUNT ON; " + sql +
                        "; SELECT CAST(SCOPE_IDENTITY() AS INT) AS novo_id;", params)
            linha = cur.fetchone()
            if linha is None:
                try:
                    cur.nextset()
                except Exception:
                    pass
                linha = cur.fetchone()
            novo_id = int(linha[0]) if linha and linha[0] is not None else None
        else:
            cur.execute(sql, params)
            novo_id = cur.lastrowid
        cur.close()
        if commitar:
            self.conn.commit()
        return novo_id

    def confirmar(self):
        self.conn.commit()

    def desfazer(self):
        self.conn.rollback()

    @contextmanager
    def transacao(self):
        """Garante atomicidade de várias operações."""
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise


class FabricaConexao:
    """Lê o config.json (sempre da raiz do projeto) e devolve a conexão ativa."""

    @staticmethod
    def criar(caminho_config=None) -> BancoDados:
        caminho_cfg = Path(
            caminho_config) if caminho_config else CAMINHO_CONFIG

        cfg = {}
        if caminho_cfg.exists():
            with open(caminho_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)

        tipo = str(cfg.get("banco", "sqlite")).lower()

        if tipo == "sqlite":
            secao = cfg.get("sqlite", {})
            arquivo = secao.get("arquivo", "data/gestor_financeiro.db")
            caminho_db = Path(arquivo)
            if not caminho_db.is_absolute():
                caminho_db = DIR_BASE / caminho_db
            caminho_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(caminho_db))
            conn.execute("PRAGMA foreign_keys = ON")
            return BancoDados(conn, DIALETO_SQLITE, f"SQLite — {caminho_db}")

        if tipo in ("sqlserver", "mssql"):
            import pyodbc  # import tardio: só exige pyodbc na fase SQL Server
            secao = cfg.get("sqlserver", {})
            driver = secao.get("driver", "ODBC Driver 17 for SQL Server")
            servidor = secao.get("servidor", "localhost")
            banco = secao.get("banco", "GestorFinanceiro")
            partes = [f"DRIVER={{{driver}}}", f"SERVER={servidor}", f"DATABASE={banco}",
                      "TrustServerCertificate=yes"]
            if secao.get("trusted_connection", True):
                partes.append("Trusted_Connection=yes")
            else:
                partes.append(f"UID={secao.get('usuario', '')}")
                partes.append(f"PWD={secao.get('senha', '')}")
            conn = pyodbc.connect(";".join(partes))
            return BancoDados(conn, DIALETO_SQLSERVER, f"SQL Server — {servidor}/{banco}")

        raise ValueError(f"Banco desconhecido no config.json: {tipo}")
