CREATE VIEW dbo.vw_Chamado_Visivel
AS
SELECT
    c.id_chamado,
    c.numero,
    c.titulo,
    c.descricao,
    c.status,
    c.prioridade,
    c.dt_abertura,
    c.dt_fechamento,
    c.resolucao,
    c.id_solicitante,
    c.id_tecnico,
    c.id_categoria,
    u_sol.nome  AS solicitante,
    u_tec.nome  AS tecnico,
    cat.nome    AS categoria,

    /* ---- REGRAS DE ACESSO CALCULADAS ---- */
    CAST(CASE WHEN
        EXISTS (SELECT 1 FROM dbo.Usuario x
                WHERE x.login = SUSER_SNAME() AND x.perfil = 'Admin')
      OR c.id_solicitante = (SELECT id_usuario FROM dbo.Usuario WHERE login = SUSER_SNAME())
      OR c.id_tecnico     = (SELECT id_usuario FROM dbo.Usuario WHERE login = SUSER_SNAME())
      OR EXISTS (SELECT 1 FROM dbo.Chamado_Envolvido e
                 JOIN dbo.Usuario eu ON eu.id_usuario = e.id_usuario
                 WHERE e.id_chamado = c.id_chamado
                   AND eu.login = SUSER_SNAME())
    THEN 1 ELSE 0 END AS BIT)                        AS pode_ver,

    CAST(CASE WHEN c.status <> 'Fechado' AND (
        EXISTS (SELECT 1 FROM dbo.Usuario x
                WHERE x.login = SUSER_SNAME() AND x.perfil IN ('Admin','Tecnico'))
      OR c.id_tecnico = (SELECT id_usuario FROM dbo.Usuario WHERE login = SUSER_SNAME())
    ) THEN 1 ELSE 0 END AS BIT)                      AS pode_editar
FROM dbo.Chamado c
JOIN dbo.Usuario    u_sol ON u_sol.id_usuario = c.id_solicitante
LEFT JOIN dbo.Usuario u_tec ON u_tec.id_usuario = c.id_tecnico
JOIN dbo.Categoria  cat   ON cat.id_categoria = c.id_categoria;
GO