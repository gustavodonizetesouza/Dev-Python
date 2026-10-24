"""
Camada de conexão com banco de dados.
Suporta múltiplos bancos: SQLite e SQL Server (MySQL: conexão ok, DDL pendente).
Cada CLIENTE usa um banco próprio; o CICLO é a unidade completa de trabalho.
Garantias desta camada:
- Ao abrir o banco de um cliente, o SCHEMA é sempre verificado/criado UMA vez
  por sessão (cache), no DIALETO correto (SQLite ou T-SQL). Nenhuma query cai
  em tabela inexistente.
- Falhas de schema são GRAVADAS em erros.log (nunca mais silenciosas).
- Sem cliente/conexão configurada, usa uma ÚNICA conexão em memória
  (singleton), que NUNCA é destruída pelo close().
- Cadastro de conexão NÃO trava: nada de exceção não tratada.

CONEXÃO DA SESSÃO (mobilidade): o usuário escolhe a conexão após o login.
Três estados possíveis:
  - SESSAO_MEMORIA (0): banco temporário em memória — trabalho offline
    consciente (dados não ficam salvos);
  - id real de conexão: usa aquela conexão (override temporário);
  - None: comportamento padrão (conexão padrão do cliente ativo).
Trocar de cliente no rodapé limpa o override APENAS se ele apontava para uma
conexão real (o modo memória é uma escolha explícita do usuário e persiste).

FALHA DE CONEXÃO: se a conexão ativa estiver inacessível (rede bloqueada,
servidor fora), get_connection() levanta erro com MENSAGEM AMIGÁVEL — nunca
fallback silencioso para memória (evita o usuário digitar dados que seriam
perdidos sem saber). A orientação é trocar a conexão no menu.

COMPATIBILIDADE DE DIALETO (Adapter):
- RowDict: dict que também aceita índice posicional (row[0]) — unifica
  sqlite3.Row e pyodbc.Row para todo o models.py;
- _CursorCompat: cursor que captura o ID de INSERTs no SQL Server via
  SELECT SCOPE_IDENTITY() (pyodbc não popula lastrowid) e devolve linhas
  como RowDict em qualquer driver;
- _ConexaoCompat: empacota a conexão para entregar sempre o cursor compatível.
O banco de CONFIGURAÇÃO (clientes, conexões, perfis, usuarios_sistema) é
SEMPRE SQLite local — identidade de login não mora no banco do cliente.

SQL SERVER: a connection string usa TrustServerCertificate=yes — o ODBC
Driver 18 exige criptografia (Encrypt=yes por padrão) e valida a cadeia do
certificado. SQL Server usa certificado autoassinado por padrão; sem esse
parâmetro a conexão falha com 'cadeia de certificação não confiável'.
O tráfego continua criptografado; apenas não validamos a cadeia.
Login timeout curto (5s) para o teste de conectividade não travar a UI.
"""
import sqlite3
import shutil
import traceback
from datetime import datetime
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
# Chaves de schema já garantidas nesta sessão (evita recriar DDL a cada conexão)
_schema_garantido = set()
# Conexão da SESSÃO: None = padrão do cliente | 0 = memória | id real = override
_conexao_sessao_id = None
# Sentinela: modo "banco temporário da sessão" (escolha explícita do usuário)
SESSAO_MEMORIA = 0


class ErroConexaoAmigavel(RuntimeError):
    """Falha de conexão com mensagem orientada ao usuário (não traceback cru)."""
    pass


class _ConexaoMemoria(sqlite3.Connection):
    """Conexão SQLite em memória que NUNCA é realmente fechada.

    Os repositórios chamam conn.close() ao final de cada operação. Numa
    conexão :memory:, fechar DESTRÓI o banco e os dados da sessão se perdem.
    Este wrapper ignora o close() para manter os dados vivos durante toda
    a sessão do app.
    """

    def close(self):
        pass


class RowDict(dict):
    """Dict que também aceita índice posicional (row[0]) e nome (row['nome']).

    Unifica o comportamento de sqlite3.Row e pyodbc.Row: o models.py pode
    usar dict(r), r['coluna'] e r[0] (queries escalares como COUNT) com
    QUALQUER driver, sem alterar uma linha de SQL.
    """

    def __init__(self, cols, values):
        super().__init__(zip(cols, values))
        self._vals = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int) and not isinstance(key, bool):
            return self._vals[key]
        return super().__getitem__(key)


