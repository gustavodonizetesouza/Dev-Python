"""Ponto de entrada do Gerenciador Testes Essencial."""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from database.connection import Database
from ui.main_window import MainWindow
from utils.themes import ThemeManager


def main():
    # Inicializa o banco de CONFIGURAÇÃO (sempre existe e funciona)
    Database.init_config_db()

    # Cria o schema da conexão ativa. Se falhar, o init_db já cai para a local padrão.
    try:
        Database.init_db()
    except Exception as e:
        # Nunca trava a abertura: mostra aviso e segue com a conexão local padrão
        print(f"Aviso: não foi possível usar a conexão ativa. Usando local padrão. ({e})")

    app = QApplication(sys.argv)
    app.setApplicationName("Gerenciador Testes Essencial")

    ThemeManager.aplicar(app, ThemeManager.tema_atual())

    janela = MainWindow()
    janela.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()