"""Criação de tabelas, índices e migrações leves — DDL por dialeto
(SQLite e SQL Server).

Estrutura multiusuário: tabela usuarios + coluna usuario_id em TODAS as
entidades. O isolamento por usuário acontece nas consultas do repositório.
A semeadura das 11 categorias padrão é POR USUÁRIO, no cadastro.

Cartão de crédito: cartoes_credito (cadastro com conta de débito, dia de
fechamento, dia de vencimento e limite) e compras_cartao (1 linha por
PARCELA, agrupadas por grupo_id; a coluna fatura 'YYYY-MM' é nomeada pelo
mês de VENCIMENTO). A fatura paga gera 1 lançamento de saída na conta
vinculada — as compras em aberto são débito previsto, não caixa.

Migrações idempotentes: ALTER TABLE de colunas novas e conversão de dados
das recorrências legadas (mes_inicio + dia_do_mes -> data_inicio etc.).
"""
from core.conexao import DIALETO_SQLITE, DIALETO_SQLSERVER
from core.util import dias_no_mes

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
    # ---------- recorrencias (v2: frequência + término por data/quantidade) ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS recorrencias (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id         INTEGER NOT NULL,
                descricao          TEXT NOT NULL,
                conta_id           INTEGER NOT NULL,
                categoria_id       INTEGER NOT NULL,
                tipo               TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
                valor              REAL NOT NULL CHECK (valor > 0),
                frequencia         TEXT NOT NULL DEFAULT 'mensal'
                                   CHECK (frequencia IN ('mensal', 'semanal',
                                                         'trimestral', 'anual')),
                data_inicio        TEXT,
                data_fim           TEXT,
                qtd_vezes          INTEGER,
                geradas            INTEGER NOT NULL DEFAULT 0,
                ultimo_gerado_data TEXT,
                mes_inicio         TEXT NOT NULL DEFAULT '',
                dia_do_mes         INTEGER NOT NULL DEFAULT 1,
                ultimo_gerado      TEXT,
                ativo              INTEGER NOT NULL DEFAULT 1,
                criado_em          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (conta_id) REFERENCES contas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'recorrencias')
                CREATE TABLE recorrencias (
                    id                 INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id         INT NOT NULL,
                    descricao          NVARCHAR(160) NOT NULL,
                    conta_id           INT NOT NULL,
                    categoria_id       INT NOT NULL,
                    tipo               NVARCHAR(10) NOT NULL
                                       CHECK (tipo IN ('entrada', 'saida')),
                    valor              DECIMAL(14,2) NOT NULL CHECK (valor > 0),
                    frequencia         NVARCHAR(10) NOT NULL DEFAULT 'mensal'
                                       CHECK (frequencia IN ('mensal', 'semanal',
                                                             'trimestral', 'anual')),
                    data_inicio        DATE NULL,
                    data_fim           DATE NULL,
                    qtd_vezes          INT NULL,
                    geradas            INT NOT NULL DEFAULT 0,
                    ultimo_gerado_data DATE NULL,
                    mes_inicio         NVARCHAR(7) NOT NULL DEFAULT '',
                    dia_do_mes         INT NOT NULL DEFAULT 1,
                    ultimo_gerado      CHAR(7) NULL,
                    ativo              BIT NOT NULL DEFAULT 1,
                    criado_em          DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
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
    # ---------- cartoes_credito (cadastro do cartão) ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS cartoes_credito (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id      INTEGER NOT NULL,
                nome            TEXT NOT NULL,
                conta_id        INTEGER NOT NULL,
                dia_fechamento  INTEGER NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31),
                dia_vencimento  INTEGER NOT NULL CHECK (dia_vencimento BETWEEN 1 AND 31),
                limite_total    REAL NOT NULL DEFAULT 0,
                ativo           INTEGER NOT NULL DEFAULT 1,
                criado_em       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (usuario_id, nome),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (conta_id) REFERENCES contas(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'cartoes_credito')
                CREATE TABLE cartoes_credito (
                    id              INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id      INT NOT NULL,
                    nome            NVARCHAR(120) NOT NULL,
                    conta_id        INT NOT NULL,
                    dia_fechamento  INT NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31),
                    dia_vencimento  INT NOT NULL CHECK (dia_vencimento BETWEEN 1 AND 31),
                    limite_total    DECIMAL(14,2) NOT NULL DEFAULT 0,
                    ativo           BIT NOT NULL DEFAULT 1,
                    criado_em       DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    UNIQUE (usuario_id, nome),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY (conta_id) REFERENCES contas(id)
                )""",
    },
    # ---------- compras_cartao (1 linha por PARCELA; fatura 'YYYY-MM' = mês de venc.) ----------
    {
        DIALETO_SQLITE: """
            CREATE TABLE IF NOT EXISTS compras_cartao (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id     INTEGER NOT NULL,
                cartao_id      INTEGER NOT NULL,
                categoria_id   INTEGER NOT NULL,
                grupo_id       INTEGER NOT NULL,
                descricao      TEXT NOT NULL DEFAULT '',
                data_compra    TEXT NOT NULL,
                valor          REAL NOT NULL CHECK (valor > 0),
                parcela        INTEGER NOT NULL DEFAULT 1,
                total_parcelas INTEGER NOT NULL DEFAULT 1,
                fatura         TEXT NOT NULL,
                pago           INTEGER NOT NULL DEFAULT 0,
                lancamento_id  INTEGER,
                criado_em      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (cartao_id) REFERENCES cartoes_credito(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )""",
        DIALETO_SQLSERVER: """
            IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'compras_cartao')
                CREATE TABLE compras_cartao (
                    id             INT IDENTITY(1,1) PRIMARY KEY,
                    usuario_id     INT NOT NULL,
                    cartao_id      INT NOT NULL,
                    categoria_id   INT NOT NULL,
                    grupo_id       INT NOT NULL,
                    descricao      NVARCHAR(200) NOT NULL DEFAULT '',
                    data_compra    DATE NOT NULL,
                    valor          DECIMAL(14,2) NOT NULL CHECK (valor > 0),
                    parcela        INT NOT NULL DEFAULT 1,
                    total_parcelas INT NOT NULL DEFAULT 1,
                    fatura         CHAR(7) NOT NULL,
                    pago           BIT NOT NULL DEFAULT 0,
                    lancamento_id  INT NULL,
                    criado_em      DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY (cartao_id) REFERENCES cartoes_credito(id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
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
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cartao_usu ON cartoes_credito (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cartao_usu' "
                            "AND object_id = OBJECT_ID('dbo.cartoes_credito')) "
                            "CREATE INDEX ix_cartao_usu ON cartoes_credito (usuario_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cc_usu ON compras_cartao (usuario_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cc_usu' "
                            "AND object_id = OBJECT_ID('dbo.compras_cartao')) "
                            "CREATE INDEX ix_cc_usu ON compras_cartao (usuario_id)"),
    },
    # ----- índices operacionais -----
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
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cc_cartao ON compras_cartao (cartao_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cc_cartao' "
                            "AND object_id = OBJECT_ID('dbo.compras_cartao')) "
                            "CREATE INDEX ix_cc_cartao ON compras_cartao (cartao_id)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cc_fatura ON compras_cartao (fatura)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cc_fatura' "
                            "AND object_id = OBJECT_ID('dbo.compras_cartao')) "
                            "CREATE INDEX ix_cc_fatura ON compras_cartao (fatura)"),
    },
    {
        DIALETO_SQLITE: "CREATE INDEX IF NOT EXISTS ix_cc_grupo ON compras_cartao (grupo_id)",
        DIALETO_SQLSERVER: ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_cc_grupo' "
                            "AND object_id = OBJECT_ID('dbo.compras_cartao')) "
                            "CREATE INDEX ix_cc_grupo ON compras_cartao (grupo_id)"),
    },
]

