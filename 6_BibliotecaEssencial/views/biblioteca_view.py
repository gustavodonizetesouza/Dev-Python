# ============================================
# views/biblioteca_view.py
# Tela do Acervo (Cadastro de Livros).
# Replica o modelo da view ASP.NET de Biblioteca:
#   - Coluna da IMAGEM à esquerda
#   - Formulário com campos LADO A LADO em grid de 3 colunas
#     (igual ao _FormFields.cshtml: label em cima, campo embaixo)
#   - Selects de Autor, Editora, Gênero e Situação
#   - Campos de texto em CAIXA ALTA
#   - Datas no formato dd/mm/aaaa
#   - Formulário centralizado e preso ao sistema (modal)
# ============================================
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

from repositories.biblioteca_repository import BibliotecaRepository
from repositories.autor_repository import AutorRepository
from repositories.editora_repository import EditoraRepository
from repositories.genero_repository import GeneroRepository


class BibliotecaView(ctk.CTkFrame):
    # Situação (mesmo do ASP.NET: 1/2/3)
    SITUACOES = {"1": "Não Lido", "2": "Em Leitura", "3": "Concluído"}

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Acervo - Cadastro de Livros",
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

        cols = ["codigo", "nome_livro", "autor",
                "editora", "genero", "situacao"]
        self.tree = ttk.Treeview(
            table_frame, columns=cols, show="headings", selectmode="browse")

        cabecalhos = {
            "codigo": "Código", "nome_livro": "Título", "autor": "Autor",
            "editora": "Editora", "genero": "Gênero", "situacao": "Situação",
        }
        larguras = {
            "codigo": 60, "nome_livro": 260, "autor": 180,
            "editora": 180, "genero": 140, "situacao": 110,
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
            for indice, row in enumerate(BibliotecaRepository.list_all()):
                # row: codigo, nome_livro, nome_autor, editora, genero, situacao
                situacao = self.SITUACOES.get(str(row[5]), "")
                values = [row[0], row[1], row[2], row[3], row[4], situacao]
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
            row = BibliotecaRepository.get_by_id(codigo)
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
        if not messagebox.askyesno("Confirmar", "Excluir este livro?"):
            return
        try:
            BibliotecaRepository.delete(codigo)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir:\n{e}")

    # ---------- Opções dos selects ----------
    @staticmethod
    def _opcoes_autor():
        return [(r[0], r[1]) for r in AutorRepository.list_all()]

    @staticmethod
    def _opcoes_editora():
        return [(r[0], r[1]) for r in EditoraRepository.list_all()]

    @staticmethod
    def _opcoes_genero():
        return [(r[0], r[1]) for r in GeneroRepository.list_all()]

    # ---------- Utilitários ----------
    @staticmethod
    def _linha_dict(row):
        """Converte um pyodbc.Row em dict usando o nome real das colunas."""
        return {desc[0]: row[i] for i, desc in enumerate(row.cursor_description)}

    @staticmethod
    def _parse_data(valor):
        """Converte dd/mm/aaaa (ou aaaa-mm-dd) para 'YYYY-MM-DD'. Vazio -> None."""
        valor = (valor or "").strip()
        if not valor:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(valor, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def _fmt_data(valor):
        """Formata data do banco para dd/mm/aaaa no campo."""
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

    # ---------- Formulário (replica o layout ASP.NET: campos lado a lado) ----------
    def _abrir_formulario(self, codigo):
        largura, altura = 780, 620

        janela = ctk.CTkToplevel(self)
        janela.title(f"{'Editar' if codigo else 'Novo'} - Livro")

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

        # Dados atuais (edição) — acesso POR NOME da coluna (robusto)
        atual = {}
        if codigo:
            row = BibliotecaRepository.get_by_id(codigo)[0]
            atual = self._linha_dict(row)

        container = ctk.CTkScrollableFrame(janela, width=740, height=520)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # ---- Coluna da IMAGEM (placeholder, como no ASP.NET) ----
        col_img = ctk.CTkFrame(container, width=170)
        col_img.pack(side="left", fill="y", padx=(0, 18))
        ctk.CTkLabel(col_img, text="Imagem", font=(
            "Segoe UI", 12, "bold")).pack(pady=(10, 5))
        img_box = ctk.CTkFrame(
            col_img, width=150, height=200, corner_radius=8, fg_color="#E2E8F0")
        img_box.pack_propagate(False)
        img_box.pack()
        ctk.CTkLabel(img_box, text="📚\n(sem foto)",
                     text_color="#64748B").pack(expand=True)

        # ---- Coluna dos DADOS (grid de 3 colunas, campos lado a lado) ----
        col_dados = ctk.CTkFrame(container, fg_color="transparent")
        col_dados.pack(side="left", fill="both", expand=True)
        # 3 colunas de largura igual, como as col-md do Bootstrap
        col_dados.grid_columnconfigure((0, 1, 2), weight=1, uniform="campos")

        entradas = {}

        def montar_campo(pai, label, nome, tipo, linha, coluna, colspan=1):
            """Cria um bloco label (em cima) + widget (embaixo), posicionado no grid.

            Replica o padrão do ASP.NET: form-label acima do form-control,
            com vários campos na mesma linha (lado a lado).
            """
            bloco = ctk.CTkFrame(pai, fg_color="transparent")
            bloco.grid(row=linha, column=coluna, columnspan=colspan,
                       sticky="nsew", padx=(0, 8), pady=(4, 4))

            ctk.CTkLabel(bloco, text=label, anchor="w",
                         font=("Segoe UI", 12)).pack(fill="x")

            if tipo == "select":
                if nome == "autor":
                    opcoes = self._opcoes_autor()
                elif nome == "editora":
                    opcoes = self._opcoes_editora()
                elif nome == "genero":
                    opcoes = self._opcoes_genero()
                else:  # situacao
                    opcoes = [(k, v) for k, v in self.SITUACOES.items()]
                nomes = [o[1] for o in opcoes]
                combo = ctk.CTkOptionMenu(bloco, values=nomes)
                combo.pack(fill="x", pady=(4, 0))
                atual_val = atual.get(nome)
                if atual_val is not None:
                    for oid, onome in opcoes:
                        if str(oid) == str(atual_val):
                            combo.set(onome)
                            break
                entradas[nome] = ("select", combo, opcoes)
            else:
                entry = ctk.CTkEntry(bloco)
                entry.pack(fill="x", pady=(4, 0))
                atual_val = atual.get(nome)
                if atual_val is not None:
                    if tipo == "date":
                        entry.insert(0, self._fmt_data(atual_val))
                    else:
                        entry.insert(0, str(atual_val).upper())
                if tipo == "text":
                    entry.bind("<KeyRelease>", self._maiusculas_ao_digitar)
                entradas[nome] = ("entry", entry)

        # ===== Campos dispostos LADO A LADO (linha, coluna, colspan) =====
        # Linha 0: Código | Título (ocupa 2 colunas)
        if codigo:
            bloco = ctk.CTkFrame(col_dados, fg_color="transparent")
            bloco.grid(row=0, column=0, sticky="nsew",
                       padx=(0, 8), pady=(4, 4))
            ctk.CTkLabel(bloco, text="Código", anchor="w",
                         font=("Segoe UI", 12)).pack(fill="x")
            entry_cod = ctk.CTkEntry(bloco)
            entry_cod.insert(0, str(atual.get("codigo", "")))
            entry_cod.configure(state="disabled")
            entry_cod.pack(fill="x", pady=(4, 0))
            # Não entra em `entradas` (não é editável)

        montar_campo(col_dados, "Título do Livro",
                     "nome_livro", "text", 0, 1, 2)

        # Linha 1: Subtítulo (2 col) | Código de Barras
        montar_campo(col_dados, "Subtítulo", "sub_titulo", "text", 1, 0, 2)
        montar_campo(col_dados, "Código de Barras",
                     "codigo_barras", "text", 1, 2, 1)

        # Linha 2: ISBN | Páginas | Edição
        montar_campo(col_dados, "ISBN", "codigo_isbn", "text", 2, 0, 1)
        montar_campo(col_dados, "Páginas",
                     "quantidade_paginas", "int", 2, 1, 1)
        montar_campo(col_dados, "Edição", "edicao", "text", 2, 2, 1)

        # Linha 3: Autor | Editora | Gênero
        montar_campo(col_dados, "Autor", "autor", "select", 3, 0, 1)
        montar_campo(col_dados, "Editora", "editora", "select", 3, 1, 1)
        montar_campo(col_dados, "Gênero", "genero", "select", 3, 2, 1)

        # Linha 4: Data Compra | Início Leitura | Fim Leitura
        montar_campo(col_dados, "Data Compra", "data_compra", "date", 4, 0, 1)
        montar_campo(col_dados, "Início Leitura",
                     "data_inicio_leitura", "date", 4, 1, 1)
        montar_campo(col_dados, "Fim Leitura",
                     "data_fim_leitura", "date", 4, 2, 1)

        # Linha 5: Situação
        montar_campo(col_dados, "Situação", "situacao", "select", 5, 0, 1)

        def salvar():
            dados = {}

            # Campos de texto
            for nome in ("nome_livro", "sub_titulo", "codigo_barras",
                         "codigo_isbn", "edicao"):
                val = entradas[nome][1].get().strip()
                dados[nome] = val.upper() if val else None

            # Páginas (int)
            val = entradas["quantidade_paginas"][1].get().strip()
            dados["quantidade_paginas"] = int(val) if val else None

            # Selects
            for nome in ("autor", "editora", "genero", "situacao"):
                _, combo, opcoes = entradas[nome]
                selecionado = combo.get()
                oid = next((o[0] for o in opcoes if o[1] == selecionado), None)
                dados[nome] = oid

            # Datas (dd/mm/aaaa)
            for nome in ("data_compra", "data_inicio_leitura", "data_fim_leitura"):
                val = entradas[nome][1].get().strip()
                if val:
                    parsed = self._parse_data(val)
                    if parsed is None:
                        messagebox.showerror(
                            "Erro",
                            f"Data inválida em '{nome}'. Use o formato dd/mm/aaaa.")
                        return
                    dados[nome] = parsed
                else:
                    dados[nome] = None

            try:
                if codigo:
                    BibliotecaRepository.update(codigo, dados)
                else:
                    BibliotecaRepository.insert(dados)
                janela.destroy()
                self._carregar()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

        ctk.CTkButton(janela, text="💾 Salvar", command=salvar).pack(pady=10)
