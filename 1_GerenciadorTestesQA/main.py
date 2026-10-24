"""Ponto de entrada da aplicação — Gerenciador de Testes QA (Protheus).

Bootstrap: inicializa o banco de configuração (clientes, conexões, perfis,
usuários do sistema), aplica o tema salvo e abre a janela principal
(o login acontece dentro da MainWindow, antes de montar as telas).

IMPORTANTE: este arquivo é o ponto de entrada — usa APENAS imports
absolutos (imports relativos só funcionam dentro de um pacote).
"""
import sys

from PySide6.QtWidgets import QApplication

from database.connection import Database
from ui.main_window import MainWindow


def main():
    # Banco de configuração (clientes, conexões, perfis, usuarios_sistema)
    Database.init_config_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Gerenciador Testes Essencial")

    # Tema (se o ThemeManager tiver tema salvo, aplica; senão usa o padrão)
    try:
        from utils.themes import ThemeManager
        ThemeManager.aplicar(app, ThemeManager.tema_salvo()
                             if hasattr(ThemeManager, "tema_salvo")
                             else "sistema")
    except Exception:
        pass  # tema padrão do sistema em caso de falha

    janela = MainWindow()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()