SELECT c.NumeroConcurso, c.DezenasKey
FROM Concursos c
JOIN Loterias l ON l.Id = c.LoteriaId
WHERE l.Nome = 'Lotofácil'
  AND (c.D1  IN (c.D2,c.D3,c.D4,c.D5,c.D6,c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D2  IN (c.D3,c.D4,c.D5,c.D6,c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D3  IN (c.D4,c.D5,c.D6,c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D4  IN (c.D5,c.D6,c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D5  IN (c.D6,c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D6  IN (c.D7,c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D7  IN (c.D8,c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D8  IN (c.D9,c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D9  IN (c.D10,c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D10 IN (c.D11,c.D12,c.D13,c.D14,c.D15)
    OR c.D11 IN (c.D12,c.D13,c.D14,c.D15)
    OR c.D12 IN (c.D13,c.D14,c.D15)
    OR c.D13 IN (c.D14,c.D15)
    OR c.D14 IN (c.D15));