# ============================================================
# PDF EXPORT - Relatórios em A4 Paisagem
# Dependência: reportlab
# ============================================================
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Table,
                                TableStyle)

MARGEM = 12 * mm


def _escape(texto: str) -> str:
    """Escapa caracteres XML usados pelo Paragraph do reportlab."""
    return (texto.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))


def _limpar(texto: str) -> str:
    """Remove caracteres fora do Latin-1 (evita crash com aspas curvas, em-dash)."""
    return texto.encode("latin-1", errors="ignore").decode("latin-1")


def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        MARGEM, 7 * mm, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}")
    canvas.drawRightString(
        landscape(A4)[0] - MARGEM, 7 * mm, f"Página {doc.page}")
    canvas.restoreState()


def exportar_pdf(df: pd.DataFrame, caminho: str, titulo: str = "Relatório Protheus"):
    """
    Gera PDF A4 paisagem com:
    - Cabeçalho repetido em todas as páginas (repeatRows=1)
    - Linhas zebradas e grade leve
    - Quebra de linha automática nas células (Paragraph)
    - Datas no formato DD/MM/AAAA, números com separador de milhar
    """
    dados = df.copy()

    # Formata cada coluna pelo tipo, ANTES de montar o PDF
    for col in dados.columns:
        if pd.api.types.is_datetime64_any_dtype(dados[col]):
            dados[col] = dados[col].dt.strftime("%d/%m/%Y")
        elif pd.api.types.is_integer_dtype(dados[col]):
            dados[col] = dados[col].apply(
                lambda v: "" if pd.isna(v) else f"{v:,}".replace(",", "."))
        elif pd.api.types.is_float_dtype(dados[col]):
            def fmt_float(v):
                if pd.isna(v):
                    return ""
                if v == int(v):
                    return f"{int(v):,}".replace(",", ".")
                return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            dados[col] = dados[col].apply(fmt_float)
        else:
            dados[col] = dados[col].fillna("").astype(str)

    page = landscape(A4)  # 297mm x 210mm
    doc = SimpleDocTemplate(
        caminho,
        pagesize=page,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=titulo,
        onFirstPage=_rodape,
        onLaterPages=_rodape,
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle("Titulo", parent=estilos["Title"],
                                   fontSize=13, spaceAfter=3 * mm)
    estilo_meta = ParagraphStyle("Meta", parent=estilos["Normal"],
                                 fontSize=8, textColor=colors.grey, spaceAfter=4 * mm)
    estilo_cab = ParagraphStyle("Cab", parent=estilos["Normal"],
                                fontName="Helvetica-Bold", fontSize=7.5,
                                textColor=colors.white, leading=9, alignment=1)
    estilo_cel = ParagraphStyle("Cel", parent=estilos["Normal"],
                                fontSize=7, leading=8.5)

    elementos = [
        Paragraph(_escape(titulo), estilo_titulo),
        Paragraph(f"{len(dados):,} registros".replace(",", ".") +
                  f" | {len(dados.columns)} colunas", estilo_meta),
    ]

    # ---- Cálculo de largura das colunas ----
    largura_util = page[0] - 2 * MARGEM
    n_cols = max(len(dados.columns), 1)
    largura_base = max(largura_util / n_cols, 20 * mm)
    col_widths = [largura_base] * n_cols
    soma = sum(col_widths)
    if soma > largura_util:                       # muitas colunas: escala proporcional
        fator = largura_util / soma
        col_widths = [w * fator for w in col_widths]

    linhas = [[Paragraph(_escape(str(c)), estilo_cab) for c in dados.columns]]
    for _, row in dados.iterrows():
        linhas.append([
            Paragraph(_escape(_limpar(str(v))), estilo_cel) for v in row
        ])

    tabela = Table(linhas, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9c9c9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#eef3f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabela)

    doc.build(elementos)
