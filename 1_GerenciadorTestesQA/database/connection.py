"""
Camada de conexão com banco de dados.
Suporta múltiplos bancos: SQLite, SQL Server e MySQL.
Cada CLIENTE usa um banco próprio; o CICLO é a unidade completa de trabalho.

Garantias desta camada:
- Ao abrir o banco SQLite de um cliente, o SCHEMA é sempre verificado/criado
  (nenhuma query cai em tabela inexistente).
- Sem cliente/conexão configurada, usa uma ÚNICA conexão em memória
  (singleton), que NUNCA é destruída pelo close(), para o app funcionar
  sem travar e sem perder dados na sessão.
- Cadastro de conexão NÃO trava: nada de exceção não tratada.
"""
import sqlite3
import shutil
from pathlib import Path

# ============ CONFIGURAÇÃO ============
BASE_DIR = Path(__file__).resolve().parent.parent

# Pasta central de dados (criada automaticamente na primeira execução)
DATA_DIR = BASE_DIR / "data"

# Banco de CONFIGURAÇÃO (sempre SQLite local) — guarda clientes, conexões e config
CONFIG_DB_PATH = DATA_DIR / "gerenciador_config.db"

# Arquivo do banco local padrão (fallback antigo — não é mais auto-criado)
BANCO_LOCAL_PADRAO = DATA_DIR / "gerenciador_testes_essencial.db"

# Conexão em memória ÚNICA (usada quando não há cliente/conexão ativa)
_mem_conn = None


class _ConexaoMemoria(sqlite3.Connection):
    """Conexão SQLite em memória que NUNCA é realmente fechada.

    Os repositórios chamam conn.close() ao final de cada operação. Numa
    conexão :memory:, fechar DESTRÓI o banco e os dados da sessão se perdem.
    Este wrapper ignora o close() para manter os dados vivos durante toda
    a sessão do app.
    """

    def close(self):
        pass


