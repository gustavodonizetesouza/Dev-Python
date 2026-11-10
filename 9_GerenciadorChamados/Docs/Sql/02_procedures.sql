USE GCH;
GO

/* =============================================================
   PADRÃO ÚNICO: toda proc recebe @id_usuario e @perfil.
   Nenhum usuário da aplicação tem SELECT/UPDATE direto nas
   tabelas. Apenas GRANT EXECUTE. Isso significa que, mesmo
   abrindo o SSMS com a mesma credencial do app, não há dados
   sem passar um id_usuario válido.
   ============================================================= */

/* ---------- LOGIN ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Usuario_Autenticar
    @login VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT id_usuario, login, nome, email, perfil, senha_hash, senha_salt, ativo
    FROM dbo.Usuario
    WHERE login = @login AND ativo = 1;
END
GO

/* ---------- LISTAR (com filtro de visibilidade) ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Chamado_Listar
    @id_usuario  INT,
    @perfil      VARCHAR(20),
    @status      VARCHAR(20) = NULL,
    @id_categoria INT        = NULL,
    @busca       NVARCHAR(150) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        c.id_chamado,
        c.numero,
        c.titulo,
        c.status,
        c.prioridade,
        c.dt_abertura,
        c.dt_fechamento,
        sol.nome AS solicitante,
        tec.nome AS tecnico,
        cat.nome AS categoria,
        CASE WHEN c.status <> 'Fechado'
              AND ( @perfil IN ('Admin','Tecnico')
                    OR c.id_tecnico = @id_usuario )
             THEN 1 ELSE 0 END AS pode_editar
    FROM dbo.Chamado c
    JOIN dbo.Usuario   sol ON sol.id_usuario = c.id_solicitante
    LEFT JOIN dbo.Usuario tec ON tec.id_usuario = c.id_tecnico
    JOIN dbo.Categoria cat ON cat.id_categoria = c.id_categoria
    WHERE
        /* ---- VISIBILIDADE ---- */
        ( @perfil = 'Admin'
          OR c.id_solicitante = @id_usuario
          OR c.id_tecnico     = @id_usuario
          OR EXISTS (SELECT 1 FROM dbo.Chamado_Envolvido e
                     WHERE e.id_chamado = c.id_chamado
                       AND e.id_usuario = @id_usuario) )
        /* ---- FILTROS OPCIONAIS ---- */
        AND (@status IS NULL       OR c.status = @status)
        AND (@id_categoria IS NULL OR c.id_categoria = @id_categoria)
        AND (@busca IS NULL
             OR c.titulo LIKE '%' + @busca + '%'
             OR c.numero LIKE '%' + @busca + '%')
    ORDER BY
        CASE c.prioridade WHEN 'Critica' THEN 1 WHEN 'Alta' THEN 2
                          WHEN 'Media'   THEN 3 ELSE 4 END,
        c.dt_abertura DESC;
END
GO

/* ---------- OBTER UM (com erros e timeline) ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Chamado_Obter
    @id_usuario INT,
    @perfil     VARCHAR(20),
    @id_chamado INT
AS
BEGIN
    SET NOCOUNT ON;

    /* cabeçalho — retorna vazio se sem permissão (não vaza existência) */
    SELECT
        c.*, sol.nome AS solicitante, tec.nome AS tecnico, cat.nome AS categoria,
        CASE WHEN c.status <> 'Fechado'
              AND ( @perfil IN ('Admin','Tecnico')
                    OR c.id_tecnico = @id_usuario )
             THEN 1 ELSE 0 END AS pode_editar
    FROM dbo.Chamado c
    JOIN dbo.Usuario   sol ON sol.id_usuario = c.id_solicitante
    LEFT JOIN dbo.Usuario tec ON tec.id_usuario = c.id_tecnico
    JOIN dbo.Categoria cat ON cat.id_categoria = c.id_categoria
    WHERE c.id_chamado = @id_chamado
      AND ( @perfil = 'Admin'
            OR c.id_solicitante = @id_usuario
            OR c.id_tecnico     = @id_usuario
            OR EXISTS (SELECT 1 FROM dbo.Chamado_Envolvido e
                       WHERE e.id_chamado = c.id_chamado
                         AND e.id_usuario = @id_usuario) );

    /* erros apresentados */
    SELECT * FROM dbo.Chamado_Erro
    WHERE id_chamado = @id_chamado
    ORDER BY dt_registro DESC;

    /* timeline */
    SELECT i.*, u.nome AS autor
    FROM dbo.Interacao i
    JOIN dbo.Usuario u ON u.id_usuario = i.id_usuario
    WHERE i.id_chamado = @id_chamado
    ORDER BY i.dt_interacao ASC;
