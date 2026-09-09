SELECT l.Nome,
       COUNT(c.Id)             AS TotalConcursos,
       MIN(c.NumeroConcurso)   AS ConcursoInicial,
       MAX(c.NumeroConcurso)   AS ConcursoFinal,
       MIN(c.DataSorteio)      AS PrimeiraData,
       MAX(c.DataSorteio)      AS UltimaData
FROM Concursos c
JOIN Loterias l ON l.Id = c.LoteriaId
GROUP BY l.Nome;