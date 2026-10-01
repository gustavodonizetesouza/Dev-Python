# ============================================
# views/relatorios_view.py
# Tela de relatórios.
# Exibirá relatórios do acervo e da movimentação
# (livros por gênero, por situação, empréstimos, etc.).
# ============================================
import customtkinter as ctk


class RelatoriosView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Título da tela
        ctk.CTkLabel(
            self, text="📈 Relatórios",
            font=("Arial", 24, "bold")
        ).pack(pady=30)

        # Mensagem provisória (os relatórios serão adicionados depois)
        ctk.CTkLabel(
            self,
            text="Em breve: relatórios de acervo e movimentação.",
            text_color="gray",
        ).pack()
