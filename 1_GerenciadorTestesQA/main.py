"""Ponto de entrada da aplicação — Gerenciador de Testes QA (Protheus).

Este arquivo é o ponto de entrada: usa APENAS imports ABSOLUTOS.
Imports relativos ("from .x import y") só funcionam dentro de um pacote
e quebram quando o arquivo é executado com "python main.py".
"""
import sys
from pathlib import Path

# Garante que a RAIZ do projeto esteja no sys.path antes dos imports.
_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from PySide6.QtWidgets import QApplication  # noqa: E402

from database.connection import Database  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def main():
    # 1) Banco de CONFIGURAÇÃO (clientes, conexões, perfis, usuarios_sistema)
    #    Precisa acontecer antes da MainWindow (que já faz login).
    Database.init_config_db()

    # 2) QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Gerenciador Testes Essencial")
    app.setOrganizationName("QA")

    # 3) Tema (se o ThemeManager tiver tema salvo, aplica; senão sistema)
    try:
        from utils.themes import ThemeManager
        tema = (ThemeManager.tema_salvo()
                if hasattr(ThemeManager, "tema_salvo") else "sistema")
        ThemeManager.aplicar(app, tema)
    except Exception:
        pass  # falha de tema não impede o app de abrir

    # 4) Janela principal (login acontece dentro dela)
    janela = MainWindow()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
