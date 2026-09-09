SELECT LoteriaId, DezenasKey, COUNT(*) AS Qtd,
       GROUP_CONCAT(NumeroConcurso) AS Concursos
FROM Concursos
GROUP BY LoteriaId, DezenasKey
HAVING COUNT(*) > 1
ORDER BY Qtd DESC
LIMIT 20;