# ============================================
# views/dashboard_view.py
# Dashboard com indicadores (KPIs) do acervo.
# Cards COMPACTOS, fixos (não esticam na tela),
# com canto arredondado, borda suave e ícone
# em badge circular colorido. Centralizados na tela.
#
# Linha 1: Editoras, Autores, Gêneros, Livros (acervo)
# Linha 2: Disponíveis, Lendo, Emprestados
# ============================================
import customtkinter as ctk
from database import Database


class DashboardView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Área central que centraliza o conteúdo na tela
        area = ctk.CTkFrame(self, fg_color="transparent")
        area.grid(row=0, column=0, sticky="nsew")

        conteudo = ctk.CTkFrame(area, fg_color="transparent")
        conteudo.place(relx=0.5, rely=0.45, anchor="center")

        # Título
        ctk.CTkLabel(conteudo, text="Dashboard", font=("Segoe UI", 26, "bold"),
                     text_color="#0F172A").pack()
        ctk.CTkLabel(conteudo, text="Visão geral do acervo", font=("Segoe UI", 13),
                     text_color="#64748B").pack(pady=(0, 15))

        # ===== Linha 1: totais de cadastro =====
        linha1 = ctk.CTkFrame(conteudo, fg_color="transparent")
        linha1.pack(pady=(0, 5))

        self.card_editoras = self._criar_card(
            linha1, "Editoras", "🏢", "#EFF6FF", "#2563EB")
        self.card_autores = self._criar_card(
            linha1, "Autores", "✍️", "#F5F3FF", "#7C3AED")
        self.card_generos = self._criar_card(
            linha1, "Gêneros", "🏷️", "#ECFEFF", "#0891B2")
        self.card_livros = self._criar_card(
            linha1, "Livros (Acervo)", "📚", "#ECFDF5", "#059669")

        # ===== Linha 2: situação dos livros =====
        linha2 = ctk.CTkFrame(conteudo, fg_color="transparent")
        linha2.pack()

        self.card_disponivel = self._criar_card(
            linha2, "Disponíveis", "✅", "#F0FDF4", "#16A34A")
        self.card_lendo = self._criar_card(
            linha2, "Lendo", "📖", "#FFFBEB", "#D97706")
        self.card_emprestado = self._criar_card(
            linha2, "Emprestados", "🔁", "#FEF2F2", "#DC2626")

        # Carrega as contagens do banco
        self._carregar()

    @staticmethod
    def _criar_card(pai, titulo, icone, cor_fundo, cor_destaque):
        """Cria um card compacto, arredondado e moderno."""
        card = ctk.CTkFrame(
            pai, width=190, height=150, corner_radius=18,
            fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0",
        )
        card.pack_propagate(False)   # trava o tamanho (não estica)
        card.pack(side="left", padx=10)

        # Badge circular com o ícone
        badge = ctk.CTkFrame(card, width=46, height=46,
                             corner_radius=23, fg_color=cor_fundo)
        badge.pack_propagate(False)
        badge.pack(pady=(16, 2))
        ctk.CTkLabel(badge, text=icone, font=(
            "Segoe UI Emoji", 20)).pack(expand=True)

        # Valor (número grande)
        valor = ctk.CTkLabel(card, text="—", font=("Segoe UI", 28, "bold"),
                             text_color="#0F172A")
        valor.pack(pady=(2, 0))

        # Rótulo do card
        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 12),
                     text_color="#64748B").pack(pady=(0, 12))

        card._valor = valor
        return card

    @staticmethod
    def _contar(sql):
        """Executa uma consulta de contagem e retorna o número (ou None em erro)."""
        try:
            rows = Database.query(sql)
            return rows[0][0] if rows else 0
        except Exception:
            return None

    @staticmethod
    def _atualizar_card(card, sql):
        """Atualiza o valor de um card com o resultado da consulta."""
        valor = DashboardView._contar(sql)
        card._valor.configure(text="—" if valor is None else str(valor))

    def _carregar(self):
        """Busca as contagens reais do banco e atualiza os cards."""
        # Totais de cadastro
        self._atualizar_card(self.card_editoras,
                             "SELECT COUNT(*) FROM Editoras WHERE ISNULL(deletado,'')=''")
        self._atualizar_card(self.card_autores,
                             "SELECT COUNT(*) FROM Autores WHERE ISNULL(deletado,'')=''")
        self._atualizar_card(self.card_generos,
                             "SELECT COUNT(*) FROM Generos WHERE ISNULL(deletado,'')=''")
        self._atualizar_card(self.card_livros,
                             "SELECT COUNT(*) FROM Biblioteca WHERE ISNULL(deletado,'')=''")

        # Situação dos livros (int: 1=Não Lido, 2=Em Leitura, 3=Concluído)
        self._atualizar_card(self.card_disponivel,
                             "SELECT COUNT(*) FROM Biblioteca "
                             "WHERE situacao = 1 AND ISNULL(deletado,'')=''")
        self._atualizar_card(self.card_lendo,
                             "SELECT COUNT(*) FROM Biblioteca "
                             "WHERE situacao = 2 AND ISNULL(deletado,'')=''")
        self._atualizar_card(self.card_emprestado,
                             "SELECT COUNT(*) FROM Biblioteca "
                             "WHERE situacao = 3 AND ISNULL(deletado,'')=''")
