# ============================================
# views/login_view.py
# Tela de login do sistema.
# Valida usuário e senha contra o ASP.NET Identity e,
# se correto, abre a janela principal.
# Erros de conexão são exibidos em janela detalhada
# (views/error_dialog.py) para diagnóstico completo.
# ============================================
import customtkinter as ctk
from repositories.auth_repository import AuthRepository
from views.main_window import MainWindow
from views.error_dialog import show_error


class LoginView(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Biblioteca Essencial - Login")
        self.geometry("400x360")
        self.resizable(False, False)

        # Título da tela
        ctk.CTkLabel(
            self, text="Biblioteca Essencial",
            font=("Arial", 22, "bold"),
        ).pack(pady=(25, 5))

        # Subtítulo
        ctk.CTkLabel(
            self, text="Acesse com o e-mail e senha do sistema web",
            text_color="gray",
        ).pack(pady=(0, 10))

        # Campo de usuário (e-mail)
        self.entry_user = ctk.CTkEntry(
            self, placeholder_text="E-mail", width=250)
        self.entry_user.pack(pady=8)

        # Campo de senha (oculta os caracteres)
        self.entry_pass = ctk.CTkEntry(
            self, placeholder_text="Senha", width=250, show="*")
        self.entry_pass.pack(pady=8)

        # Botão de entrar
        self.btn_login = ctk.CTkButton(
            self, text="Entrar", width=250, command=self._login)
        self.btn_login.pack(pady=14)

        # Rótulo para mensagens curtas (ex.: credenciais inválidas)
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_status.pack()

        # Permite logar pressionando Enter
        self.entry_user.bind("<Return>", lambda e: self._login())
        self.entry_pass.bind("<Return>", lambda e: self._login())

    def _login(self):
        """Executa a validação do login."""
        email = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()

        # Valida se os campos não estão vazios
        if not email or not pwd:
            self.lbl_status.configure(text="Preencha e-mail e senha.")
            return

        # Desabilita o botão durante a tentativa de conexão
        self.btn_login.configure(state="disabled", text="Conectando...")
        self.lbl_status.configure(text="")

        try:
            usuario = AuthRepository.authenticate(email, pwd)
        except Exception as e:
            # Exibe o erro COMPLETO na janela de diagnóstico
            show_error(self, "Erro de conexão com o banco de dados", e)
            self.btn_login.configure(state="normal", text="Entrar")
            return

        if usuario:
            # Login OK: fecha o login e abre a janela principal
            self.destroy()
            MainWindow(usuario).mainloop()
        else:
            self.lbl_status.configure(text="E-mail ou senha inválidos.")
            self.btn_login.configure(state="normal", text="Entrar")
