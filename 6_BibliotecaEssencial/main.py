# ============================================
# main.py
# Ponto de entrada do aplicativo.
# Inicializa o customTkinter e abre a tela de login.
# ============================================
import customtkinter as ctk
from views.login_view import LoginView


def main():
    # Define o tema visual do app (claro/escuro) e a cor padrão
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # Abre a janela de login (primeira tela do sistema)
    LoginView().mainloop()


# Garante que o app só roda quando executado diretamente
if __name__ == "__main__":
    main()
