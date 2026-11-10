/* =============================================================
   Gerenciador de Chamados - SQL Server 2019+
   Executar em banco dedicado (ex.: GCH)
   ============================================================= */
CREATE DATABASE GCH;
GO
USE GCH;
GO

/* ---------- USUÁRIOS ---------- */
CREATE TABLE dbo.Usuario (
    id_usuario      INT IDENTITY(1,1) PRIMARY KEY,
    login           VARCHAR(50)   NOT NULL,
    nome            NVARCHAR(120) NOT NULL,
    email           NVARCHAR(150) NULL,
    senha_hash      VARBINARY(64) NOT NULL,   -- PBKDF2/bcrypt
    senha_salt      VARBINARY(32) NOT NULL,
    perfil          VARCHAR(20)   NOT NULL
                    CONSTRAINT CK_Usuario_perfil
                    CHECK (perfil IN ('Admin','Tecnico','Solicitante')),
    ativo           BIT           NOT NULL DEFAULT 1,
    dt_criacao      DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_Usuario_login UNIQUE (login)
);
GO

/* ---------- CATEGORIA / SLA ---------- */
CREATE TABLE dbo.Categoria (
    id_categoria    INT IDENTITY(1,1) PRIMARY KEY,
    nome            NVARCHAR(80)  NOT NULL,
    sla_horas       INT           NOT NULL DEFAULT 24,
    ativo           BIT           NOT NULL DEFAULT 1,
    CONSTRAINT UQ_Categoria_nome UNIQUE (nome)
);
GO

/* ---------- CHAMADO ---------- */
CREATE TABLE dbo.Chamado (
    id_chamado      INT IDENTITY(1,1) PRIMARY KEY,
    numero          AS ('CH-' + RIGHT('000000' + CAST(id_chamado AS VARCHAR(6)), 6)) PERSISTED,
    titulo          NVARCHAR(150) NOT NULL,
    descricao       NVARCHAR(MAX) NOT NULL,       -- solicitação
    id_solicitante  INT           NOT NULL,
    id_tecnico      INT           NULL,
    id_categoria    INT           NOT NULL,
    prioridade      VARCHAR(10)   NOT NULL
                    CONSTRAINT CK_Chamado_prioridade
                    CHECK (prioridade IN ('Baixa','Media','Alta','Critica')),
    status          VARCHAR(20)   NOT NULL DEFAULT 'Aberto'
                    CONSTRAINT CK_Chamado_status
                    CHECK (status IN ('Aberto','EmAnalise','Aguardando','Resolvido','Fechado','Cancelado')),
    resolucao       NVARCHAR(MAX) NULL,
    dt_abertura     DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    dt_fechamento   DATETIME2(0)  NULL,
    rowversion      ROWVERSION,                   -- optimistic locking

    CONSTRAINT FK_Chamado_solicitante FOREIGN KEY (id_solicitante) REFERENCES dbo.Usuario(id_usuario),
    CONSTRAINT FK_Chamado_tecnico     FOREIGN KEY (id_tecnico)     REFERENCES dbo.Usuario(id_usuario),
    CONSTRAINT FK_Chamado_categoria   FOREIGN KEY (id_categoria)   REFERENCES dbo.Categoria(id_categoria)
);
CREATE INDEX IX_Chamado_status      ON dbo.Chamado(status)      INCLUDE (id_tecnico, id_solicitante);
CREATE INDEX IX_Chamado_tecnico     ON dbo.Chamado(id_tecnico);
CREATE INDEX IX_Chamado_solicitante ON dbo.Chamado(id_solicitante);
GO

