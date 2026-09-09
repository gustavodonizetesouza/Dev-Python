WITH dezenas AS (
    SELECT NumeroConcurso, D1  AS dezena FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D2  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D3  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D4  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D5  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D6  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D7  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D8  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D9  FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D10 FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D11 FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D12 FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D13 FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D14 FROM Concursos WHERE LoteriaId = 1
    UNION ALL SELECT NumeroConcurso, D15 FROM Concursos WHERE LoteriaId = 1
)
SELECT dezena, COUNT(*) AS Qtd, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Concursos WHERE LoteriaId = 1), 1) AS PctSorteios
FROM dezenas
GROUP BY dezena
ORDER BY Qtd DESC;