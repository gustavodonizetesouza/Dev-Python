# ============================================================
# CAMADA DE ACESSO AO BANCO
# ============================================================
import pyodbc
import pandas as pd
from config import CONNECTION_STRING


def testar_conexao() -> str:
    """Testa a conexão e retorna mensagem de status."""
    try:
        with pyodbc.connect(CONNECTION_STRING, timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT @@VERSION")
                versao = cur.fetchone()[0]
        return f"Conectado! SQL Server: {versao.splitlines()[0]}"
    except Exception as e:
        return f"Falha na conexão: {e}"


def executar_query(sql: str) -> pd.DataFrame:
    """
    Executa a query e retorna um DataFrame.
    - Limita a quantidade de linhas para não travar a tela.
    - Converte colunas de data (formato Protheus CYYMMDD) quando detectadas.
    """
    sql = sql.strip().rstrip(";")

    # Segurança: se não houver TOP, aplica limite nas primeiras consultas
    if "TOP " not in sql.upper() and "SET ROWCOUNT" not in sql.upper():
        sql = sql.replace("SELECT", "SELECT TOP 5000", 1)

    with pyodbc.connect(CONNECTION_STRING, timeout=30) as conn:
        df = pd.read_sql(sql, conn)

    # Converte datas no padrão Protheus (CYYMMDD) para datetime
    for col in df.columns:
        if col.upper().startswith("F") and df[col].dtype == "int64":
            df[col] = _converter_data_protheus(df[col])

    return df


def _converter_data_protheus(serie: pd.Series) -> pd.Series:
    """Converte data Protheus CYYMMDD -> datetime. Ex: 2230520 -> 2023-05-20"""
    def converter(valor):
        if pd.isna(valor) or valor == 0:
            return None
        try:
            # CYYMMDD: o primeiro dígito é o século (2 = 2000)
            ano = 1900 + (valor // 10000)
            resto = valor % 10000
            mes = resto // 100
            dia = resto % 100
            return pd.Timestamp(year=ano, month=mes, day=dia)
        except Exception:
            return None
    return serie.apply(converter)


def exportar_xlsx(df: pd.DataFrame, caminho: str):
    """Exporta o DataFrame para Excel com formatação básica."""
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultado")

        # Ajusta largura das colunas automaticamente
        ws = writer.sheets["Resultado"]
        for coluna in ws.columns:
            comprimento = max(len(str(celula.value))
                              for celula in coluna if celula.value)
            ws.column_dimensions[coluna[0].column_letter].width = min(
                comprimento + 4, 60)
