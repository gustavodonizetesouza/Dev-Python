SELECT LoteriaId, NumeroConcurso, COUNT(*) AS Qtd
FROM Concursos
GROUP BY LoteriaId, NumeroConcurso
HAVING COUNT(*) > 1;