/* ---------- ERRO APRESENTADO (substitui anexos) ---------- */
CREATE TABLE dbo.Chamado_Erro (
    id_erro         INT IDENTITY(1,1) PRIMARY KEY,
    id_chamado      INT           NOT NULL,
    mensagem        NVARCHAR(MAX) NOT NULL,       -- texto literal exibido na tela
    stack_trace     NVARCHAR(MAX) NULL,           -- opcional, copiado do log
    ambiente        NVARCHAR(80)  NULL,           -- ex.: Protheus 12.1.2410 / Produção
    passos_repro    NVARCHAR(MAX) NULL,           -- como reproduzir
    dt_registro     DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    id_usuario      INT           NOT NULL,

    CONSTRAINT FK_Erro_chamado FOREIGN KEY (id_chamado) REFERENCES dbo.Chamado(id_chamado),
    CONSTRAINT FK_Erro_usuario FOREIGN KEY (id_usuario) REFERENCES dbo.Usuario(id_usuario)
);
CREATE INDEX IX_Erro_chamado ON dbo.Chamado_Erro(id_chamado);
GO

/* ---------- ENVOLVIDOS (N:N) ---------- */
CREATE TABLE dbo.Chamado_Envolvido (
    id_chamado      INT          NOT NULL,
    id_usuario      INT          NOT NULL,
    papel           VARCHAR(20)  NOT NULL DEFAULT 'Observador'
                    CONSTRAINT CK_Envolvido_papel
                    CHECK (papel IN ('Observador','Apoio','Aprovador')),
    dt_vinculo      DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT PK_Chamado_Envolvido PRIMARY KEY (id_chamado, id_usuario),
    CONSTRAINT FK_Envolvido_chamado FOREIGN KEY (id_chamado) REFERENCES dbo.Chamado(id_chamado),
    CONSTRAINT FK_Envolvido_usuario FOREIGN KEY (id_usuario) REFERENCES dbo.Usuario(id_usuario)
);
GO

/* ---------- INTERAÇÕES / TIMELINE ---------- */
CREATE TABLE dbo.Interacao (
    id_interacao    INT IDENTITY(1,1) PRIMARY KEY,
    id_chamado      INT          NOT NULL,
    id_usuario      INT          NOT NULL,
    tipo            VARCHAR(20)  NOT NULL DEFAULT 'Comentario'
                    CONSTRAINT CK_Interacao_tipo
                    CHECK (tipo IN ('Comentario','MudancaStatus','Atribuicao','Sistema')),
    texto           NVARCHAR(MAX) NULL,
    dt_interacao    DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(),

    CONSTRAINT FK_Interacao_chamado FOREIGN KEY (id_chamado) REFERENCES dbo.Chamado(id_chamado),
    CONSTRAINT FK_Interacao_usuario FOREIGN KEY (id_usuario) REFERENCES dbo.Usuario(id_usuario)
);
CREATE INDEX IX_Interacao_chamado ON dbo.Interacao(id_chamado, dt_interacao);
GO

/* ---------- BASE DE CONHECIMENTO ---------- */
CREATE TABLE dbo.KB_Artigo (
    id_artigo        INT IDENTITY(1,1) PRIMARY KEY,
    id_chamado_origem INT          NULL,          -- rastreabilidade
    titulo           NVARCHAR(150) NOT NULL,
    sintoma          NVARCHAR(MAX) NOT NULL,      -- a mensagem de erro
    causa_raiz       NVARCHAR(MAX) NULL,
    solucao          NVARCHAR(MAX) NOT NULL,
    tags             NVARCHAR(300) NULL,
    id_autor         INT           NOT NULL,
    publicado        BIT           NOT NULL DEFAULT 0,
    visualizacoes    INT           NOT NULL DEFAULT 0,
    dt_criacao       DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    dt_atualizacao   DATETIME2(0)  NULL,

    CONSTRAINT FK_KB_chamado FOREIGN KEY (id_chamado_origem) REFERENCES dbo.Chamado(id_chamado),
    CONSTRAINT FK_KB_autor   FOREIGN KEY (id_autor)           REFERENCES dbo.Usuario(id_usuario)
);
CREATE INDEX IX_KB_publicado ON dbo.KB_Artigo(publicado) INCLUDE (titulo);
GO