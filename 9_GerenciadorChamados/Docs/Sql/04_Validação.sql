USE GCH;
GO

-- 1. Quem eu sou de verdade?
SELECT
    SUSER_SNAME()                    AS login_atual,
    USER_NAME()                      AS usuario_banco,
    IS_SRVROLEMEMBER('sysadmin')     AS eh_sysadmin,
    IS_MEMBER('app_chamados')        AS eh_app;
GO

-- 2. A tabela tem dados?
SELECT COUNT(*) AS total_chamados FROM dbo.Chamado;
GO

-- 3. A proc existe e está íntegra?
SELECT name, type_desc, modify_date
FROM sys.objects
WHERE name LIKE 'sp_Chamado%' OR name LIKE 'sp_KB%' OR name LIKE 'sp_Usuario%';
GO

-- 4. O DENY está registrado?
SELECT
    dp.name       AS principal,
    dp.type_desc  AS tipo,
    o.name        AS objeto,
    p.permission_name,
    p.state_desc
FROM sys.database_permissions p
JOIN sys.objects o            ON o.object_id   = p.major_id
JOIN sys.database_principals dp ON dp.principal_id = p.grantee_principal_id
WHERE o.name IN ('Chamado','Chamado_Erro','Usuario','Interacao','Chamado_Envolvido');
GO