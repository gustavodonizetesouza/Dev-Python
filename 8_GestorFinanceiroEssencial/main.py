"""Ponto de entrada do Gestor Financeiro — aplicação multiusuário.

Fluxo de vida da aplicação:
1. Conecta ao banco (config.json) e cria o schema (se necessário).
2. Abre a tela de login/cadastro (o primeiro cadastro vira admin).
3. Com a sessão iniciada, abre a janela principal com o repositório
   isolado pelo usuario_id.
4. 'Sair da conta' volta à tela de login mantendo o app aberto.

Fase 1: SQLite. Fase 2: SQL Server (aponte "banco": "sqlserver" no config).
"""
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from core.conexao import FabricaConexao
from core.schema import inicializar_banco
from core.sessao import Sessao
from dominio.repositorio import Repositorio, RepositorioUsuarios
from ui.janela_login import JanelaLogin
from ui.janela_principal import JanelaPrincipal
from ui.tema import aplicar_tema, ler_tema


class FluxoApp:
    """Orquestra o ciclo login → janela principal → Sair → login.

    Usa um único event loop do Qt: o login é um diálogo modal (exec) e a
    volta ao login após 'Sair' é agendada com QTimer.singleShot, evitando
    reinicializações do event loop.
    """

    def __init__(self, app, db, repo_usuarios, sessao):
        self.app = app
        self.db = db
        self.repo_usuarios = repo_usuarios
        self.sessao = sessao
        self.janela = None
        self.encerrado = False

    def iniciar(self):
        """Primeira abertura: login antes do event loop principal."""
        self._abrir_login(primeira_vez=True)

    def _abrir_login(self, primeira_vez=False):
        self.sessao.encerrar()
        login = JanelaLogin(self.repo_usuarios, self.sessao)
        resultado = login.exec()
        if resultado == QDialog.DialogCode.Accepted and self.sessao.logado:
            self._abrir_principal()
        elif primeira_vez:
            # Usuário fechou o login na abertura: não inicia o event loop.
            self.encerrado = True
        else:
            # Usuário fechou o login após 'Sair': encerra a aplicação.
            self.app.quit()

    def _abrir_principal(self):
        repo = Repositorio(self.db, self.sessao.usuario_id)
        self.janela = JanelaPrincipal(
            repo, self.repo_usuarios, self.sessao, self.db.descricao)
        self.janela.sair_solicitado.connect(self._sair)
        self.janela.show()

    def _sair(self):
        if self.janela:
            self.janela.deleteLater()
            self.janela = None
        QTimer.singleShot(0, lambda: self._abrir_login(primeira_vez=False))


def main():
    app = QApplication(sys.argv)
    aplicar_tema(app, ler_tema())

    try:
        db = FabricaConexao.criar()
        inicializar_banco(db)
    except Exception as e:
        QMessageBox.critical(
            None, "Erro de banco de dados",
            f"Não foi possível conectar/criar o banco de dados:\n\n{e}\n\n"
            "Verifique o config.json. Para SQL Server, instale o pacote pyodbc "
            "e crie o banco antes de trocar a chave \"banco\".")
        return 1

    repo_usuarios = RepositorioUsuarios(db)
    sessao = Sessao()
    fluxo = FluxoApp(app, db, repo_usuarios, sessao)
    fluxo.iniciar()
    if fluxo.encerrado:
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