class _CursorCompat:
    """Cursor que normaliza o comportamento entre sqlite3 e pyodbc.

    - fetchone/fetchall devolvem RowDict (dict + índice posicional);
    - No SQL Server, após todo INSERT executa SELECT SCOPE_IDENTITY() e
      expõe o resultado em .lastrowid (pyodbc não popula lastrowid);
    - execute() retorna self (permite cur.execute(...).fetchall()).
    """

    def __init__(self, cur, dialeto):
        self._cur = cur
        self.dialeto = dialeto
        self._lastrowid = None

    def execute(self, sql, params=None):
        if params is None:
            self._cur.execute(sql)
        else:
            self._cur.execute(sql, params)
        if self.dialeto == "sqlserver" and \
                (sql or "").lstrip().upper().startswith("INSERT"):
            try:
                self._cur.execute(
                    "SELECT CAST(SCOPE_IDENTITY() AS INT) AS novo_id")
                row = self._cur.fetchone()
                self._lastrowid = row[0] if row is not None else None
            except Exception:
                self._lastrowid = None
        return self

    def executemany(self, sql, seq):
        self._cur.executemany(sql, seq)
        return self

    def _cols(self):
        d = self._cur.description
        return [c[0] for c in d] if d else []

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return RowDict(self._cols(), row)

    def fetchall(self):
        cols = self._cols()
        return [RowDict(cols, r) for r in self._cur.fetchall()]

    @property
    def lastrowid(self):
        if self.dialeto == "sqlserver":
            return self._lastrowid
        return getattr(self._cur, "lastrowid", None)

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _ConexaoCompat:
    """Conexão que entrega SEMPRE o cursor compatível (_CursorCompat)."""

    def __init__(self, conn, dialeto):
        self._conn = conn
        self.dialeto = dialeto

    def cursor(self):
        return _CursorCompat(self._conn.cursor(), self.dialeto)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def execute(self, sql, params=None):
        if params is None:
            return self._conn.execute(sql)
        return self._conn.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