# ----- ALTERs das colunas novas de recorrências (idempotentes) -----
ALTER_RECORRENCIAS = [
    ("frequencia", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN frequencia TEXT NOT NULL DEFAULT 'mensal'",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD frequencia NVARCHAR(10) NOT NULL DEFAULT 'mensal'",
    }),
    ("data_inicio", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN data_inicio TEXT",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD data_inicio DATE NULL",
    }),
    ("data_fim", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN data_fim TEXT",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD data_fim DATE NULL",
    }),
    ("qtd_vezes", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN qtd_vezes INTEGER",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD qtd_vezes INT NULL",
    }),
    ("geradas", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN geradas INTEGER NOT NULL DEFAULT 0",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD geradas INT NOT NULL DEFAULT 0",
    }),
    ("ultimo_gerado_data", {
        DIALETO_SQLITE: "ALTER TABLE recorrencias ADD COLUMN ultimo_gerado_data TEXT",
        DIALETO_SQLSERVER: "ALTER TABLE recorrencias ADD ultimo_gerado_data DATE NULL",
    }),
]

# ----- migração da flag pago dos lançamentos (bancos anteriores) -----
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


def _migrar_dados_recorrencias(db):
    """Converte recorrências do modelo antigo (mes_inicio + dia_do_mes,
    sempre mensal) para o modelo v2. Só roda se houver linhas com
    data_inicio NULL (bancos novos nunca entram aqui)."""
    if not _coluna_existe(db, "recorrencias", "mes_inicio"):
        return
    linhas = db.consultar(
        """SELECT id, mes_inicio, dia_do_mes, ultimo_gerado FROM recorrencias
           WHERE data_inicio IS NULL""")
    for l in linhas:
        mes_inicio = str(l["mes_inicio"] or "").strip()
        if len(mes_inicio) < 7:
            continue
        try:
            ano_i, mes_i = int(mes_inicio[:4]), int(mes_inicio[5:7])
            dia = int(l["dia_do_mes"] or 1)
        except (ValueError, TypeError):
            continue
        dia = max(1, min(dia, dias_no_mes(ano_i, mes_i)))
        data_inicio = f"{ano_i:04d}-{mes_i:02d}-{dia:02d}"

        geradas = 0
        ultimo_data = None
        ug = str(l["ultimo_gerado"] or "").strip()[:7]
        if len(ug) == 7:
            try:
                ano_u, mes_u = int(ug[:4]), int(ug[5:7])
                dia_u = max(1, min(dia, dias_no_mes(ano_u, mes_u)))
                ultimo_data = f"{ano_u:04d}-{mes_u:02d}-{dia_u:02d}"
                geradas = max(1, (ano_u - ano_i) * 12 + (mes_u - mes_i) + 1)
            except (ValueError, TypeError):
                pass
        db.executar(
            """UPDATE recorrencias SET data_inicio = ?, frequencia = 'mensal',
               ultimo_gerado_data = ?, geradas = ? WHERE id = ?""",
            (data_inicio, ultimo_data, geradas, l["id"]), commitar=False)
    db.confirmar()


def _migrar(db):
    """Aplica todas as migrações idempotentes (estrutura e dados)."""
    if not _coluna_existe(db, "lancamentos", "pago"):
        db.executar(MIGRACAO_PAGO[db.dialeto])
    for coluna, sqls in ALTER_RECORRENCIAS:
        if not _coluna_existe(db, "recorrencias", coluna):
            db.executar(sqls[db.dialeto])
    _migrar_dados_recorrencias(db)


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