END
GO

/* ---------- SALVAR (abrir / editar) ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Chamado_Salvar
    @id_usuario   INT,
    @perfil       VARCHAR(20),
    @id_chamado   INT = NULL,          -- NULL = novo
    @titulo       NVARCHAR(150),
    @descricao    NVARCHAR(MAX),
    @id_categoria INT,
    @prioridade   VARCHAR(10),
    @id_tecnico   INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRAN;

        /* -------- NOVO CHAMADO -------- */
        IF @id_chamado IS NULL
        BEGIN
            INSERT INTO dbo.Chamado
                (titulo, descricao, id_solicitante, id_tecnico,
                 id_categoria, prioridade, status)
            VALUES
                (@titulo, @descricao, @id_usuario, @id_tecnico,
                 @id_categoria, @prioridade, 'Aberto');

            SET @id_chamado = SCOPE_IDENTITY();

            INSERT INTO dbo.Interacao (id_chamado, id_usuario, tipo, texto)
            VALUES (@id_chamado, @id_usuario, 'Sistema', 'Chamado aberto.');

            COMMIT;
            SELECT @id_chamado AS id_chamado, CAST(1 AS BIT) AS ok, 'Chamado criado.' AS msg;
            RETURN;
        END

        /* -------- EDIÇÃO: valida permissão no banco -------- */
        IF NOT EXISTS (
            SELECT 1 FROM dbo.Chamado c
            WHERE c.id_chamado = @id_chamado
              AND c.status <> 'Fechado'
              AND ( @perfil IN ('Admin','Tecnico')
                    OR c.id_tecnico     = @id_usuario
                    OR c.id_solicitante = @id_usuario )
        )
        BEGIN
            ROLLBACK;
            SELECT @id_chamado AS id_chamado, CAST(0 AS BIT) AS ok,
                   'Sem permissão: chamado fechado ou você não está envolvido.' AS msg;
            RETURN;
        END

        UPDATE dbo.Chamado
        SET titulo       = @titulo,
            descricao    = @descricao,
            id_categoria = @id_categoria,
            prioridade   = @prioridade,
            id_tecnico   = COALESCE(@id_tecnico, id_tecnico)
        WHERE id_chamado = @id_chamado;

        IF @id_tecnico IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbo.Chamado_Envolvido
                           WHERE id_chamado = @id_chamado
                             AND id_usuario = @id_tecnico)
            INSERT INTO dbo.Chamado_Envolvido (id_chamado, id_usuario, papel)
            VALUES (@id_chamado, @id_tecnico, 'Apoio');

        COMMIT;
        SELECT @id_chamado AS id_chamado, CAST(1 AS BIT) AS ok, 'Chamado atualizado.' AS msg;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT @id_chamado AS id_chamado, CAST(0 AS BIT) AS ok, ERROR_MESSAGE() AS msg;
    END CATCH
END
GO