class Database:
    """Fachada de conexão. O resto do sistema só conhece esta classe."""

    # ---------- Log interno de falhas de schema ----------
    @staticmethod
    def _log_erro_interno(mensagem):
        """Registra falhas de schema/infra em erros.log (nunca mais silenciosas)."""
        try:
            with open(BASE_DIR / "erros.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {mensagem}\n")
                f.write(traceback.format_exc())
                f.write("\n" + "=" * 60 + "\n")
        except Exception:
            pass

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
        # ---------- SEGURANÇA (Fase 1): perfis, login e vínculo usuário-cliente ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS perfis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT
            )
        """)
        cur.execute("SELECT COUNT(*) FROM perfis")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO perfis (nome, descricao) VALUES (?,?)",
                [("Administrador", "Dono do sistema — acesso total"),
                 ("Gerente", "Gestão do ciclo — aprova orçamento e decide go-live"),
                 ("Líder de Teste", "Coordenação técnica — cria ciclos, casos e rotinas"),
                 ("Testador", "Execução — executa casos e lança horas"),
                 ("Visualizador", "Somente leitura — relatórios e KPIs (auditoria)")])
        # Permissões por perfil (códigos usados na Fase 2 — já semeados)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS perfil_permissoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                perfil_id INTEGER NOT NULL,
                permissao TEXT NOT NULL,
                UNIQUE (perfil_id, permissao)
            )
        """)
        cur.execute("SELECT COUNT(*) FROM perfil_permissoes")
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT id, nome FROM perfis")
            mapa_perfis = {nome: pid for pid, nome in cur.fetchall()}
            _perm_por_perfil = {
                "Administrador": ["ciclos.gerenciar", "casos.gerenciar",
                                  "execucao.executar", "horas.lancar",
                                  "custos.gerenciar", "relatorios.ver",
                                  "config.gerenciar", "usuarios.gerenciar"],
                "Gerente": ["ciclos.gerenciar", "casos.gerenciar",
                            "execucao.executar", "horas.lancar",
                            "custos.gerenciar", "relatorios.ver"],
                "Líder de Teste": ["ciclos.gerenciar", "casos.gerenciar",
                                   "execucao.executar", "horas.lancar",
                                   "relatorios.ver"],
                "Testador": ["execucao.executar", "horas.lancar", "relatorios.ver"],
                "Visualizador": ["relatorios.ver"],
            }
            for nome_perfil, perms in _perm_por_perfil.items():
                pid = mapa_perfis.get(nome_perfil)
                if pid is None:
                    continue
                for p in perms:
                    cur.execute(
                        "INSERT OR IGNORE INTO perfil_permissoes (perfil_id, permissao) VALUES (?,?)",
                        (pid, p))
        # Usuários do SISTEMA (login) — identidade global, no banco de configuração.
        # Diferente da tabela 'usuarios' por cliente (catálogo de analistas/responsáveis).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                perfil_id INTEGER NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (perfil_id) REFERENCES perfis(id)
            )
        """)
        # Vínculo N:N usuário do sistema ↔ clientes (escopo de acesso)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuario_clientes (
                usuario_id INTEGER NOT NULL,
                cliente_id INTEGER NOT NULL,
                PRIMARY KEY (usuario_id, cliente_id)
            )
        """)
        # Bootstrap: primeiro acesso — cria 'admin' com senha padrão se não houver usuários
        cur.execute("SELECT COUNT(*) FROM usuarios_sistema")
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT id FROM perfis WHERE nome='Administrador'")
            p = cur.fetchone()
            if p:
                from utils.autenticacao import hash_senha
                cur.execute("""
                    INSERT INTO usuarios_sistema (login, nome, senha_hash, perfil_id)
                    VALUES (?,?,?,?)
                """, ("admin", "Administrador", hash_senha("admin123"), p[0]))
        # ---------- FIM SEGURANÇA ----------
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

    # ---------- Conexão da SESSÃO (mobilidade) ----------
    @staticmethod
    def definir_conexao_sessao(conexao_id):
        """Define a conexão da sessão.

        conexao_id = SESSAO_MEMORIA (0) -> banco temporário em memória;
        conexao_id = id real           -> override para aquela conexão.
        """
        global _conexao_sessao_id
        _conexao_sessao_id = conexao_id

    @staticmethod
    def limpar_conexao_sessao():
        """Remove o override da sessão (volta à conexão padrão do cliente)."""
        global _conexao_sessao_id
        _conexao_sessao_id = None

    @staticmethod
    def conexao_sessao_ativa():
        """Retorna o estado da conexão da sessão (None | SESSAO_MEMORIA | id)."""
        return _conexao_sessao_id

    @staticmethod
    def _get_conexao_sessao():
        """Config da conexão da sessão.

        Retorna: None (sem override) | {'tipo': 'memoria'} (modo temporário)
        | dict da conexão real (override).
        """
        if _conexao_sessao_id is None:
            return None
        if _conexao_sessao_id == SESSAO_MEMORIA:
            return {"tipo": "memoria", "nome": "Banco temporário da sessão"}
        conn = Database.get_config_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conexoes WHERE id=?", (_conexao_sessao_id,))
        c = cur.fetchone()
        conn.close()
        return dict(c) if c else None

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

    # ---------- Dialeto ----------
    @staticmethod
    def _dialeto_de_cfg(cfg):
        """Resolve o dialeto a partir da configuração da conexão."""
        if not cfg:
            return "sqlite"
        tipo = (cfg.get("tipo") or "sqlite").strip().lower()
        if tipo in ("sqlserver", "mssql"):
            return "sqlserver"
        if tipo == "mysql":
            return "mysql"
        return "sqlite"

    @staticmethod
    def _chave_schema(cfg):
        """Chave de cache do schema garantido (por banco de destino)."""
        return (f"{cfg.get('tipo')}|{cfg.get('host') or ''}|"
                f"{cfg.get('porta') or ''}|{cfg.get('banco') or ''}")

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
            raw = sqlite3.connect(":memory:", factory=_ConexaoMemoria)
        except TypeError:
            raw = sqlite3.connect(":memory:")
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
        Database._criar_tabelas(raw.cursor(), "sqlite")
        raw.commit()
        _mem_conn = _ConexaoCompat(raw, "sqlite")
        return _mem_conn

    # ---------- Conexão de dados ----------
    @staticmethod
    def get_connection():
        """
        Retorna a conexão com o banco de dados ativo (cursor compatível).
        Ordem de resolução:
        1. Conexão da SESSÃO:
           - SESSAO_MEMORIA (0): banco temporário em memória (escolha explícita);
           - id real: aquela conexão (override temporário);
           - None: conexão PADRÃO do cliente ativo;
        2. Sem conexão configurada: conexão em memória ÚNICA (fallback).
        FALHA DE CONEXÃO (rede bloqueada, servidor fora): levanta
        ErroConexaoAmigavel com orientação clara — NUNCA fallback silencioso
        para memória (evita o usuário digitar dados que seriam perdidos).
        """
        cfg = Database._get_conexao_sessao()
        if cfg is None:
            cliente = Database._get_cliente_ativo()
            if cliente.get("id"):
                cfg = Database._get_conexao_padrao_cliente(cliente["id"])
        if cfg is None:
            return Database._get_mem_conn()
        # Modo explícito: banco temporário da sessão (trabalho offline)
        if (cfg.get("tipo") or "").strip().lower() == "memoria":
            return Database._get_mem_conn()
        dialeto = Database._dialeto_de_cfg(cfg)
        try:
            conn = Database._conectar(cfg)
        except Exception as e:
            Database._log_erro_interno(
                f"Falha ao conectar no banco '{cfg.get('banco')}' "
                f"({cfg.get('tipo')}, host={cfg.get('host')}): {e}")
            raise ErroConexaoAmigavel(
                f"Não foi possível conectar ao banco '{cfg.get('nome') or cfg.get('banco')}' "
                f"({cfg.get('tipo')}).\n\n"
                "Verifique sua rede ou troque a conexão em:\n"
                "Configurações → Trocar Conexão...\n\n"
                f"Detalhe técnico: {e}")
        chave = Database._chave_schema(cfg)
        if chave not in _schema_garantido and dialeto in ("sqlite", "sqlserver"):
            try:
                cur = conn.cursor()
                Database._criar_tabelas(cur, dialeto)
                conn.commit()
                _schema_garantido.add(chave)
            except Exception:
                Database._log_erro_interno(
                    f"Falha ao garantir o schema no banco "
                    f"'{cfg.get('banco')}' ({dialeto}). "
                    f"As tabelas podem não existir — verifique permissões "
                    f"(db_owner/db_ddladmin) e o erros.log.")
        return _ConexaoCompat(conn, dialeto)

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
    def _conectar_sqlserver(cfg, timeout=5):
        import pyodbc
        from utils.seguranca import obter_senha
        senha = obter_senha(cfg["id"], cfg.get("senha"))
        driver = cfg.get("driver") or "ODBC Driver 17 for SQL Server"
        porta = cfg.get("porta") or 1433
        # TrustServerCertificate=yes: o ODBC Driver 18 exige criptografia
        # (Encrypt=yes por padrão) e valida a cadeia do certificado do
        # servidor. SQL Server usa certificado autoassinado por padrão,
        # o que quebra a conexão com 'cadeia de certificação não confiável'.
        # Mantém o tráfego criptografado; apenas confia no certificado.
        # timeout: login timeout curto — rede bloqueada falha em segundos.
        conn_str = (
            f"DRIVER={{{driver}}};SERVER={cfg['host']},{porta};"
            f"DATABASE={cfg['banco']};UID={cfg['usuario']};PWD={senha};"
            f"TrustServerCertificate=yes"
        )
        return pyodbc.connect(conn_str, timeout=timeout)

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
    def testar_conexao(cfg, senha=None, timeout=5):
        """Testa a conexão com timeout curto (para o diálogo de seleção)."""
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
                # Mesmo ajuste do _conectar_sqlserver (TrustServerCertificate)
                conn_str = (
                    f"DRIVER={{{driver}}};SERVER={cfg['host']},{porta};"
                    f"DATABASE={cfg['banco']};UID={cfg['usuario']};PWD={senha};"
                    f"TrustServerCertificate=yes"
                )
                conn = pyodbc.connect(conn_str, timeout=timeout)
                conn.close()
            elif cfg["tipo"] == "mysql":
                import pymysql
                conn = pymysql.connect(
                    host=cfg["host"], port=int(cfg.get("porta") or 3306),
                    database=cfg["banco"], user=cfg["usuario"], password=senha,
                    connect_timeout=timeout)
                conn.close()
            else:
                return False, "Tipo de conexão inválido."
            return True, "Conexão OK!"
        except Exception as e:
            return False, str(e)

    # ---------- Schema ----------
    @staticmethod
    def criar_schema_para(cfg):
        """Cria/verifica o schema no banco indicado, no dialeto correto."""
        dialeto = Database._dialeto_de_cfg(cfg)
        conn = Database._conectar(cfg)
        try:
            cur = conn.cursor()
            Database._criar_tabelas(cur, dialeto)
            conn.commit()
        finally:
            conn.close()
        _schema_garantido.add(Database._chave_schema(cfg))

    @staticmethod
    def init_db():
        """Cria o schema no banco ativo (sessão ou cliente). Falhas vão para erros.log."""
        try:
            cfg = Database._get_conexao_sessao()
            if cfg is not None and (cfg.get("tipo") or "") == "memoria":
                return  # banco em memória: schema já criado no singleton
            if cfg is None:
                cliente = Database._get_cliente_ativo()
                if cliente.get("id"):
                    cfg = Database._get_conexao_padrao_cliente(cliente["id"])
            if cfg is None:
                return
            Database.criar_schema_para(cfg)
        except Exception:
            Database._log_erro_interno(
                "Falha ao criar/verificar o schema do banco ativo.")

    @staticmethod
    def _criar_tabelas(cur, dialeto="sqlite"):
        """Cria o schema padrão do banco de dados de um cliente, no dialeto correto."""
        if dialeto == "sqlserver":
            Database._criar_tabelas_sqlserver(cur)
        else:
            Database._criar_tabelas_sqlite(cur)

    @staticmethod
    def _criar_tabelas_sqlite(cur):
        """Schema no dialeto SQLite (inclui migração do legado)."""
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
        # Tipos de Teste — configuráveis pelo usuário (Configurações → Tipos de Teste)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tipos_teste (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE
            )
        """)
        # Semear padrões (só se vazia) para não quebrar os combos existentes
        cur.execute("SELECT COUNT(*) FROM tipos_teste")
        if cur.fetchone()[0] == 0:
            for nome in ("Funcional", "Processo", "Regressivo", "Integração", "Segurança"):
                cur.execute("INSERT OR IGNORE INTO tipos_teste (nome) VALUES (?)", (nome.upper(),))
        # Garantir que tipos já usados em casos existentes fiquem disponíveis no combo
        cur.execute("SELECT DISTINCT tipo FROM casos_teste WHERE tipo IS NOT NULL AND tipo <> ''")
        for row in cur.fetchall():
            t = (row[0] or "").strip()
            if not t:
                continue
            cur.execute("INSERT OR IGNORE INTO tipos_teste (nome) VALUES (?)", (t.upper(),))
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
        # Etapas de validação do caso de teste (teste de processo).
        # Cada etapa pode estar vinculada a uma ROTINA do ciclo (herda o status)
        # ou ser manual (checklist livre). Execução por etapa grava percentual
        # e horas_reais (informados na ABA EXECUÇÃO, com totalização no caso).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS caso_etapas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caso_id INTEGER NOT NULL,
                rotina_id INTEGER,
                nome TEXT NOT NULL,
                ordem INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Nao iniciada',
                percentual INTEGER DEFAULT 0,
                horas_reais REAL DEFAULT 0,
                observacoes TEXT,
                criado_em TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (caso_id) REFERENCES casos_teste(id) ON DELETE CASCADE
            )
        """)
        try:
            cols_etp = [r[1] for r in cur.execute("PRAGMA table_info(caso_etapas)").fetchall()]
            if "rotina_id" not in cols_etp:
                cur.execute("ALTER TABLE caso_etapas ADD COLUMN rotina_id INTEGER")
            if "percentual" not in cols_etp:
                cur.execute("ALTER TABLE caso_etapas ADD COLUMN percentual INTEGER DEFAULT 0")
            if "horas_reais" not in cols_etp:
                cur.execute("ALTER TABLE caso_etapas ADD COLUMN horas_reais REAL DEFAULT 0")
        except Exception:
            pass
        Database._migrar_legado(cur)

    @staticmethod
    def _criar_tabelas_sqlserver(cur):
        """Schema no dialeto T-SQL (SQL Server) — idempotente.

        Diferenças do SQLite: IDENTITY(1,1) no lugar de AUTOINCREMENT,
        NVARCHAR/FLOAT, verificação de existência via sys.tables e
        timestamps como NVARCHAR(30) com DEFAULT CONVERT(..., SYSDATETIME(), 120)
        (mesmo formato de string ISO do SQLite — zero surpresa de tipo na UI).
        """

        def existe_tabela(nome):
            cur.execute("SELECT COUNT(*) FROM sys.tables WHERE name = ?", (nome,))
            return cur.fetchone()[0] > 0

        if not existe_tabela("ciclos"):
            cur.execute("""
                CREATE TABLE ciclos (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nome NVARCHAR(255) NOT NULL,
                    tipo NVARCHAR(100) NOT NULL DEFAULT 'Virada de Versão',
                    versao NVARCHAR(100),
                    ano INT,
                    data_inicio NVARCHAR(20),
                    data_fim NVARCHAR(20),
                    status NVARCHAR(50) NOT NULL DEFAULT 'Planejado',
                    responsavel NVARCHAR(255),
                    custo_orcado FLOAT DEFAULT 0,
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120)
                )
            """)
        if not existe_tabela("casos_teste"):
            cur.execute("""
                CREATE TABLE casos_teste (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    ciclo_id INT NOT NULL,
                    codigo NVARCHAR(50) NOT NULL,
                    tarefa NVARCHAR(MAX),
                    descricao NVARCHAR(MAX) NOT NULL,
                    modulo NVARCHAR(100) NOT NULL,
                    rotina NVARCHAR(255),
                    tipo NVARCHAR(100) NOT NULL DEFAULT 'Funcional',
                    prioridade NVARCHAR(50) NOT NULL DEFAULT 'Media',
                    responsavel NVARCHAR(255),
                    requisito_compliance NVARCHAR(255),
                    status_exec NVARCHAR(50) NOT NULL DEFAULT 'Nao iniciado',
                    percentual INT NOT NULL DEFAULT 0,
                    horas_estimadas FLOAT DEFAULT 0,
                    horas_reais FLOAT DEFAULT 0,
                    evidencia NVARCHAR(MAX),
                    observacoes NVARCHAR(MAX),
                    atualizado_em NVARCHAR(30),
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120)
                )
            """)
        if not existe_tabela("modulos"):
            cur.execute("""
                CREATE TABLE modulos (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nome NVARCHAR(100) NOT NULL UNIQUE
                )
            """)
        if not existe_tabela("usuarios"):
            cur.execute("""
                CREATE TABLE usuarios (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nome NVARCHAR(255) NOT NULL,
                    email NVARCHAR(255),
                    cargo NVARCHAR(100),
                    ativo INT NOT NULL DEFAULT 1,
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120)
                )
            """)
        if not existe_tabela("ciclo_etapas"):
            cur.execute("""
                CREATE TABLE ciclo_etapas (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    ciclo_id INT NOT NULL,
                    nome NVARCHAR(255) NOT NULL,
                    descricao NVARCHAR(MAX),
                    ordem INT DEFAULT 0,
                    responsavel NVARCHAR(255),
                    status NVARCHAR(50) NOT NULL DEFAULT 'Nao iniciada',
                    percentual INT NOT NULL DEFAULT 0,
                    data_prevista_inicio NVARCHAR(20),
                    data_prevista_fim NVARCHAR(20),
                    custo_orcado FLOAT DEFAULT 0,
                    FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
                )
            """)
        if not existe_tabela("ciclo_rotinas"):
            cur.execute("""
                CREATE TABLE ciclo_rotinas (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    codigo NVARCHAR(60) NOT NULL UNIQUE,
                    ciclo_id INT NOT NULL,
                    etapa_id INT,
                    nome NVARCHAR(255) NOT NULL,
                    descricao NVARCHAR(MAX),
                    status NVARCHAR(50) NOT NULL DEFAULT 'Pendente',
                    responsavel NVARCHAR(255),
                    horas_estimadas FLOAT DEFAULT 0,
                    caso_teste_id INT,
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120),
                    FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE,
                    FOREIGN KEY (etapa_id) REFERENCES ciclo_etapas(id) ON DELETE SET NULL
                )
            """)
        if not existe_tabela("ciclo_horas"):
            cur.execute("""
                CREATE TABLE ciclo_horas (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    ciclo_id INT NOT NULL,
                    etapa_id INT,
                    rotina_id INT,
                    lancado_por NVARCHAR(255),
                    data NVARCHAR(20),
                    horas FLOAT DEFAULT 0,
                    custo_hora FLOAT DEFAULT 0,
                    descricao NVARCHAR(MAX),
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120),
                    FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
                )
            """)
        if not existe_tabela("ciclo_custos"):
            cur.execute("""
                CREATE TABLE ciclo_custos (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    ciclo_id INT NOT NULL,
                    etapa_id INT,
                    descricao NVARCHAR(255) NOT NULL,
                    categoria NVARCHAR(50) DEFAULT 'Outros',
                    valor FLOAT DEFAULT 0,
                    data NVARCHAR(20),
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120),
                    FOREIGN KEY (ciclo_id) REFERENCES ciclos(id) ON DELETE CASCADE
                )
            """)
        if not existe_tabela("tipos_ciclo"):
            cur.execute("""
                CREATE TABLE tipos_ciclo (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nome NVARCHAR(100) NOT NULL UNIQUE
                )
            """)
        if not existe_tabela("tipos_teste"):
            cur.execute("""
                CREATE TABLE tipos_teste (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nome NVARCHAR(100) NOT NULL UNIQUE
                )
            """)
        if not existe_tabela("melhorias"):
            cur.execute("""
                CREATE TABLE melhorias (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    codigo NVARCHAR(50) NOT NULL UNIQUE,
                    titulo NVARCHAR(255) NOT NULL,
                    descricao NVARCHAR(MAX),
                    modulo NVARCHAR(100),
                    prioridade NVARCHAR(50) NOT NULL DEFAULT 'Media',
                    status NVARCHAR(50) NOT NULL DEFAULT 'Proposta',
                    responsavel NVARCHAR(255),
                    ciclo_id INT,
                    caso_origem_id INT,
                    caso_teste_id INT,
                    data_criacao NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120),
                    data_implementacao NVARCHAR(30),
                    observacoes NVARCHAR(MAX)
                )
            """)
        if not existe_tabela("caso_etapas"):
            cur.execute("""
                CREATE TABLE caso_etapas (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    caso_id INT NOT NULL,
                    rotina_id INT,
                    nome NVARCHAR(255) NOT NULL,
                    ordem INT DEFAULT 0,
                    status NVARCHAR(50) NOT NULL DEFAULT 'Nao iniciada',
                    percentual INT DEFAULT 0,
                    horas_reais FLOAT DEFAULT 0,
                    observacoes NVARCHAR(MAX),
                    criado_em NVARCHAR(30) DEFAULT CONVERT(NVARCHAR(30), SYSDATETIME(), 120),
                    FOREIGN KEY (caso_id) REFERENCES casos_teste(id) ON DELETE CASCADE
                )
            """)
        # Índice de casos por ciclo
        cur.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes
                           WHERE name = 'idx_casos_ciclo'
                             AND object_id = OBJECT_ID('dbo.casos_teste'))
                CREATE INDEX idx_casos_ciclo ON casos_teste(ciclo_id)
        """)
        # Semear tipos de ciclo (só se vazia) — verificação por COUNT (dialético-neutro)
        cur.execute("SELECT COUNT(*) FROM tipos_ciclo")
        if cur.fetchone()[0] == 0:
            for nome in ("Virada de Versão", "Implementação Legal", "Reforma Tributária",
                         "Novo Módulo", "Adequação Compliance", "Outro"):
                cur.execute("INSERT INTO tipos_ciclo (nome) VALUES (?)", (nome,))
        # Semear tipos de teste (só se vazia)
        cur.execute("SELECT COUNT(*) FROM tipos_teste")
        if cur.fetchone()[0] == 0:
            for nome in ("Funcional", "Processo", "Regressivo", "Integração", "Segurança"):
                cur.execute("INSERT INTO tipos_teste (nome) VALUES (?)", (nome.upper(),))
        # Garantir que tipos já usados em casos existentes fiquem disponíveis
        cur.execute("SELECT DISTINCT tipo FROM casos_teste WHERE tipo IS NOT NULL AND tipo <> ''")
        for row in cur.fetchall():
            t = (row[0] or "").strip().upper()
            if not t:
                continue
            cur.execute("SELECT COUNT(*) FROM tipos_teste WHERE nome = ?", (t,))
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO tipos_teste (nome) VALUES (?)", (t,))

    @staticmethod
    def _migrar_legado(cur):
        """Migra o schema antigo (catálogo + projetos) para o novo (ciclo central).

        Executado SOMENTE no dialeto SQLite — bancos SQL Server nascem novos,
        sem histórico legado a migrar.
        """
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