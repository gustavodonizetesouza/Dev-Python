# ============================================
# views/login_view.py
# Tela de login do sistema.
#
# MODO TEMPORÁRIO (desenvolvimento):
# A autenticação real ainda depende da tabela de usuários
# do ASP.NET Identity, que será construída depois.
# Por enquanto, o botão "Entrar" apenas confirma e abre
# a janela principal com um usuário padrão.
#
# Ajustes desta versão:
#   - Tamanho original restaurado (400x320)
#   - Janela centralizada no centro da tela
# ============================================
import customtkinter as ctk
from views.main_window import MainWindow


class LoginView(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Biblioteca Essencial - Login")
        self.geometry("400x320")
        self.resizable(False, False)

        # Centraliza a janela no centro da tela
        self._centralizar()

        # Título da tela
        ctk.CTkLabel(
            self, text="Biblioteca Essencial",
            font=("Arial", 22, "bold"),
        ).pack(pady=(25, 5))

        # Subtítulo
        ctk.CTkLabel(
            self, text="Acesse o sistema",
            text_color="gray",
        ).pack(pady=(0, 10))

        # Campo de usuário (e-mail)
        self.entry_user = ctk.CTkEntry(
            self, placeholder_text="E-mail", width=250)
        self.entry_user.pack(pady=8)
        self.entry_user.insert(0, "gustavodonizetesouza@hotmail.com")

        # Campo de senha (oculta os caracteres)
        self.entry_pass = ctk.CTkEntry(
            self, placeholder_text="Senha", width=250, show="*")
        self.entry_pass.pack(pady=8)
        self.entry_pass.insert(0, "Souza0159")

        # Botão de entrar (modo temporário: só confirma e entra)
        self.btn_login = ctk.CTkButton(
            self, text="Entrar", width=250, command=self._entrar)
        self.btn_login.pack(pady=14)

        # Aviso de modo de desenvolvimento
        ctk.CTkLabel(
            self, text="Modo desenvolvimento: acesso liberado",
            text_color="gray", font=("Arial", 10),
        ).pack(pady=(0, 10))

        # Permite entrar pressionando Enter
        self.entry_user.bind("<Return>", lambda e: self._entrar())
        self.entry_pass.bind("<Return>", lambda e: self._entrar())

    def _centralizar(self):
        """Centraliza a janela no centro da tela."""
        largura, altura = 400, 320
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def _entrar(self):
        """Modo temporário: confirma e abre a janela principal.

        Usa um usuário padrão para exibir as telas e os dados.
        Quando o login real for implementado, este método será
        substituído pela validação contra o ASP.NET Identity.
        """
        usuario_padrao = {
            "email": "gustavodonizetesouza@hotmail.com",
            "role": "Admin",
        }
        self.destroy()
        MainWindow(usuario_padrao).mainloop()
