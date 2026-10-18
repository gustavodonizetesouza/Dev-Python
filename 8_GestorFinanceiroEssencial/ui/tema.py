"""Temas escuro/claro (QSS) + alternância em tempo de execução.

O config.json é lido/gravado sempre na raiz do projeto (core.util.CAMINHO_CONFIG),
independentemente do diretório de trabalho.
"""
import json

from core.util import CAMINHO_CONFIG

ESCURO, CLARO = "escuro", "claro"
TEMAS = (ESCURO, CLARO)

CORES_ESCURO = dict(fundo="#1e1f22", fundo2="#26282c", fundo3="#31343a",
                    texto="#e6e6e6", texto2="#9aa0a6", borda="#3c4045",
                    primaria="#4f8cff", verde="#43a047", vermelho="#e53935",
                    hover="#3a3e44", selecao="#2e4d80")
CORES_CLARO = dict(fundo="#f4f5f7", fundo2="#ffffff", fundo3="#e9ecef",
                   texto="#212529", texto2="#5f6368", borda="#d7dade",
                   primaria="#1a73e8", verde="#2e7d32", vermelho="#c62828",
                   hover="#e2e6ea", selecao="#c5d9f7")


def montar_qss(c: dict) -> str:
    return f"""
QWidget {{ background-color: {c['fundo']}; color: {c['texto']}; font-size: 13px; }}
QDialog {{ background-color: {c['fundo']}; }}
QLabel {{ background: transparent; }}
QLabel#tituloApp {{ font-size: 17px; font-weight: 700; }}
QLabel#tituloPagina {{ font-size: 19px; font-weight: 700; }}
QLabel#tituloCard {{ color: {c['texto2']}; font-size: 12px; font-weight: 600; }}
QLabel#kpiValor {{ font-size: 20px; font-weight: 700; }}
QLabel#aviso {{ color: {c['vermelho']}; }}

QFrame#card {{ background-color: {c['fundo2']}; border: 1px solid {c['borda']};
               border-radius: 10px; }}
QFrame#card QLabel {{ background: transparent; }}

QPushButton {{ background-color: {c['fundo3']}; color: {c['texto']};
               border: 1px solid {c['borda']}; border-radius: 6px; padding: 6px 14px; }}
QPushButton:hover {{ background-color: {c['hover']}; }}
QPushButton:disabled {{ color: {c['texto2']}; }}
QPushButton[variacao="primaria"] {{ background-color: {c['primaria']}; color: white;
                                   border: none; font-weight: 600; }}
QPushButton[variacao="primaria"]:hover {{ background-color: {c['hover']}; }}
QPushButton[variacao="sucesso"] {{ background-color: {c['verde']}; color: white; border: none; }}
QPushButton[variacao="perigo"] {{ background-color: {c['vermelho']}; color: white; border: none; }}
QPushButton#nav {{ background: transparent; border: none; border-radius: 8px;
                   text-align: left; padding: 9px 14px; }}
QPushButton#nav:hover {{ background-color: {c['hover']}; }}
QPushButton#nav:checked {{ background-color: {c['primaria']}; color: white; font-weight: 600; }}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c['fundo3']}; border: 1px solid {c['borda']};
    border-radius: 6px; padding: 5px 8px;
    selection-background-color: {c['selecao']}; selection-color: {c['texto']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background-color: {c['fundo2']};
    selection-background-color: {c['selecao']}; selection-color: {c['texto']}; }}

QTableWidget {{ background-color: {c['fundo2']}; alternate-background-color: {c['fundo']};
                gridline-color: {c['borda']}; border: 1px solid {c['borda']};
                border-radius: 8px; selection-background-color: {c['selecao']};
                selection-color: {c['texto']}; }}
QTableWidget::item {{ padding: 4px; }}
QHeaderView::section {{ background-color: {c['fundo3']}; color: {c['texto']};
                        border: none; border-bottom: 1px solid {c['borda']};
                        padding: 6px; font-weight: 600; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['borda']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c['borda']}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QCheckBox {{ spacing: 6px; }}
QMessageBox {{ background-color: {c['fundo2']}; }}
"""


def ler_tema() -> str:
    try:
        with open(CAMINHO_CONFIG, "r", encoding="utf-8") as arq:
            return json.load(arq).get("tema", ESCURO)
    except (OSError, ValueError):
        return ESCURO


def salvar_tema(nome: str) -> None:
    try:
        with open(CAMINHO_CONFIG, "r", encoding="utf-8") as arq:
            cfg = json.load(arq)
    except (OSError, ValueError):
        cfg = {}
    cfg["tema"] = nome
    try:
        with open(CAMINHO_CONFIG, "w", encoding="utf-8") as arq:
            json.dump(cfg, arq, indent=2, ensure_ascii=False)
    except OSError:
        pass


def aplicar_tema(app, nome=None) -> str:
    nome = nome or ler_tema()
    cores = CORES_ESCURO if nome == ESCURO else CORES_CLARO
    app.setStyleSheet(montar_qss(cores))
    return nome


def alternar_tema(nome_atual: str) -> str:
    return CLARO if nome_atual == ESCURO else ESCURO
