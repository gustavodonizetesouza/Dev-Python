"""
Camada de conexão com banco de dados.
Suporta múltiplos bancos: SQLite, SQL Server e MySQL.
Cada cliente usa um banco próprio; a conexão ativa é definida no banco de configuração.
"""
import sqlite3
from pathlib import Path

# ============ CONFIGURAÇÃO ============
BASE_DIR = Path(__file__).resolve().parent.parent

# Banco de CONFIGURAÇÃO (sempre SQLite local) — guarda as conexões cadastradas
CONFIG_DB_PATH = BASE_DIR / "gerenciador_config.db"

# Arquivo do banco local padrão (fallback sempre funcional)
BANCO_LOCAL_PADRAO = BASE_DIR / "gerenciador_testes_essencial.db"


class Database:
    """Fachada de conexão. O resto do sistema só conhece esta classe."""

    # ---------- Banco de configuração ----------
    @staticmethod
    def get_config_connection():
        """Conexão com o banco de configuração (sempre SQLite local)."""
        conn = sqlite3.connect(CONFIG_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_config_db():
        """Cria as tabelas de configuração e uma conexão padrão se não houver."""
        conn = Database.get_config_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS conexoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cliente TEXT,
                tipo TEXT NOT NULL,
                host TEXT,
                porta INTEGER,
                banco TEXT,
                usuario TEXT,
                senha TEXT,
                driver TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)

        # Garante que sempre exista a conexão local padrão
        cur.execute("SELECT COUNT(*) FROM conexoes WHERE tipo='sqlite' AND banco=?",
                    (str(BANCO_LOCAL_PADRAO),))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO conexoes (nome, cliente, tipo, banco)
                VALUES ('Local (SQLite)', 'Local', 'sqlite', ?)
            """, (str(BANCO_LOCAL_PADRAO),))

        conn.commit()
        conn.close()

    # ---------- Conexão ativa ----------
    @staticmethod
    def _get_conexao_ativa():
        """Lê a conexão ativa do banco de configuração. Retorna dict ou None."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT valor FROM config WHERE chave='conexao_ativa'")
        row = cur.fetchone()
        ativa_id = int(row["valor"]) if row and row["valor"] else None
        if ativa_id is None:
            conn.close()
            return None
        cur.execute("SELECT * FROM conexoes WHERE id=?", (ativa_id,))
        c = cur.fetchone()
        conn.close()
        return dict(c) if c else None

    @staticmethod
    def definir_conexao_ativa(conexao_id):
        """Define qual conexão é a ativa."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('conexao_ativa', ?)",
                    (str(conexao_id),))
        conn.commit()
        conn.close()

    @staticmethod
    def _conexao_padrao_local():
        """Retorna o dict da conexão local padrão (sempre funcional)."""
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conexoes WHERE tipo='sqlite' AND banco=?",
                    (str(BANCO_LOCAL_PADRAO),))
        c = cur.fetchone()
        conn.close()
        if c:
            return dict(c)
        return {"id": None, "nome": "Local (SQLite)", "cliente": "Local",
                "tipo": "sqlite", "banco": str(BANCO_LOCAL_PADRAO),
                "host": None, "porta": None, "usuario": None, "driver": None}

    # ---------- Conexão de dados ----------
    @staticmethod
    def get_connection():
        """Retorna a conexão com o banco da conexão ATIVA."""
        cfg = Database._get_conexao_ativa()
        if cfg is None:
            cfg = Database._conexao_padrao_local()
        return Database._conectar(cfg)

    @staticmethod
    def _conectar(cfg):
        """Conecta em qualquer conexão pelo dict de configuração."""
        tipo = cfg["tipo"]
        if tipo == "sqlite":
            return Database._conectar_sqlite(cfg.get("banco"))
        if tipo == "sqlserver":
            return Database._conectar_sqlserver(cfg)
        if tipo == "mysql":
            return Database._conectar_mysql(cfg)
        raise ValueError(f"Tipo de conexão inválido: {tipo}")

    @staticmethod
    def _conectar_sqlite(caminho):
        """Conecta a um banco SQLite de forma robusta."""
        caminho = Path(caminho) if caminho else None
        if caminho is None or not str(caminho).strip():
            raise RuntimeError("Caminho do banco SQLite vazio.")
        if not caminho.is_absolute():
            caminho = BASE_DIR / caminho
        if caminho.parent and not caminho.parent.exists():
            caminho.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(caminho)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _conectar_sqlserver(cfg):
        import pyodbc
        from utils.seguranca import obter_senha
        senha = obter_senha(cfg["id"], cfg.get("senha"))
        driver = cfg.get("driver") or "ODBC Driver 17 for SQL Server"
        porta = cfg.get("porta") or 1433
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={cfg['host']},{porta};"
            f"DATABASE={cfg['banco']};UID={cfg['usuario']};PWD={senha}"
        )
        return pyodbc.connect(conn_str)

    @staticmethod
    def _conectar_mysql(cfg):
        import pymysql
        from utils.seguranca import obter_senha
        senha = obter_senha(cfg["id"], cfg.get("senha"))
        return pymysql.connect(
            host=cfg["host"], port=int(cfg.get("porta") or 3306),
            database=cfg["banco"], user=cfg["usuario"], password=senha,
            cursorclass=pymysql.cursors.DictCursor,
        )

    # ---------- Teste de conexão ----------
    @staticmethod
    def testar_conexao(cfg, senha=None):
        """Tenta conectar e retorna (ok, mensagem)."""
        try:
            if cfg["tipo"] == "sqlite":
                caminho = Path(cfg["banco"]) if cfg.get("banco") else None
                if caminho is None or not str(caminho).strip():
                    return False, "Caminho do banco SQLite vazio."
                if not caminho.is_absolute():
                    caminho = BASE_DIR / caminho
                if caminho.parent and not caminho.parent.exists():
                    caminho.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(caminho)
                conn.execute("SELECT 1")
                conn.close()
            elif cfg["tipo"] == "sqlserver":
                import pyodbc
                driver = cfg.get("driver") or "ODBC Driver 17 for SQL Server"
                porta = cfg.get("porta") or 1433
                conn_str = (
                    f"DRIVER={{{driver}}};SERVER={cfg['host']},{porta};"
                    f"DATABASE={cfg['banco']};UID={cfg['usuario']};PWD={senha}"
                )
                conn = pyodbc.connect(conn_str)
                conn.close()
            elif cfg["tipo"] == "mysql":
                import pymysql
                conn = pymysql.connect(
                    host=cfg["host"], port=int(cfg.get("porta") or 3306),
                    database=cfg["banco"], user=cfg["usuario"], password=senha)
                conn.close()
            else:
                return False, "Tipo de conexão inválido."
            return True, "Conexão OK!"
        except Exception as e:
            return False, str(e)

    # ---------- Schema ----------
    @staticmethod
    def criar_schema_para(cfg):
        """Cria as tabelas de dados em uma conexão específica (sem torná-la ativa)."""
        conn = Database._conectar(cfg)
        cur = conn.cursor()
        Database._criar_tabelas(cur)
        conn.commit()
        conn.close()

    @staticmethod
    def init_db():
        """
        Cria as tabelas na conexão ativa.
        Se a conexão ativa estiver quebrada, cai para a conexão local padrão
        (que sempre funciona) e a define como ativa — o app NUNCA trava na abertura.
        """
        try:
            cfg = Database._get_conexao_ativa()
            if cfg is None:
                cfg = Database._conexao_padrao_local()
            Database.criar_schema_para(cfg)
        except Exception:
            cfg = Database._conexao_padrao_local()
            if cfg.get("id"):
                Database.definir_conexao_ativa(cfg["id"])
            Database.criar_schema_para(cfg)

    @staticmethod
    def _criar_tabelas(cur):
        """Cria o schema padrão (usado por init_db e criar_schema_para)."""
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        """)
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS melhorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                modulo TEXT,
                prioridade TEXT NOT NULL DEFAULT 'Media',
                status TEXT NOT NULL DEFAULT 'Proposta',
                responsavel TEXT,
                ciclo_id INTEGER,
                caso_origem_id INTEGER,
                caso_teste_id INTEGER,
                data_criacao TEXT DEFAULT (datetime('now','localtime')),
                data_implementacao TEXT,
                observacoes TEXT
            )
        """)
