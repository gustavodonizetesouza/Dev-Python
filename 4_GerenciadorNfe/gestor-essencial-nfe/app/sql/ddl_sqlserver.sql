-- Serviço Fiscal NF-e · Gestor Essencial — SQL Server
CREATE TABLE dbo.tb_nfe_nsu (
    id               INT IDENTITY(1,1) PRIMARY KEY,
    cnpj_interessado NVARCHAR(14) NOT NULL UNIQUE,
    ambiente         NVARCHAR(10) NOT NULL DEFAULT 'homologacao',
    ultimo_nsu       BIGINT       NOT NULL DEFAULT 0,
    ultima_consulta  DATETIME2(0) NULL
);
GO

CREATE TABLE dbo.tb_nfe_nota (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    chave               NVARCHAR(44)  NOT NULL UNIQUE,
    numero              INT           NOT NULL,
    serie               INT           NOT NULL DEFAULT 1,
    tipo_operacao       NVARCHAR(1)   NOT NULL,          -- 0=entrada 1=saída
    data_emissao        DATE          NOT NULL,
    modelo              NVARCHAR(2)   NULL,              -- 55=NF-e 65=NFC-e
    valor_total         NUMERIC(15,2) NULL,
    emissor_cnpj        NVARCHAR(14)  NULL,
    emissor_nome        NVARCHAR(200) NULL,
    destinatario_cnpj   NVARCHAR(14)  NULL,
    destinatario_nome   NVARCHAR(200) NULL,
    caminho_xml         NVARCHAR(500) NULL,
    hash_xml            NVARCHAR(64)  NULL,              -- SHA-256
    status_manifestacao NVARCHAR(10)  NULL,
    criado_em           DATETIME2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX ix_nota_emissor_emissao ON dbo.tb_nfe_nota (emissor_cnpj, data_emissao);
CREATE INDEX ix_nota_destinatario   ON dbo.tb_nfe_nota (destinatario_cnpj);
GO

CREATE TABLE dbo.tb_nfe_item (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    nota_id         INT            NOT NULL REFERENCES dbo.tb_nfe_nota(id) ON DELETE CASCADE,
    n_item          INT            NOT NULL,
    codigo          NVARCHAR(60)   NULL,
    descricao       NVARCHAR(250)  NULL,
    ncm             NVARCHAR(8)    NULL,
    cfop            NVARCHAR(4)    NULL,
    unidade         NVARCHAR(6)    NULL,
    quantidade      NUMERIC(15,4)  NULL,
    valor_unitario  NUMERIC(15,2)  NULL,
    valor_total     NUMERIC(15,2)  NULL
);
CREATE INDEX ix_nfe_item_nota ON dbo.tb_nfe_item (nota_id);
GO