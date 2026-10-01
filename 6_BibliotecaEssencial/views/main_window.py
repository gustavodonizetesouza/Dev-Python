# ============================================
# views/main_window.py
# Janela principal do sistema.
# Contém a barra lateral de navegação e a área de conteúdo,
# onde cada tela (dashboard, CRUDs, relatórios) é exibida.
# ============================================
import customtkinter as ctk
from views.dashboard_view import DashboardView
from views.editora_view import EditoraView
from views.autor_view import AutorView
from views.genero_view import GeneroView
from views.biblioteca_view import BibliotecaView
from views.relatorios_view import RelatoriosView


class MainWindow(ctk.CTk):
    def __init__(self, usuario: dict):
        super().__init__()
        self.title("Biblioteca Essencial")
        self.geometry("1100x700")
        self.usuario = usuario

        # Configura o layout: coluna 1 (conteúdo) se expande
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ===== Barra lateral (menu de navegação) =====
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Logo do sistema
        ctk.CTkLabel(
            self.sidebar, text="Biblioteca\nEssencial",
            font=("Arial", 18, "bold")
        ).pack(pady=20)

        # Botões do menu (cada um abre uma tela)
        self._add_nav_btn("📊 Dashboard", lambda: self._show(DashboardView))
        self._add_nav_btn("🏢 Editoras", lambda: self._show(EditoraView))
        self._add_nav_btn("✍️ Autores", lambda: self._show(AutorView))
        self._add_nav_btn("🏷️ Gêneros", lambda: self._show(GeneroView))
        self._add_nav_btn("📚 Biblioteca", lambda: self._show(BibliotecaView))
        self._add_nav_btn("📈 Relatórios", lambda: self._show(RelatoriosView))

        # E-mail e perfil do usuário logado, no rodapé do menu
        email = usuario.get("email", "")
        role = usuario.get("role", "")
        ctk.CTkLabel(
            self.sidebar, text=f"👤 {email}\n{role}",
            text_color="gray", justify="left"
        ).pack(side="bottom", pady=10, padx=10)

        # ===== Área de conteúdo (onde as telas aparecem) =====
        self.content = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Abre o dashboard ao iniciar
        self._show(DashboardView)

    def _add_nav_btn(self, text, command):
        """Cria um botão de navegação na barra lateral."""
        ctk.CTkButton(
            self.sidebar, text=text, command=command,
            anchor="w", fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray25"),
        ).pack(fill="x", pady=2, padx=10)

    def _clear_content(self):
        """Remove todos os widgets da área de conteúdo."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def _show(self, view_class):
        """Exibe uma tela na área de conteúdo."""
        self._clear_content()
        view_class(self.content).grid(row=0, column=0, sticky="nsew")
