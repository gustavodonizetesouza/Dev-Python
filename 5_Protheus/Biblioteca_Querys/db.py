# ============================================================
# db.py - Camada de acesso ao banco (SQL Server / Protheus)
#   - Conexão via pyodbc (somente leitura)
#   - Lê as configurações atuais via config.py (config.json)
#   - Conversão de datas padrão Protheus (CYYMMDD)
#   - Suporte a cancelamento da query em execução
# ============================================================
import pyodbc
import pandas as pd
from datetime import datetime

import config

# Limite de linhas aplicado automaticamente quando o SQL não traz TOP
LIMITE_PADRAO = 5000


class CancelaConsulta(Exception):
    """Exceção interna para sinalizar que a consulta foi cancelada pelo usuário."""
    pass


class ExecucaoQuery:
    """
    Ponte entre a interface e a thread em execução.
    Permite cancelar a query que está rodando no banco.
    """

    def __init__(self):
        self.conn = None
        self.cancelada = False

    def cancelar(self):
        """Cancela a operação em andamento no servidor (via ODBC)."""
        self.cancelada = True
        conn = self.conn
        if conn is not None:
            try:
                conn.cancel()
            except Exception:
                pass


def testar_conexao(custom_cfg: dict = None) -> str:
    """Testa a conexão e devolve mensagem de status.

    custom_cfg: dict opcional com os dados da tela de configuração
    (permite testar ANTES de salvar).
    """
    try:
        with pyodbc.connect(config.montar_connection_string(custom_cfg),
                            timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT @@VERSION")
                versao = cur.fetchone()[0]
        return f"Conectado! SQL Server: {versao.splitlines()[0]}"
    except Exception as e:
        return f"Falha na conexão: {e}"


# ---------- Datas Protheus ----------
def data_para_protheus(texto: str, formato: str = "cyymmdd") -> str:
    """
    Converte 'DD/MM/AAAA' para o formato usado no filtro.
    formato 'aaaammdd' -> 20260930
    formato 'cyymmdd'  -> 2260930
    """
    dt = datetime.strptime(texto.strip(), "%d/%m/%Y")
    if formato == "aaaammdd":
        return dt.strftime("%Y%m%d")
    c = 2 if dt.year >= 2000 else 1
    return f"{c}{dt.year % 100:02d}{dt.month:02d}{dt.day:02d}"


def protheus_para_data(valor) -> datetime:
    """Converte CYYMMDD -> datetime. Ex: 2260930 -> 2026-09-30."""
    if not valor:
        return None
    try:
        c = valor // 1000000
        resto = valor % 1000000
        yy = resto // 10000
        mm = (resto % 10000) // 100
        dd = resto % 100
        ano = 1900 + (c - 1) * 100 + yy
        return datetime(ano, mm, dd)
    except Exception:
        return None


# ---------- Execução ----------
def executar_query(sql: str, execucao: ExecucaoQuery = None) -> pd.DataFrame:
    """
    Executa a query (somente leitura) e devolve um DataFrame.

    Parâmetros:
        sql      : comando SELECT
        execucao : objeto ExecucaoQuery (opcional). Permite que a interface
                   cancele a query em andamento pelo botão "Parar".

    - Bloqueia SQL que não comece com SELECT (proteção)
    - Aplica TOP LIMITE_PADRAO quando o SQL não traz limite
    - Converte colunas de data no padrão Protheus (CYYMMDD) para datetime
    - Se cancelado, levanta CancelaConsulta (os dados parciais são descartados)
    """
    sql = sql.strip().rstrip(";")
    if not sql.upper().startswith("SELECT"):
        raise ValueError(
            "A consulta precisa começar com SELECT (apenas leitura é permitido).")

    if "TOP " not in sql.upper() and "SET ROWCOUNT" not in sql.upper():
        sql = sql.replace("SELECT", f"SELECT TOP {LIMITE_PADRAO}", 1)

    conf = config.carregar_config()
    conn = pyodbc.connect(config.montar_connection_string(conf),
                          timeout=int(conf.get("timeout", 30)))
    if execucao is not None:
        execucao.conn = conn  # expõe a conexão para o botão "Parar" cancelar

    try:
        df = pd.read_sql(sql, conn)

        # Se o usuário clicou em "Parar" enquanto o banco respondia,
        # descarta o resultado mesmo que a query tenha terminado.
        if execucao is not None and execucao.cancelada:
            raise CancelaConsulta()
    except Exception as e:
        # Erro comum ao cancelar: HY008 (Operation canceled).
        if execucao is not None and execucao.cancelada:
            raise CancelaConsulta() from e
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass
        if execucao is not None:
            execucao.conn = None

    # Converte colunas de data no padrão Protheus (nomes F* + inteiro)
    for col in df.columns:
        if col.upper().startswith("F") and df[col].dtype == "int64":
            df[col] = df[col].apply(protheus_para_data)

    return df


# ---------- Exportação XLSX ----------
def exportar_xlsx(df: pd.DataFrame, caminho: str):
    """Exporta o DataFrame para Excel com largura de coluna ajustada."""
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultado")
        ws = writer.sheets["Resultado"]
        for coluna in ws.columns:
            comprimento = max(len(str(celula.value))
                              for celula in coluna if celula.value)
            ws.column_dimensions[coluna[0].column_letter].width = min(
                comprimento + 4, 60)
