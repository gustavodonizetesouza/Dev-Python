/* ============================================================
   Provisionamento do acesso da aplicação
   Rodar uma única vez, com conta sysadmin/db_owner
   ============================================================ */

USE master;
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'app_chamados')
BEGIN
    CREATE LOGIN app_chamados
        WITH PASSWORD = 'TrocarEstaSenha!2026',
             CHECK_POLICY = ON,
             CHECK_EXPIRATION = ON,
             DEFAULT_DATABASE = GCH;
    PRINT 'LOGIN criado.';
END
ELSE
    PRINT 'LOGIN já existe.';
GO

USE GCH;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'app_chamados')
BEGIN
    CREATE USER app_chamados FOR LOGIN app_chamados WITH DEFAULT_SCHEMA = dbo;
    PRINT 'USER criado.';
END
ELSE
    PRINT 'USER já existe.';
GO

GRANT EXECUTE ON dbo.sp_Usuario_Autenticar     TO app_chamados;
GRANT EXECUTE ON dbo.sp_Chamado_Listar         TO app_chamados;
GRANT EXECUTE ON dbo.sp_Chamado_Obter          TO app_chamados;
GRANT EXECUTE ON dbo.sp_Chamado_Salvar         TO app_chamados;
GRANT EXECUTE ON dbo.sp_Chamado_Erro_Registrar TO app_chamados;
GRANT EXECUTE ON dbo.sp_Chamado_MudarStatus    TO app_chamados;
GRANT EXECUTE ON dbo.sp_KB_PublicarDoChamado   TO app_chamados;
GRANT EXECUTE ON dbo.sp_KB_Buscar              TO app_chamados;
PRINT 'Permissões aplicadas.';
GO