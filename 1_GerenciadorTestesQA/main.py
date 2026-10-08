"""Ponto de entrada do Gerenciador Testes Essencial."""
import sys
from PySide6.QtWidgets import QApplication
from database.connection import Database
from ui.main_window import MainWindow
from utils.themes import ThemeManager


def main():
    # Inicializa o banco (cria tabelas se necessário)
    Database.init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Gerenciador Testes Essencial")

    # Aplica o tema salvo (claro / escuro / sistema)
    ThemeManager.aplicar(app, ThemeManager.tema_atual())

    janela = MainWindow()
    janela.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
