"""Criação de tabelas, índices e migrações leves — DDL por dialeto
(SQLite e SQL Server).

Estrutura multiusuário: tabela usuarios + coluna usuario_id em TODAS as
entidades (contas, categorias, lancamentos, recorrencias). O isolamento
por usuário acontece nas consultas do repositório (multi-tenancy lógico).

A semeadura das 11 categorias padrão agora é POR USUÁRIO, executada no
momento do cadastro (ver dominio.repositorio.RepositorioUsuarios.semear_categorias).

Migrações: como CREATE TABLE IF NOT EXISTS não altera tabelas existentes,
as evoluções de coluna são aplicadas por migrações idempotentes (verificam
se a coluna já existe antes do ALTER TABLE). A migração "pago" adiciona o
controle de contas a pagar/receber aos lançamentos existentes, marcando
todos como pagos (pago = 1) para preservar o comportamento anterior.
"""
from core.conexao import DIALETO_SQLITE, DIALETO_SQLSERVER

DDL = [
    # ---------- usuarios (primeira tabela: referenciada por FK nas demais) ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT NOT NULL,
                email      TEXT NOT NULL COLLATE NOCASE UNIQUE,
                senha_hash TEXT NOT NULL,
                papel      TEXT NOT NULL DEFAULT 'usuario'
                           CHECK (papel IN ('admin', 'usuario')),
                plano      TEXT NOT NULL DEFAULT 'gratuito',
                ativo      INTEGER NOT NULL DEFAULT 1,
                criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'usuarios')
                CREATE TABLE usuarios (
                    id         INT IDENTITY(1,1) PRIMARY KEY,
                    nome       NVARCHAR(120) NOT NULL,
                    email      NVARCHAR(160) NOT NULL UNIQUE,
                    senha_hash NVARCHAR(400) NOT NULL,
                    papel      NVARCHAR(10) NOT NULL DEFAULT 'usuario'
                               CHECK (papel IN ('admin', 'usuario')),
                    plano      NVARCHAR(20) NOT NULL DEFAULT 'gratuito',
                    ativo      BIT NOT NULL DEFAULT 1,
                    criado_em  DATETIME2 NOT NULL DEFAULT SYSDATETIME()
                )""",
    },
    # ---------- contas ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS contas (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id    INTEGER NOT NULL,
                nome          TEXT NOT NULL,
                tipo          TEXT NOT NULL DEFAULT 'Corrente',
                saldo_inicial REAL NOT NULL DEFAULT 0,
                ativo         INTEGER NOT NULL DEFAULT 1,
                criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (usuario_id, nome),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contas')
                CREATE TABLE contas (
                    id            INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id    INT NOT NULL,
                    nome          NVARCHAR(120) NOT NULL,
                    tipo          NVARCHAR(40) NOT NULL DEFAULT 'Corrente',
                    saldo_inicial DECIMAL(14,2) NOT NULL DEFAULT 0,
                    ativo         BIT NOT NULL DEFAULT 1,
                    criado_em     DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    UNIQUE (usuario_id, nome),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )""",
    },
    # ---------- categorias ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS categorias (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                nome      TEXT NOT NULL,
                tipo      TEXT NOT NULL DEFAULT 'saida' CHECK (tipo IN ('entrada', 'saida')),
                cor       TEXT NOT NULL DEFAULT '#607d8b',
                ativo     INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (usuario_id, nome),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'categorias')
                CREATE TABLE categorias (
                    id        INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    nome      NVARCHAR(120) NOT NULL,
                    tipo      NVARCHAR(10) NOT NULL DEFAULT 'saida'
                              CHECK (tipo IN ('entrada', 'saida')),
                    cor       NVARCHAR(9) NOT NULL DEFAULT '#607d8b',
                    ativo     BIT NOT NULL DEFAULT 1,
                    criado_em DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    UNIQUE (usuario_id, nome),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )""",
    },
    # ---------- recorrencias ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS recorrencias (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id    INTEGER NOT NULL,
                descricao     TEXT NOT NULL,
                conta_id      INTEGER NOT NULL,
                categoria_id  INTEGER NOT NULL,
                tipo          TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
                valor         REAL NOT NULL CHECK (valor > 0),
                dia_do_mes    INTEGER NOT NULL CHECK (dia_do_mes BETWEEN 1 AND 31),
                mes_inicio    TEXT NOT NULL,
                ativo         INTEGER NOT NULL DEFAULT 1,
                ultimo_gerado TEXT,
                criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (conta_id) REFERENCES contas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'recorrencias')
                CREATE TABLE recorrencias (
                    id            INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id    INT NOT NULL,
                    descricao     NVARCHAR(160) NOT NULL,
                    conta_id      INT NOT NULL,
                    categoria_id  INT NOT NULL,
                    tipo          NVARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
                    valor         DECIMAL(14,2) NOT NULL CHECK (valor > 0),
                    dia_do_mes    INT NOT NULL CHECK (dia_do_mes BETWEEN 1 AND 31),
                    mes_inicio    CHAR(7) NOT NULL,
                    ativo         BIT NOT NULL DEFAULT 1,
                    ultimo_gerado CHAR(7) NULL,
                    criado_em     DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY (conta_id) REFERENCES contas(id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                )""",
    },
    # ---------- lancamentos (com controle pago/pendente) ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS lancamentos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id     INTEGER NOT NULL,
                conta_id       INTEGER NOT NULL,
                categoria_id   INTEGER NOT NULL,
                tipo           TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
                valor          REAL NOT NULL CHECK (valor > 0),
                data_mov       TEXT NOT NULL,
                descricao      TEXT NOT NULL DEFAULT '',
                pago           INTEGER NOT NULL DEFAULT 1,
                recorrencia_id INTEGER,
                criado_em      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (conta_id) REFERENCES contas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                FOREIGN KEY (recorrencia_id) REFERENCES recorrencias(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'lancamentos')
                CREATE TABLE lancamentos (
                    id             INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id     INT NOT NULL,
                    conta_id       INT NOT NULL,
                    categoria_id   INT NOT NULL,
                    tipo           NVARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
                    valor          DECIMAL(14,2) NOT NULL CHECK (valor > 0),
                    data_mov       DATE NOT NULL,
                    descricao      NVARCHAR(200) NOT NULL DEFAULT '',
                    pago           BIT NOT NULL DEFAULT 1,
                    recorrencia_id INT NULL,
                    criado_em      DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY (conta_id) REFERENCES contas(id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                    FOREIGN KEY (recorrencia_id) REFERENCES recorrencias(id)
                )""",
    },
]

INDICES = [
    # ----- índices de usuario_id (aceleram o filtro de isolamento) -----
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_conta_usu ON contas (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_conta_usu' "
                            "AND object_id = OBJECT_ID('dbo.contas')) "
                            "CREATE INDEX ix_conta_usu ON contas (usuario_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cat_usu ON categorias (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cat_usu' "
                            "AND object_id = OBJECT_ID('dbo.categorias')) "
                            "CREATE INDEX ix_cat_usu ON categorias (usuario_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_rec_usu ON recorrencias (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_rec_usu' "
                            "AND object_id = OBJECT_ID('dbo.recorrencias')) "
                            "CREATE INDEX ix_rec_usu ON recorrencias (usuario_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_lanc_usu ON lancamentos (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_lanc_usu' "
                            "AND object_id = OBJECT_ID('dbo.lancamentos')) "
                            "CREATE INDEX ix_lanc_usu ON lancamentos (usuario_id)"),
    },
    # ----- índices operacionais dos lançamentos -----
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_lanc_data ON lancamentos (data_mov)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_lanc_data' "
                            "AND object_id = OBJECT_ID('dbo.lancamentos')) "
                            "CREATE INDEX ix_lanc_data ON lancamentos (data_mov)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_lanc_conta ON lancamentos (conta_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_lanc_conta' "
                            "AND object_id = OBJECT_ID('dbo.lancamentos')) "
                            "CREATE INDEX ix_lanc_conta ON lancamentos (conta_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_lanc_cat ON lancamentos (categoria_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_lanc_cat' "
                            "AND object_id = OBJECT_ID('dbo.lancamentos')) "
                            "CREATE INDEX ix_lanc_cat ON lancamentos (categoria_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_lanc_rec ON lancamentos (recorrencia_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_lanc_rec' "
                            "AND object_id = OBJECT_ID('dbo.lancamentos')) "
                            "CREATE INDEX ix_lanc_rec ON lancamentos (recorrencia_id)"),
    },
]

# ----- migrações leves (evolução de schema em bancos já existentes) -----
# Executadas no arranque, idempotentes: só aplicam se a coluna não existir.
# "pago": controla contas a pagar/receber. Dados anteriores = pagos (1),
# preservando o comportamento e os números anteriores à migração.
MIGRACAO_PAGO = {
    DIALETO_SQLITE: "ALTER TABLE lancamentos ADD COLUMN pago INTEGER NOT NULL DEFAULT 1",
    DIALETO_SQLSERVER: "ALTER TABLE lancamentos ADD pago BIT NOT NULL DEFAULT 1",
}

CATEGORIAS_INICIAIS = [
    ("Moradia", "saida", "#e91e63"),
    ("Alimentação", "saida", "#ff9800"),
    ("Transporte", "saida", "#795548"),
    ("Saúde", "saida", "#f44336"),
    ("Educação", "saida", "#3f51b5"),
    ("Lazer", "saida", "#00bcd4"),
    ("Assinaturas", "saida", "#9c27b0"),
    ("Outros", "saida", "#607d8b"),
    ("Salário", "entrada", "#43a047"),
    ("Renda Extra", "entrada", "#8bc34a"),
    ("Investimentos", "entrada", "#2196f3"),
]


def _coluna_existe(db, tabela: str, coluna: str) -> bool:
    """Verifica existência de coluna nos dois dialetos."""
    if db.dialeto == DIALETO_SQLITE:
        linhas = db.consultar(f"PRAGMA table_info({tabela})")
        return any(linha["name"] == coluna for linha in linhas)
    linhas = db.consultar(
        """SELECT COUNT(*) AS t FROM sys.columns
           WHERE object_id = OBJECT_ID(?) AND name = ?""",
        (f"dbo.{tabela}", coluna))
    return linhas[0]["t"] > 0


def _migrar(db):
    """Aplica migrações idempotentes de coluna."""
    if not _coluna_existe(db, "lancamentos", "pago"):
        db.executar(MIGRACAO_PAGO[db.dialeto])


def inicializar_banco(db):
    """Cria tabelas e índices (se não existirem) e aplica migrações.

    Não semeia categorias globais: cada usuário recebe suas próprias
    11 categorias padrão no momento do cadastro.
    """
    for stmt in DDL:
        db.executar(stmt[db.dialeto])
    for stmt in INDICES:
        db.executar(stmt[db.dialeto])
    _migrar(db)
    db.confirmar()
