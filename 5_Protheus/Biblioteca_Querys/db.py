import pyodbc
import pandas as pd
from datetime import datetime
from config import CONNECTION_STRING


def testar_conexao() -> str:
    try:
        with pyodbc.connect(CONNECTION_STRING, timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT @@VERSION")
                versao = cur.fetchone()[0]
        return f"Conectado! SQL Server: {versao.splitlines()[0]}"
    except Exception as e:
        return f"Falha na conexão: {e}"


# ---------- Datas Protheus ----------
def data_para_protheus(texto: str, formato: str = "cyymmdd") -> str:
    """Converte 'DD/MM/AAAA' -> formato Protheus (CYYMMDD ou AAAAAMMDD)."""
    dt = datetime.strptime(texto.strip(), "%d/%m/%Y")
    if formato == "aaaammdd":
        return dt.strftime("%Y%m%d")
    # CYYMMDD: C=2 para anos 2000+, YY = ano no século
    c = 2 if dt.year >= 2000 else 1
    yy = dt.year % 100
    return f"{c}{yy:02d}{dt.month:02d}{dt.day:02d}"


def protheus_para_data(valor) -> datetime:
    """Converte CYYMMDD -> datetime. Ex: 2260930 -> 2026-09-30."""
    if not valor:
        return None
    c = valor // 1000000
    resto = valor % 1000000
    yy = resto // 10000
    mm = (resto % 10000) // 100
    dd = resto % 100
    ano = 1900 + (c - 1) * 100 + yy
    try:
        return datetime(ano, mm, dd)
    except Exception:
        return None


# ---------- Execução ----------
def executar_query(sql: str) -> pd.DataFrame:
    sql = sql.strip().rstrip(";")
    if "TOP " not in sql.upper() and "SET ROWCOUNT" not in sql.upper():
        sql = sql.replace("SELECT", "SELECT TOP 5000", 1)

    with pyodbc.connect(CONNECTION_STRING, timeout=30) as conn:
        df = pd.read_sql(sql, conn)

    # Converte colunas de data no padrão CYYMMDD (nomes começando com F + int)
    for col in df.columns:
        if col.upper().startswith("F") and df[col].dtype == "int64":
            df[col] = df[col].apply(protheus_para_data)
    return df


def exportar_xlsx(df: pd.DataFrame, caminho: str):
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultado")
        ws = writer.sheets["Resultado"]
        for coluna in ws.columns:
            comprimento = max(len(str(celula.value))
                              for celula in coluna if celula.value)
            ws.column_dimensions[coluna[0].column_letter].width = min(
                comprimento + 4, 60)
