# ============================================
# views/dashboard_view.py
# Tela inicial (dashboard).
# Exibirá os principais indicadores do acervo
# (total de livros, por gênero, por situação, etc.).
# ============================================
import customtkinter as ctk


class DashboardView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Título da tela
        ctk.CTkLabel(
            self, text="📊 Dashboard",
            font=("Arial", 24, "bold")
        ).pack(pady=30)

        # Mensagem provisória (os KPIs serão adicionados depois)
        ctk.CTkLabel(
            self,
            text="Aqui vão os KPIs do acervo (total de livros, empréstimos ativos, etc.)",
            text_color="gray",
        ).pack()