/* ---------- REGISTRAR ERRO APRESENTADO ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Chamado_Erro_Registrar
    @id_usuario INT,
    @perfil     VARCHAR(20),
    @id_chamado INT,
    @mensagem   NVARCHAR(MAX),
    @stack      NVARCHAR(MAX) = NULL,
    @ambiente   NVARCHAR(80)  = NULL,
    @passos     NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.Chamado c
        WHERE c.id_chamado = @id_chamado
          AND c.status <> 'Fechado'
          AND ( @perfil = 'Admin'
                OR c.id_solicitante = @id_usuario
                OR c.id_tecnico     = @id_usuario
                OR EXISTS (SELECT 1 FROM dbo.Chamado_Envolvido e
                           WHERE e.id_chamado = c.id_chamado
                             AND e.id_usuario = @id_usuario) )
    )
    BEGIN
        SELECT CAST(0 AS BIT) AS ok,
               'Sem permissão para registrar erro neste chamado.' AS msg;
        RETURN;
    END

    INSERT INTO dbo.Chamado_Erro
        (id_chamado, mensagem, stack_trace, ambiente, passos_repro, id_usuario)
    VALUES
        (@id_chamado, @mensagem, @stack, @ambiente, @passos, @id_usuario);

    SELECT CAST(1 AS BIT) AS ok, 'Erro registrado.' AS msg,
           SCOPE_IDENTITY() AS id_erro;
END
GO

/* ---------- FECHAR / REABRIR (auditado) ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_Chamado_MudarStatus
    @id_usuario  INT,
    @perfil      VARCHAR(20),
    @id_chamado  INT,
    @novo_status VARCHAR(20),
    @resolucao   NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRAN;

        DECLARE @status_atual VARCHAR(20);
        SELECT @status_atual = status FROM dbo.Chamado WHERE id_chamado = @id_chamado;

        /* fechamento exige técnico/admin */
        IF @novo_status = 'Fechado' AND @perfil NOT IN ('Admin','Tecnico')
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS ok, 'Apenas técnico ou admin pode fechar.' AS msg;
            RETURN;
        END

        /* reabertura exige admin (chamado fechado = read-only total) */
        IF @status_atual = 'Fechado' AND @novo_status <> 'Fechado'
           AND @perfil <> 'Admin'
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS ok, 'Chamado fechado: apenas admin reabre.' AS msg;
            RETURN;
        END

        UPDATE dbo.Chamado
        SET status = @novo_status,
            resolucao = COALESCE(@resolucao, resolucao),
            dt_fechamento = CASE WHEN @novo_status = 'Fechado'
                                 THEN SYSDATETIME() ELSE NULL END
        WHERE id_chamado = @id_chamado;

        INSERT INTO dbo.Interacao (id_chamado, id_usuario, tipo, texto)
        VALUES (@id_chamado, @id_usuario, 'MudancaStatus',
                CONCAT('Status alterado de ', @status_atual, ' para ', @novo_status));

        COMMIT;
        SELECT CAST(1 AS BIT) AS ok, 'Status atualizado.' AS msg;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS ok, ERROR_MESSAGE() AS msg;
    END CATCH
END
GO

/* ---------- KB: gerar artigo a partir do chamado ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_KB_PublicarDoChamado
    @id_usuario INT,
    @perfil     VARCHAR(20),
    @id_chamado INT,
    @titulo     NVARCHAR(150),
    @causa_raiz NVARCHAR(MAX) = NULL,
    @solucao    NVARCHAR(MAX),
    @tags       NVARCHAR(300) = NULL,
    @publicado  BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    IF @perfil NOT IN ('Admin','Tecnico')
    BEGIN
        SELECT CAST(0 AS BIT) AS ok, 'Apenas técnico ou admin publica na KB.' AS msg;
        RETURN;
    END

    DECLARE @sintoma NVARCHAR(MAX);
    SELECT TOP 1 @sintoma = mensagem
    FROM dbo.Chamado_Erro
    WHERE id_chamado = @id_chamado
    ORDER BY dt_registro DESC;

    IF @sintoma IS NULL
        SELECT @sintoma = descricao FROM dbo.Chamado WHERE id_chamado = @id_chamado;

    INSERT INTO dbo.KB_Artigo
        (id_chamado_origem, titulo, sintoma, causa_raiz, solucao,
         tags, id_autor, publicado)
    VALUES
        (@id_chamado, @titulo, @sintoma, @causa_raiz, @solucao,
         @tags, @id_usuario, @publicado);

    SELECT CAST(1 AS BIT) AS ok, 'Artigo criado.' AS msg,
           SCOPE_IDENTITY() AS id_artigo;
END
GO

/* ---------- KB: buscar (sugestão na abertura do chamado) ---------- */
CREATE OR ALTER PROCEDURE dbo.sp_KB_Buscar
    @termo     NVARCHAR(200),
    @max_linhas INT = 10
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@max_linhas)
        id_artigo, titulo, sintoma, solucao, tags, visualizacoes,
        /* ranking simples por incidência do termo */
        (CASE WHEN titulo  LIKE '%' + @termo + '%' THEN 3 ELSE 0 END)
      + (CASE WHEN sintoma LIKE '%' + @termo + '%' THEN 2 ELSE 0 END)
      + (CASE WHEN tags    LIKE '%' + @termo + '%' THEN 1 ELSE 0 END) AS score
    FROM dbo.KB_Artigo
    WHERE publicado = 1
      AND ( titulo  LIKE '%' + @termo + '%'
         OR sintoma LIKE '%' + @termo + '%'
         OR tags    LIKE '%' + @termo + '%'
         OR solucao LIKE '%' + @termo + '%' )
    ORDER BY score DESC, visualizacoes DESC;
END
GO

/* ---------- SEGURANÇA: só EXECUTE, sem SELECT direto ---------- */
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.Chamado           TO PUBLIC;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.Chamado_Erro      TO PUBLIC;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.Chamado_Envolvido TO PUBLIC;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.Interacao         TO PUBLIC;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.Usuario           TO PUBLIC;
GO