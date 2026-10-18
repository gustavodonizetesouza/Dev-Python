"""Funções utilitárias compartilhadas: caminhos do projeto, moeda e datas."""
import calendar
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos absolutos do projeto — derivados da localização deste arquivo.
# core/util.py -> sobe 2 níveis até a raiz (pasta onde está o main.py).
# Isso garante que config.json e o banco SQLite SEMPRE fiquem dentro da
# pasta do projeto, independentemente do diretório de trabalho (CWD)
# usado ao executar: terminal, VS Code, .bat ou IDE.
# ---------------------------------------------------------------------------
DIR_BASE = Path(__file__).resolve().parent.parent
CAMINHO_CONFIG = DIR_BASE / "config.json"

NOMES_MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
               "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def fmt_moeda(valor) -> str:
    """Formata como moeda brasileira: R$ 1.234,56"""
    v = float(valor or 0)
    s = f"{v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {s}"


def fmt_moeda_compacta(valor) -> str:
    """Versão curta para eixos de gráfico: R$ 1,2 mil / R$ 3,4 mi"""
    v = float(valor or 0)
    if abs(v) >= 1_000_000:
        return ("R$ " + f"{v / 1_000_000:.1f} mi").replace(".", ",")
    if abs(v) >= 1_000:
        return ("R$ " + f"{v / 1_000:.1f} mil").replace(".", ",")
    return fmt_moeda(v)


def fmt_data(iso: str) -> str:
    """'2026-01-05' -> '05/01/2026'"""
    try:
        a, m, d = str(iso)[:10].split("-")
        return f"{d}/{m}/{a}"
    except ValueError:
        return str(iso)


def nome_mes(ano: int, mes: int) -> str:
    return f"{NOMES_MESES[mes - 1]}/{ano}"


def fmt_mes_curto(ym: str) -> str:
    """'2026-01' -> 'Jan/26'"""
    ano, mes = int(ym[:4]), int(ym[5:7])
    return f"{MESES_ABREV[mes - 1]}/{str(ano)[2:]}"


def dias_no_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]


def avancar_mes(ano: int, mes: int):
    mes += 1
    if mes > 12:
        mes, ano = 1, ano + 1
    return ano, mes


def mes_anterior(ano: int, mes: int):
    mes -= 1
    if mes < 1:
        mes, ano = 12, ano - 1
    return ano, mes


def primeiro_dia(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}-01"


def ultimo_dia(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}-{dias_no_mes(ano, mes):02d}"


def hoje_iso() -> str:
    return date.today().isoformat()
