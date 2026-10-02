# ============================================
# views/autor_view.py
# Tela CRUD de Autores.
# Replica o modelo da view ASP.NET de Autores:
#   - Formulário com 4 campos LADO A LADO em uma linha:
#     Código | Nome do Autor (maior) | Data Cadastro | Data Alteração
#     (proporção igual aos col-md-2 / col-md-6 / col-md-2 / col-md-2)
#   - Nome do Autor em CAIXA ALTA ao digitar
#   - Data Cadastro e Data Alteração controladas pelo banco (GETDATE())
#   - Formulário centralizado e preso ao sistema (modal)
# ============================================
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

from repositories.autor_repository import AutorRepository


class AutorView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Cadastro de Autores",
                     font=("Arial", 22, "bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=15)
        ctk.CTkButton(toolbar, text="➕ Novo", width=90,
                      command=self._novo).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✏️ Editar", width=90,
                      command=self._editar).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑️ Excluir", width=90,
                      command=self._excluir).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔄 Atualizar", width=100,
                      command=self._carregar).pack(side="left", padx=5)

        self._montar_tabela()
        self._carregar()

    # ---------- Tabela de listagem ----------
    def _montar_tabela(self):
        self.estilo = ttk.Style()
        if "clam" in self.estilo.theme_names():
            self.estilo.theme_use("clam")
        self.estilo.configure(
            "Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
            foreground="#1F2937", borderwidth=0, rowheight=32, font=("Segoe UI", 12))
        self.estilo.configure(
            "Treeview.Heading", background="#E2E8F0", foreground="#0F172A",
            borderwidth=0, font=("Segoe UI", 12, "bold"))
        self.estilo.map("Treeview",
                        background=[("selected", "#2563EB")],
                        foreground=[("selected", "#FFFFFF")])

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, sticky="nsew",
                         padx=15, pady=(10, 15))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ["codigo", "nome_autor", "data_cadastro"]
        self.tree = ttk.Treeview(
            table_frame, columns=cols, show="headings", selectmode="browse")

        cabecalhos = {
            "codigo": "Código", "nome_autor": "Autor", "data_cadastro": "Cadastro",
        }
        larguras = {
            "codigo": 60, "nome_autor": 420, "data_cadastro": 130,
        }
        for c in cols:
            self.tree.heading(c, text=cabecalhos[c])
            self.tree.column(c, width=larguras[c], minwidth=50,
                             anchor="center" if c == "codigo" else "w")

        self.tree.tag_configure("linha_par", background="#F1F5F9")
        self.tree.tag_configure("linha_impar", background="#FFFFFF")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._editar())

    # ---------- Carregar dados ----------
    def _carregar(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            for indice, row in enumerate(AutorRepository.list_all()):
                values = [row[0], row[1], self._fmt_data(row[2])]
                tag = "linha_par" if indice % 2 == 0 else "linha_impar"
                self.tree.insert("", "end", values=values, tags=(tag,))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar dados:\n{e}")

    def _selected_codigo(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um registro na tabela.")
            return None
        return self.tree.item(sel[0], "values")[0]

    # ---------- Ações ----------
    def _novo(self):
        self._abrir_formulario(None)

    def _editar(self):
        codigo = self._selected_codigo()
        if codigo is None:
            return
        try:
            row = AutorRepository.get_by_id(codigo)
            if not row:
                messagebox.showwarning("Aviso", "Registro não encontrado.")
                return
            self._abrir_formulario(codigo)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao buscar registro:\n{e}")

    def _excluir(self):
        codigo = self._selected_codigo()
        if codigo is None:
            return
        if not messagebox.askyesno("Confirmar", "Excluir este autor?"):
            return
        try:
            AutorRepository.delete(codigo)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir:\n{e}")

    # ---------- Utilitários ----------
    @staticmethod
    def _linha_dict(row):
        """Converte um pyodbc.Row em dict usando o nome real das colunas."""
        return {desc[0]: row[i] for i, desc in enumerate(row.cursor_description)}

    @staticmethod
    def _fmt_data(valor):
        """Formata data do banco para dd/mm/aaaa."""
        if not valor:
            return ""
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y")
        return str(valor)

    @staticmethod
    def _maiusculas_ao_digitar(evento):
        entry = evento.widget
        try:
            pos = entry.index("insert")
        except Exception:
            pos = len(entry.get())
        texto = entry.get()
        if texto != texto.upper():
            entry.delete(0, "end")
            entry.insert(0, texto.upper())
            try:
                entry.icursor(min(pos, len(entry.get())))
            except Exception:
                pass

    # ---------- Formulário (replica o modelo ASP.NET) ----------
    def _abrir_formulario(self, codigo):
        largura, altura = 640, 300

        janela = ctk.CTkToplevel(self)
        janela.title(f"{'Editar' if codigo else 'Novo'} - Autor")

        x = (janela.winfo_screenwidth() - largura) // 2
        y = (janela.winfo_screenheight() - altura) // 2
        janela.geometry(f"{largura}x{altura}+{x}+{y}")
        janela.resizable(False, False)

        # Presa ao sistema (modal)
        janela.transient(self)
        janela.lift()
        janela.focus_force()
        janela.grab_set()
        janela.after(50, janela.focus_force)

        # Dados atuais (edição) — acesso POR NOME da coluna
        atual = {}
        if codigo:
            row = AutorRepository.get_by_id(codigo)[0]
            atual = self._linha_dict(row)

        container = ctk.CTkFrame(janela, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Grid de 6 unidades (proporção igual ao Bootstrap col-md):
        # Código(1) | Nome Autor(3) | Data Cadastro(1) | Data Alteração(1)
        #  =>  replica os col-md-2 / col-md-6 / col-md-2 / col-md-2
        container.grid_columnconfigure(
            (0, 1, 2, 3, 4, 5), weight=1, uniform="campos")

        entradas = {}

        def bloco(label, nome, coluna, colspan, tipo="text", desabilitado=False):
            """Cria bloco label (em cima) + campo (embaixo), lado a lado no grid."""
            frame = ctk.CTkFrame(container, fg_color="transparent")
            frame.grid(row=0, column=coluna, columnspan=colspan,
                       sticky="nsew", padx=(0, 8), pady=(4, 4))

            ctk.CTkLabel(frame, text=label, anchor="w",
                         font=("Segoe UI", 12)).pack(fill="x")

            entry = ctk.CTkEntry(frame)
            entry.pack(fill="x", pady=(4, 0))

            if desabilitado:
                entry.configure(state="disabled")

            if nome in atual and atual[nome] is not None:
                if tipo == "date":
                    entry.insert(0, self._fmt_data(atual[nome]))
                else:
                    entry.insert(0, str(atual[nome]).upper())

            if tipo == "text" and not desabilitado:
                entry.bind("<KeyRelease>", self._maiusculas_ao_digitar)

            entradas[nome] = entry

        # Linha única: Código | Nome do Autor (maior) | Data Cadastro | Data Alteração
        bloco("Código", "codigo", 0, 1, "text", desabilitado=not codigo)
        bloco("Nome do Autor", "nome_autor", 1, 3, "text")
        bloco("Data Cadastro", "data_cadastro",
              4, 1, "date", desabilitado=True)
        bloco("Data Alteração", "data_alteracao",
              5, 1, "date", desabilitado=True)

        # Data Cadastro: mostra hoje no novo cadastro (o banco grava GETDATE())
        if not codigo:
            entradas["data_cadastro"].configure(state="normal")
            entradas["data_cadastro"].insert(
                0, datetime.now().strftime("%d/%m/%Y"))
            entradas["data_cadastro"].configure(state="disabled")

        def salvar():
            """Coleta os dados e salva no banco."""
            nome = entradas["nome_autor"].get().strip()
            if not nome:
                messagebox.showerror("Erro", "Informe o nome do autor.")
                return

            dados = {"nome_autor": nome.upper()}

            try:
                if codigo:
                    AutorRepository.update(codigo, dados)
                else:
                    AutorRepository.insert(dados)
                janela.destroy()
                self._carregar()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

        rodape = ctk.CTkFrame(janela, fg_color="transparent")
        rodape.pack(pady=(0, 15))

        ctk.CTkButton(rodape, text="💾 Salvar Cadastro",
                      command=salvar).pack(side="left", padx=5)
        ctk.CTkButton(rodape, text="❌ Cancelar Cadastro",
                      command=janela.destroy).pack(side="left", padx=5)