class Database:
    """Fachada de conexão. O resto do sistema só conhece esta classe."""

    # ---------- Migração de arquivos para data/ ----------
    @staticmethod
    def _migrar_arquivos_para_data():
        """Garante que todos os bancos SQLite fiquem na pasta data/. Idempotente."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        antigo_cfg = BASE_DIR / "gerenciador_config.db"
        if antigo_cfg.exists() and not CONFIG_DB_PATH.exists():
            shutil.move(str(antigo_cfg), str(CONFIG_DB_PATH))

        antigo_local = BASE_DIR / "gerenciador_testes_essencial.db"
        if antigo_local.exists() and not BANCO_LOCAL_PADRAO.exists():
            shutil.move(str(antigo_local), str(BANCO_LOCAL_PADRAO))

        if CONFIG_DB_PATH.exists():
            try:
                conn = sqlite3.connect(CONFIG_DB_PATH)
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
                cur.execute(
                    "SELECT id, banco FROM conexoes WHERE tipo='sqlite'")
                for r in cur.fetchall():
                    caminho = (r["banco"] or "").strip()
                    if not caminho:
                        continue
                    p = Path(caminho)
                    if p.is_absolute():
                        continue
                    alvo = DATA_DIR / p
                    origem = BASE_DIR / p
                    if origem.exists() and not alvo.exists():
                        alvo.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(origem), str(alvo))
                    cur.execute("UPDATE conexoes SET banco=? WHERE id=?",
                                (str(alvo), r["id"]))
                antigo_local_abs = str(
                    BASE_DIR / "gerenciador_testes_essencial.db")
                cur.execute("UPDATE conexoes SET banco=? WHERE tipo='sqlite' AND banco=?",
                            (str(BANCO_LOCAL_PADRAO), antigo_local_abs))
                conn.commit()
                conn.close()
            except Exception:
                pass

    # ---------- Banco de configuração ----------
    @staticmethod
    def get_config_connection():
        """Conexão com o banco de configuração (sempre SQLite local em data/)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(CONFIG_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_config_db():
        """Cria as tabelas de configuração (clientes, conexões, config) e migra."""
        Database._migrar_arquivos_para_data()
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                observacoes TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        cols = [r[1]
                for r in cur.execute("PRAGMA table_info(conexoes)").fetchall()]
        if "cliente_id" not in cols:
            cur.execute("ALTER TABLE conexoes ADD COLUMN cliente_id INTEGER")
        if "padrao" not in cols:
            cur.execute(
                "ALTER TABLE conexoes ADD COLUMN padrao INTEGER NOT NULL DEFAULT 0")

        cur.execute("SELECT COUNT(*) FROM clientes")
        tem_clientes = cur.fetchone()[0] > 0
        cur.execute("SELECT COUNT(*) FROM conexoes")
        tem_conexoes = cur.fetchone()[0] > 0

        if tem_clientes or tem_conexoes:
            if not tem_clientes:
                cur.execute(
                    "SELECT valor FROM config WHERE chave='conexao_ativa'")
                row = cur.fetchone()
                ativa_id = int(row["valor"]) if row and row["valor"] else None

                cur.execute("SELECT * FROM conexoes ORDER BY id")
                conexoes = cur.fetchall()
                primeiro_cliente = None
                for c in conexoes:
                    nome_cli = (c["cliente"] or c["nome"]
                                or "Cliente").strip() or "Cliente"
                    cur.execute(
                        "INSERT INTO clientes (nome, ativo) VALUES (?, 1)", (nome_cli,))
                    cli_id = cur.lastrowid
                    if primeiro_cliente is None:
                        primeiro_cliente = cli_id
                    cur.execute("UPDATE conexoes SET cliente_id=?, padrao=1 WHERE id=?",
                                (cli_id, c["id"]))
                    if ativa_id is not None and c["id"] == ativa_id:
                        cur.execute(
                            "INSERT OR REPLACE INTO config (chave, valor) VALUES ('cliente_ativo', ?)",
                            (str(cli_id),))
                if ativa_id is None and primeiro_cliente is not None:
                    cur.execute(
                        "INSERT OR REPLACE INTO config (chave, valor) VALUES ('cliente_ativo', ?)",
                        (str(primeiro_cliente),))
                cur.execute("DELETE FROM config WHERE chave='conexao_ativa'")
            else:
                cur.execute("""
                    UPDATE conexoes SET cliente_id =
                        (SELECT id FROM clientes ORDER BY id LIMIT 1)
                    WHERE cliente_id IS NULL
                """)
                cur.execute(
                    "SELECT DISTINCT cliente_id FROM conexoes WHERE cliente_id IS NOT NULL")
                for r in cur.fetchall():
                    cli_id = r[0]
                    cur.execute(
                        "SELECT COUNT(*) FROM conexoes WHERE cliente_id=? AND padrao=1", (cli_id,))
                    if cur.fetchone()[0] == 0:
                        cur.execute(
                            "SELECT id FROM conexoes WHERE cliente_id=? ORDER BY id LIMIT 1", (cli_id,))
                        c = cur.fetchone()
                        if c:
                            cur.execute(
                                "UPDATE conexoes SET padrao=1 WHERE id=?", (c["id"],))
                cur.execute(
                    "SELECT valor FROM config WHERE chave='cliente_ativo'")
                if not cur.fetchone():
                    cur.execute(
                        "SELECT id FROM clientes WHERE ativo=1 ORDER BY id LIMIT 1")
                    cli = cur.fetchone()
                    if cli:
                        cur.execute(
                            "INSERT OR REPLACE INTO config (chave, valor) VALUES ('cliente_ativo', ?)",
                            (str(cli["id"]),))
        # Banco novo: não cria nada — o usuário configura pelo menu.

        conn.commit()
        conn.close()

    # ---------- Cliente ativo ----------
    @staticmethod
    def _get_cliente_ativo():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT valor FROM config WHERE chave='cliente_ativo'")
        row = cur.fetchone()
        ativo_id = int(row["valor"]) if row and row["valor"] else None
        if ativo_id:
            cur.execute(
                "SELECT * FROM clientes WHERE id=? AND ativo=1", (ativo_id,))
            c = cur.fetchone()
            if c:
                conn.close()
                return dict(c)
        cur.execute("SELECT * FROM clientes WHERE ativo=1 ORDER BY id LIMIT 1")
        c = cur.fetchone()
        conn.close()
        if c:
            return dict(c)
        return {"id": None, "nome": "Sem Cliente"}

    @staticmethod
    def definir_cliente_ativo(cliente_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('cliente_ativo', ?)",
                    (str(cliente_id),))
        conn.commit()
        conn.close()

    @staticmethod
    def ajustar_cliente_ativo():
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT valor FROM config WHERE chave='cliente_ativo'")
        row = cur.fetchone()
        atual = int(row["valor"]) if row and row["valor"] else None
        if atual:
            cur.execute(
                "SELECT id FROM clientes WHERE id=? AND ativo=1", (atual,))
            if cur.fetchone():
                conn.close()
                return
        cur.execute("SELECT id FROM clientes WHERE ativo=1 ORDER BY id LIMIT 1")
        c = cur.fetchone()
        if c:
            cur.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES ('cliente_ativo', ?)",
                        (str(c["id"]),))
        else:
            cur.execute("DELETE FROM config WHERE chave='cliente_ativo'")
        conn.commit()
        conn.close()

    # ---------- Conexão do cliente ----------
    @staticmethod
    def definir_conexao_padrao(conexao_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT cliente_id FROM conexoes WHERE id=?",
                    (conexao_id,))
        row = cur.fetchone()
        cliente_id = row["cliente_id"] if row else None
        if cliente_id is None:
            conn.close()
            return
        cur.execute(
            "UPDATE conexoes SET padrao=0 WHERE cliente_id=?", (cliente_id,))
        cur.execute("UPDATE conexoes SET padrao=1 WHERE id=?", (conexao_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def _get_conexao_padrao_cliente(cliente_id):
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conexoes WHERE cliente_id=? AND padrao=1 ORDER BY id LIMIT 1",
                    (cliente_id,))
        c = cur.fetchone()
        if c is None:
            cur.execute("SELECT * FROM conexoes WHERE cliente_id=? ORDER BY id LIMIT 1",
                        (cliente_id,))
            c = cur.fetchone()
        conn.close()
        return dict(c) if c else None

    # ---------- Conexão em memória única ----------
    @staticmethod
    def _get_mem_conn():
        """Retorna a ÚNICA conexão em memória (singleton) da sessão.

        Se a conexão for acidentalmente corrompida, recria do zero.
        O close() dos repositórios é inofensivo (ignorado pelo wrapper).
        """
        global _mem_conn
        if _mem_conn is not None:
            try:
                _mem_conn.execute("SELECT 1")
                return _mem_conn
            except Exception:
                _mem_conn = None
        try:
            conn = sqlite3.connect(":memory:", factory=_ConexaoMemoria)
        except TypeError:
            conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        Database._criar_tabelas(conn.cursor())
        conn.commit()
        _mem_conn = conn
        return _mem_conn

    # ---------- Conexão de dados ----------
    @staticmethod
    def get_connection():
        """
        Retorna a conexão com o banco do CLIENTE ATIVO.
        - Sem cliente/conexão: usa a conexão em memória ÚNICA (nada se perde na sessão).
        - Com cliente SQLite: garante o SCHEMA antes de retornar (nunca trava).
        """
        cliente = Database._get_cliente_ativo()
        cfg = None
        if cliente.get("id"):
            cfg = Database._get_conexao_padrao_cliente(cliente["id"])
        if cfg is None:
            return Database._get_mem_conn()

        conn = Database._conectar(cfg)

        # Garantia de schema: nenhuma query encontra tabela inexistente
        if cfg["tipo"] == "sqlite":
            try:
                cur = conn.cursor()
                Database._criar_tabelas(cur)
                conn.commit()
            except Exception:
                pass

        return conn

    @staticmethod
    def _conectar(cfg):
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
        caminho = Path(caminho) if caminho else None
        if caminho is None or not str(caminho).strip():
            raise RuntimeError("Caminho do banco SQLite vazio.")
        if not caminho.is_absolute():
            caminho = DATA_DIR / caminho
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
        try:
            if cfg["tipo"] == "sqlite":
                caminho = Path(cfg["banco"]) if cfg.get("banco") else None
                if caminho is None or not str(caminho).strip():
                    return False, "Caminho do banco SQLite vazio."
                if not caminho.is_absolute():
                    caminho = DATA_DIR / caminho
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
        conn = Database._conectar(cfg)
        cur = conn.cursor()
        Database._criar_tabelas(cur)
        conn.commit()
        conn.close()

    @staticmethod
    def init_db():
        """Cria o schema no banco do cliente ativo (se houver)."""
        try:
            cliente = Database._get_cliente_ativo()
            cfg = None
            if cliente.get("id"):
                cfg = Database._get_conexao_padrao_cliente(cliente["id"])
            if cfg is None:
                return
            Database.criar_schema_para(cfg)
        except Exception:
            pass

    @staticmethod
    def _criar_tabelas(cur):
        """Cria o schema padrão do banco de um cliente e migra o legado."""
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'Virada de Versão',
                versao TEXT,
                ano INTEGER,
                data_inicio TEXT,
                data_fim TEXT,
                status TEXT NOT NULL DEFAULT 'Planejado',
                responsavel TEXT,
                custo_orcado REAL DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS casos_teste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ciclo_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                tarefa TEXT,
                descricao TEXT NOT NULL,
                modulo TEXT NOT NULL,
                rotina TEXT,
                tipo TEXT NOT NULL DEFAULT 'Funcional',
                prioridade TEXT NOT NULL DEFAULT 'Media',
                responsavel TEXT,
                requisito_compliance TEXT,
                status_exec TEXT NOT NULL DEFAULT 'Nao iniciado',
                percentual INTEGER NOT NULL DEFAULT 0,
                horas_estimadas REAL DEFAULT 0,
                horas_reais REAL DEFAULT 0,
                evidencia TEXT,
                observacoes TEXT,
                atualizado_em TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_casos_ciclo ON casos_teste(ciclo_id)")
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
            CREATE TABLE IF NOT EXISTS ciclo_etapas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ciclo_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                descricao TEXT,
                ordem INTEGER DEFAULT 0,
                responsavel TEXT,
                status TEXT NOT NULL DEFAULT 'Nao iniciada',
                percentual INTEGER NOT NULL DEFAULT 0,
                data_prevista_inicio TEXT,
                data_prevista_fim TEXT,
                custo_orcado REAL DEFAULT 0,
                FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclo_rotinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                ciclo_id INTEGER NOT NULL,
                etapa_id INTEGER,
                nome TEXT NOT NULL,
                descricao TEXT,
                status TEXT NOT NULL DEFAULT 'Pendente',
                responsavel TEXT,
                horas_estimadas REAL DEFAULT 0,
                caso_teste_id INTEGER,
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE,
                FOREIGN KEY (etapa_id) REFERENCES ciclo_etapas(id) ON DELETE SET NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclo_horas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ciclo_id INTEGER NOT NULL,
                etapa_id INTEGER,
                rotina_id INTEGER,
                lancado_por TEXT,
                data TEXT,
                horas REAL DEFAULT 0,
                custo_hora REAL DEFAULT 0,
                descricao TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ciclo_custos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ciclo_id INTEGER NOT NULL,
                etapa_id INTEGER,
                descricao TEXT NOT NULL,
                categoria TEXT DEFAULT 'Outros',
                valor REAL DEFAULT 0,
                data TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tipos_ciclo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
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

        Database._migrar_legado(cur)

    @staticmethod
    def _migrar_legado(cur):
        """Migra o schema antigo (catálogo + projetos) para o novo (ciclo central)."""

        # 1) ciclos antigos ganham colunas novas
        cols_c = [r[1]
                  for r in cur.execute("PRAGMA table_info(ciclos)").fetchall()]
        if "tipo" not in cols_c:
            cur.execute(
                "ALTER TABLE ciclos ADD COLUMN tipo TEXT DEFAULT 'Virada de Versão'")
        if "responsavel" not in cols_c:
            cur.execute("ALTER TABLE ciclos ADD COLUMN responsavel TEXT")
        if "custo_orcado" not in cols_c:
            cur.execute(
                "ALTER TABLE ciclos ADD COLUMN custo_orcado REAL DEFAULT 0")

        # 2) casos_teste: se não tem ciclo_id, é o catálogo antigo -> reconstruir
        cols = [r[1] for r in cur.execute(
            "PRAGMA table_info(casos_teste)").fetchall()]
        if "ciclo_id" not in cols:
            cur.execute("""
                CREATE TABLE casos_teste_novo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ciclo_id INTEGER NOT NULL,
                    codigo TEXT NOT NULL,
                    tarefa TEXT,
                    descricao TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    rotina TEXT,
                    tipo TEXT NOT NULL DEFAULT 'Funcional',
                    prioridade TEXT NOT NULL DEFAULT 'Media',
                    responsavel TEXT,
                    requisito_compliance TEXT,
                    status_exec TEXT NOT NULL DEFAULT 'Nao iniciado',
                    percentual INTEGER NOT NULL DEFAULT 0,
                    horas_estimadas REAL DEFAULT 0,
                    horas_reais REAL DEFAULT 0,
                    evidencia TEXT,
                    observacoes TEXT,
                    atualizado_em TEXT,
                    criado_em TEXT DEFAULT (datetime('now','localtime'))
                )
            """)

            vinculos = {}
            tem_cc = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ciclo_casos'"
            ).fetchone()
            if tem_cc:
                for cc in cur.execute("SELECT * FROM ciclo_casos").fetchall():
                    vinculos.setdefault(cc["caso_id"], []).append(cc)

            ciclo_migracao = None

            for caso in cur.execute("SELECT * FROM casos_teste ORDER BY id").fetchall():
                lista = vinculos.get(caso["id"], [])
                if lista:
                    for cc in lista:
                        cur.execute("""
                            INSERT INTO casos_teste_novo
                                (id, ciclo_id, codigo, tarefa, descricao, modulo, rotina,
                                 tipo, prioridade, responsavel, requisito_compliance,
                                 status_exec, percentual, horas_estimadas, horas_reais,
                                 evidencia, observacoes, atualizado_em, criado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            caso["id"], cc["ciclo_id"], caso["codigo"], caso["tarefa"],
                            caso["descricao"], caso["modulo"], caso["rotina"], caso["tipo"],
                            caso["prioridade"], cc["responsavel"] or caso["responsavel"],
                            caso["requisito_compliance"], cc["status"], cc["percentual"],
                            cc["horas_estimadas"], cc["horas_reais"], cc["evidencia"],
                            cc["observacoes"], cc["atualizado_em"], caso["criado_em"],
                        ))
                else:
                    if ciclo_migracao is None:
                        cur.execute("""
                            INSERT INTO ciclos (nome, tipo, status)
                            VALUES ('Migração (dados antigos)', 'Virada de Versão', 'Planejado')
                        """)
                        ciclo_migracao = cur.lastrowid
                    cur.execute("""
                        INSERT INTO casos_teste_novo
                            (id, ciclo_id, codigo, tarefa, descricao, modulo, rotina,
                             tipo, prioridade, responsavel, requisito_compliance)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        caso["id"], ciclo_migracao, caso["codigo"], caso["tarefa"],
                        caso["descricao"], caso["modulo"], caso["rotina"], caso["tipo"],
                        caso["prioridade"], caso["responsavel"], caso["requisito_compliance"],
                    ))

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_casos_ciclo ON casos_teste_novo(ciclo_id)")
            cur.execute("DROP TABLE casos_teste")
            cur.execute("ALTER TABLE casos_teste_novo RENAME TO casos_teste")
            Database._fix_seq(cur, "casos_teste")

        # 2b) Garante que casos_teste tenha TODAS as colunas usadas pelo app
        #     (bancos criados por versões antigas podem estar sem colunas).
        cols_caso = [r[1] for r in cur.execute(
            "PRAGMA table_info(casos_teste)").fetchall()]
        _colunas_casos = {
            "tarefa": "TEXT",
            "descricao": "TEXT DEFAULT ''",
            "modulo": "TEXT DEFAULT ''",
            "rotina": "TEXT",
            "tipo": "TEXT DEFAULT 'Funcional'",
            "prioridade": "TEXT DEFAULT 'Media'",
            "responsavel": "TEXT",
            "requisito_compliance": "TEXT",
            "status_exec": "TEXT NOT NULL DEFAULT 'Nao iniciado'",
            "percentual": "INTEGER NOT NULL DEFAULT 0",
            "horas_estimadas": "REAL DEFAULT 0",
            "horas_reais": "REAL DEFAULT 0",
            "evidencia": "TEXT",
            "observacoes": "TEXT",
            "atualizado_em": "TEXT",
            "criado_em": "TEXT DEFAULT (datetime('now','localtime'))",
        }
        for nome_col, def_col in _colunas_casos.items():
            if nome_col not in cols_caso:
                try:
                    cur.execute(
                        f"ALTER TABLE casos_teste ADD COLUMN {nome_col} {def_col}")
                except Exception:
                    pass

        # 3) melhorias: projeto_id -> ciclo_id
        cols_m = [r[1] for r in cur.execute(
            "PRAGMA table_info(melhorias)").fetchall()]
        if "ciclo_id" not in cols_m and "projeto_id" in cols_m:
            cur.execute(
                "ALTER TABLE melhorias RENAME COLUMN projeto_id TO ciclo_id")

        # 4) tipos_projeto -> tipos_ciclo
        tem_tp = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tipos_projeto'"
        ).fetchone()
        tem_tc = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tipos_ciclo'"
        ).fetchone()
        if tem_tp and not tem_tc:
            cur.execute("ALTER TABLE tipos_projeto RENAME TO tipos_ciclo")
        elif tem_tp and tem_tc:
            for t in cur.execute("SELECT * FROM tipos_projeto").fetchall():
                cur.execute(
                    "INSERT OR IGNORE INTO tipos_ciclo (nome) VALUES (?)", (t["nome"],))
            cur.execute("DROP TABLE tipos_projeto")
        cur.execute("SELECT COUNT(*) FROM tipos_ciclo")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO tipos_ciclo (nome) VALUES (?)",
                [("Virada de Versão",), ("Implementação Legal",), ("Reforma Tributária",),
                 ("Novo Módulo",), ("Adequação Compliance",), ("Outro",)])

        # 5) projetos (e detalhes) -> ciclos (e detalhes)
        tem_proj = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projetos'"
        ).fetchone()
        if tem_proj:
            for p in cur.execute("SELECT * FROM projetos ORDER BY id").fetchall():
                cur.execute("""
                    INSERT INTO ciclos (nome, tipo, status, responsavel, data_inicio,
                                        data_fim, custo_orcado, criado_em)
                    VALUES (?,?,?,?,?,?,?, COALESCE(?, datetime('now','localtime')))
                """, (p["nome"], p.get("tipo") or "Virada de Versão",
                      p.get("status") or "Planejado", p.get("responsavel"),
                      p.get("data_inicio"), p.get("data_fim"),
                      p.get("custo_orcado") or 0, p.get("criado_em")))
                novo_ciclo = cur.lastrowid

                tem_etapas = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='projeto_etapas'"
                ).fetchone()
                if tem_etapas:
                    for e in cur.execute(
                            "SELECT * FROM projeto_etapas WHERE projeto_id=?", (p["id"],)).fetchall():
                        cur.execute("""
                            INSERT INTO ciclo_etapas
                                (id, ciclo_id, nome, descricao, ordem, responsavel, status,
                                 percentual, data_prevista_inicio, data_prevista_fim, custo_orcado)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """, (e["id"], novo_ciclo, e["nome"], e.get("descricao"),
                              e.get("ordem") or 0, e.get("responsavel"),
                              e.get("status") or "Nao iniciada", e.get(
                                  "percentual") or 0,
                              e.get("data_prevista_inicio"), e.get(
                                  "data_prevista_fim"),
                              e.get("custo_orcado") or 0))
                    Database._fix_seq(cur, "ciclo_etapas")

                tem_rot = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='projeto_rotinas'"
                ).fetchone()
                if tem_rot:
                    for r in cur.execute(
                            "SELECT * FROM projeto_rotinas WHERE projeto_id=?", (p["id"],)).fetchall():
                        cur.execute("""
                            INSERT INTO ciclo_rotinas
                                (id, codigo, ciclo_id, etapa_id, nome, descricao, status,
                                 responsavel, horas_estimadas, caso_teste_id, criado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """, (r["id"], r["codigo"], novo_ciclo, r.get("etapa_id"),
                              r["nome"], r.get("descricao"), r.get(
                                  "status") or "Pendente",
                              r.get("responsavel"), r.get(
                                  "horas_estimadas") or 0,
                              r.get("caso_teste_id"), r.get("criado_em")))
                    Database._fix_seq(cur, "ciclo_rotinas")

                tem_horas = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='projeto_horas'"
                ).fetchone()
                if tem_horas:
                    for h in cur.execute(
                            "SELECT * FROM projeto_horas WHERE projeto_id=?", (p["id"],)).fetchall():
                        cur.execute("""
                            INSERT INTO ciclo_horas
                                (id, ciclo_id, etapa_id, rotina_id, lancado_por, data,
                                 horas, custo_hora, descricao, criado_em)
                            VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (h["id"], novo_ciclo, h.get("etapa_id"), h.get("rotina_id"),
                              h.get("lancado_por"), h.get(
                                  "data"), h.get("horas") or 0,
                              h.get("custo_hora") or 0, h.get("descricao"), h.get("criado_em")))
                    Database._fix_seq(cur, "ciclo_horas")

                tem_custos = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='projeto_custos'"
                ).fetchone()
                if tem_custos:
                    for c in cur.execute(
                            "SELECT * FROM projeto_custos WHERE projeto_id=?", (p["id"],)).fetchall():
                        cur.execute("""
                            INSERT INTO ciclo_custos
                                (id, ciclo_id, etapa_id, descricao, categoria, valor, data, criado_em)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (c["id"], novo_ciclo, c.get("etapa_id"), c["descricao"],
                              c.get("categoria") or "Outros", c.get(
                                  "valor") or 0,
                              c.get("data"), c.get("criado_em")))
                    Database._fix_seq(cur, "ciclo_custos")

        # 6) remove tabelas legadas
        for t in ("ciclo_casos", "projetos", "projeto_etapas", "projeto_rotinas",
                  "projeto_horas", "projeto_custos"):
            cur.execute(f"DROP TABLE IF EXISTS {t}")

    @staticmethod
    def _fix_seq(cur, tabela):
        try:
            cur.execute(
                f"UPDATE sqlite_sequence SET seq=(SELECT COALESCE(MAX(id),0) FROM {tabela}) "
                f"WHERE name=?", (tabela,))
        except Exception:
            pass
