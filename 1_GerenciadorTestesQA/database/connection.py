"""
Camada de conexão com banco de dados.
Fase 1: SQLite (portátil, sem servidor).
Fase 2: troque DB_ENGINE para 'sqlserver' ou 'mysql' e preencha as credenciais.
"""
import sqlite3
from pathlib import Path

# ============ CONFIGURAÇÃO ============
DB_ENGINE = "sqlite"  # opções: "sqlite" | "sqlserver" | "mysql"

# Caminho do banco SQLite (Fase 1)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "gerenciador_testes_essencial.db"

# Credenciais para Fase 2 (SQL Server / MySQL) — deixe pronto
SQLSERVER_CONFIG = {
    "server": "SEU_SERVIDOR",
    "database": "GerenciadorTestes",
    "username": "sa",
    "password": "SUA_SENHA",
    "driver": "ODBC Driver 17 for SQL Server",
}

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "GerenciadorTestes",
    "user": "root",
    "password": "SUA_SENHA",
}

# Módulos iniciais, cadastrados automaticamente na primeira execução
MODULOS_INICIAIS = [
    "SIGAFAT", "SIGAFIS", "SIGAEST", "SIGAPCP", "SIGACFG",
    "SIGAFIN", "SIGACOM", "SIGAPES", "SIGAADM", "SIGAINT",
]


class Database:
    """Fachada de conexão. O resto do sistema só conhece esta classe."""

    @staticmethod
    def get_connection():
        if DB_ENGINE == "sqlite":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        elif DB_ENGINE == "sqlserver":
            # Fase 2: instale pyodbc e descomente
            # import pyodbc
            # cfg = SQLSERVER_CONFIG
            # conn_str = (
            #     f"DRIVER={{{cfg['driver']}}};SERVER={cfg['server']};"
            #     f"DATABASE={cfg['database']};UID={cfg['username']};PWD={cfg['password']}"
            # )
            # conn = pyodbc.connect(conn_str)
            # conn.row_factory = None
            # return conn
            raise NotImplementedError(
                "Configure pyodbc para usar SQL Server (Fase 2).")
        elif DB_ENGINE == "mysql":
            # Fase 2: instale pymysql e descomente
            # import pymysql
            # cfg = MYSQL_CONFIG
            # conn = pymysql.connect(
            #     host=cfg["host"], port=cfg["port"], database=cfg["database"],
            #     user=cfg["user"], password=cfg["password"], cursorclass=pymysql.cursors.DictCursor,
            # )
            # return conn
            raise NotImplementedError(
                "Configure pymysql para usar MySQL (Fase 2).")
        raise ValueError(f"DB_ENGINE inválido: {DB_ENGINE}")

    @staticmethod
    def init_db():
        """Cria as tabelas caso não existam + módulos iniciais."""
        conn = Database.get_connection()
        cur = conn.cursor()

        # Catálogo mestre de casos de teste (reutilizável entre viradas)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS casos_teste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                tarefa TEXT,
                descricao TEXT NOT NULL,
                modulo TEXT NOT NULL,
                rotina TEXT,
                tipo TEXT NOT NULL DEFAULT 'Funcional',
                prioridade TEXT NOT NULL DEFAULT 'Media',
                responsavel TEXT,
                requisito_compliance TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # Migração: adiciona a coluna "tarefa" em bancos criados antes desta versão
        colunas = [r[1] for r in cur.execute(
            "PRAGMA table_info(casos_teste)").fetchall()]
        if colunas and "tarefa" not in colunas:
            cur.execute("ALTER TABLE casos_teste ADD COLUMN tarefa TEXT")

        # Tabela de módulos (cadastrados pelo usuário no menu Cadastros > Módulos)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("SELECT COUNT(*) FROM modulos")
        if cur.fetchone()[0] == 0:
            for m in MODULOS_INICIAIS:
                cur.execute(
                    "INSERT OR IGNORE INTO modulos (nome) VALUES (?)", (m,))

        # Tabela de usuários (para vincular como responsável nos testes)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT,
                cargo TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # Ciclos de virada de versão (ex.: Release 12.1.2410)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                versao TEXT,
                ano INTEGER,
                data_inicio TEXT,
                data_fim TEXT,
                status TEXT NOT NULL DEFAULT 'Planejado',
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # Associação caso <-> ciclo (muitos-para-muitos com status de execução)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclo_casos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ciclo_id INTEGER NOT NULL,
                caso_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Nao iniciado',
                percentual INTEGER NOT NULL DEFAULT 0,
                responsavel TEXT,
                horas_estimadas REAL DEFAULT 0,
                horas_reais REAL DEFAULT 0,
                evidencia TEXT,
                observacoes TEXT,
                atualizado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE,
                FOREIGN KEY (caso_id) REFERENCES casos_teste(id) ON DELETE CASCADE,
                UNIQUE (ciclo_id, caso_id)
            )
        """)

        conn.commit()
        conn.close()
