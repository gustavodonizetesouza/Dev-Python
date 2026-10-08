"""
Sistema de temas do aplicativo.
- Claro / Escuro / Sistema (segue o Windows)
- Persiste a escolha em um arquivo de configuração (settings.json)
"""
import json
import sys
from pathlib import Path

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "settings.json"

# ============ ESTILOS (QSS) ============

ESTILO_CLARO = """
/* ===== Tema Claro ===== */
QMainWindow, QWidget {
    background-color: #F5F6FA;
    color: #2C3E50;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #D5DBE3;
    border-radius: 6px;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #E4E8EE;
    color: #2C3E50;
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1F4E78;
    color: #FFFFFF;
    font-weight: bold;
}
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F0F3F8;
    gridline-color: #E1E6ED;
    border: 1px solid #D5DBE3;
    border-radius: 4px;
    selection-background-color: #1F4E78;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background: #1F4E78;
    color: #FFFFFF;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QPushButton {
    background: #1F4E78;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: bold;
}
QPushButton:hover { background: #2A6BA8; }
QPushButton:pressed { background: #16395A; }
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
    background: #FFFFFF;
    border: 1px solid #C9D2DE;
    border-radius: 4px;
    padding: 5px;
    color: #2C3E50;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 2px solid #1F4E78;
}
QComboBox::drop-down { border: none; width: 22px; }
QLabel { color: #2C3E50; }
QStatusBar { background: #E4E8EE; color: #2C3E50; }
QMessageBox { background: #FFFFFF; }
"""

ESTILO_ESCURO = """
/* ===== Tema Escuro ===== */
QMainWindow, QWidget {
    background-color: #1E2430;
    color: #E6E9EF;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #3A4454;
    border-radius: 6px;
    background: #262D3B;
}
QTabBar::tab {
    background: #2B3342;
    color: #C7CDD8;
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #3D6FA8;
    color: #FFFFFF;
    font-weight: bold;
}
QTableWidget {
    background: #262D3B;
    alternate-background-color: #2C3545;
    gridline-color: #3A4454;
    border: 1px solid #3A4454;
    border-radius: 4px;
    selection-background-color: #3D6FA8;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background: #3A4454;
    color: #E6E9EF;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QPushButton {
    background: #3D6FA8;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: bold;
}
QPushButton:hover { background: #4F86C4; }
QPushButton:pressed { background: #2C5480; }
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
    background: #2B3342;
    border: 1px solid #3A4454;
    border-radius: 4px;
    padding: 5px;
    color: #E6E9EF;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 2px solid #3D6FA8;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: #2B3342;
    color: #E6E9EF;
    selection-background-color: #3D6FA8;
}
QLabel { color: #E6E9EF; }
QStatusBar { background: #2B3342; color: #C7CDD8; }
QMessageBox { background: #262D3B; }
QDialog { background: #262D3B; }
"""


class ThemeManager:
    """Aplica e persiste o tema escolhido."""

    @staticmethod
    def _carregar_preferencia():
        """Lê a preferência salva. Padrão: 'sistema'."""
        try:
            if SETTINGS_PATH.exists():
                dados = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                return dados.get("tema", "sistema")
        except (json.JSONDecodeError, OSError):
            pass
        return "sistema"

    @staticmethod
    def _salvar_preferencia(tema):
        """Grava a preferência em settings.json."""
        try:
            dados = {}
            if SETTINGS_PATH.exists():
                dados = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            dados["tema"] = tema
            SETTINGS_PATH.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _sistema_escuro():
        """Detecta se o Windows está em modo escuro."""
        try:
            import winreg
            chave = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            valor, _ = winreg.QueryValueEx(chave, "AppsUseLightTheme")
            winreg.CloseKey(chave)
            return valor == 0
        except Exception:
            return False

    @staticmethod
    def tema_atual():
        """Retorna 'claro' ou 'escuro' considerando a preferência do sistema."""
        pref = ThemeManager._carregar_preferencia()
        if pref == "claro":
            return "claro"
        if pref == "escuro":
            return "escuro"
        # 'sistema' -> segue o Windows
        return "escuro" if ThemeManager._sistema_escuro() else "claro"

    @staticmethod
    def aplicar(app: QApplication, tema: str):
        """Aplica o tema escolhido ('claro', 'escuro' ou 'sistema')."""
        if tema == "sistema":
            tema = "escuro" if ThemeManager._sistema_escuro() else "claro"

        if tema == "escuro":
            app.setStyleSheet(ESTILO_ESCURO)
            paleta = QPalette()
            paleta.setColor(QPalette.Window, QColor("#1E2430"))
            paleta.setColor(QPalette.WindowText, QColor("#E6E9EF"))
            paleta.setColor(QPalette.Base, QColor("#262D3B"))
            paleta.setColor(QPalette.AlternateBase, QColor("#2C3545"))
            paleta.setColor(QPalette.Text, QColor("#E6E9EF"))
            paleta.setColor(QPalette.Button, QColor("#2B3342"))
            paleta.setColor(QPalette.ButtonText, QColor("#E6E9EF"))
            paleta.setColor(QPalette.Highlight, QColor("#3D6FA8"))
            paleta.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            app.setPalette(paleta)
        else:
            app.setStyleSheet(ESTILO_CLARO)
            paleta = QPalette()
            paleta.setColor(QPalette.Window, QColor("#F5F6FA"))
            paleta.setColor(QPalette.WindowText, QColor("#2C3E50"))
            paleta.setColor(QPalette.Base, QColor("#FFFFFF"))
            paleta.setColor(QPalette.AlternateBase, QColor("#F0F3F8"))
            paleta.setColor(QPalette.Text, QColor("#2C3E50"))
            paleta.setColor(QPalette.Button, QColor("#E4E8EE"))
            paleta.setColor(QPalette.ButtonText, QColor("#2C3E50"))
            paleta.setColor(QPalette.Highlight, QColor("#1F4E78"))
            paleta.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            app.setPalette(paleta)

        ThemeManager._salvar_preferencia(tema)
