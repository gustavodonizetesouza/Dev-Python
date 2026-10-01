# ============================================
# views/crud_view.py
# Tela CRUD genérica.
# Recebe um repositório, os campos do formulário e as colunas
# da tabela, montando automaticamente a tela de listagem,
# cadastro, edição e exclusão de qualquer entidade.
#
# Ajustes desta versão:
#   - Grid moderno (tema clam, cabeçalho destacado, linhas altas)
#   - CORES ALTERNADAS nas linhas (branco/cinza claro)
#   - Coluna "codigo" estreita e centralizada por padrão
#   - Larguras customizáveis via parâmetro column_widths
# ============================================
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime


class CrudView(ctk.CTkFrame):
    def __init__(self, master, repository, title, fields, display_columns,
                 column_widths=None):
        super().__init__(master, fg_color="transparent")
        self.repository = repository
        self.title = title
        self.fields = fields                    # configuração dos campos do formulário
        self.display_columns = display_columns  # colunas exibidas na tabela
        # larguras customizadas (opcional)
        self.column_widths = column_widths or {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Título da tela
        ctk.CTkLabel(self, text=title, font=("Arial", 22, "bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        # ===== Barra de ferramentas (botões) =====
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

        # ===== Estilo moderno da tabela =====
        self.estilo = ttk.Style()
        if "clam" in self.estilo.theme_names():
            self.estilo.theme_use("clam")

        self.estilo.configure(
            "Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground="#1F2937",
            borderwidth=0,
            rowheight=32,
            font=("Segoe UI", 12),
        )
        self.estilo.configure(
            "Treeview.Heading",
            background="#E2E8F0",
            foreground="#0F172A",
            borderwidth=0,
            font=("Segoe UI", 12, "bold"),
        )
        self.estilo.map(
            "Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")],
        )

        # ===== Tabela de listagem =====
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, sticky="nsew",
                         padx=15, pady=(10, 15))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = [key for key, _ in display_columns]
        self.tree = ttk.Treeview(
            table_frame, columns=cols, show="headings", selectmode="browse")

        # Monta cabeçalhos e larguras das colunas
        for key, label in display_columns:
            self.tree.heading(key, text=label)
            # Largura: usa a customizada; senão, "codigo" fica estreito (70) e o resto 160
            largura = self.column_widths.get(key)
            if largura is None:
                largura = 70 if key == "codigo" else 160
            # "codigo" centralizado; demais colunas alinhadas à esquerda
            ancoragem = "center" if key == "codigo" else "w"
            self.tree.column(key, width=largura, minwidth=60,
                             anchor=ancoragem, stretch=True)

        # Cores alternadas nas linhas (efeito zebra)
        self.tree.tag_configure("linha_par", background="#F1F5F9")
        self.tree.tag_configure("linha_impar", background="#FFFFFF")

        # Barra de rolagem vertical
        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Duplo clique na linha abre a edição
        self.tree.bind("<Double-1>", lambda e: self._editar())

        # Carrega os dados ao abrir a tela
        self._carregar()

    # ---------- Carregar dados ----------
    def _carregar(self):
        """Recarrega a tabela com os dados do banco."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            for indice, row in enumerate(self.repository.list_all()):
                values = [self._format(row[i])
                          for i in range(len(self.display_columns))]
                tag = "linha_par" if indice % 2 == 0 else "linha_impar"
                self.tree.insert("", "end", values=values, tags=(tag,))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar dados:\n{e}")

    @staticmethod
    def _format(valor):
        """Formata valores para exibição (datas, nulos, etc.)."""
        if valor is None:
            return ""
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y")
        return str(valor)

    def _selected_codigo(self):
        """Retorna o código do registro selecionado na tabela."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um registro na tabela.")
            return None
        return self.tree.item(sel[0], "values")[0]

    # ---------- Ações: novo / editar / excluir ----------
    def _novo(self):
        self._abrir_formulario(None)

    def _editar(self):
        codigo = self._selected_codigo()
        if codigo is None:
            return
        try:
            row = self.repository.get_by_id(codigo)
            if not row:
                messagebox.showwarning("Aviso", "Registro não encontrado.")
                return
            self._abrir_formulario(row[0])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao buscar registro:\n{e}")

    def _excluir(self):
        codigo = self._selected_codigo()
        if codigo is None:
            return
        if not messagebox.askyesno("Confirmar", "Excluir este registro?"):
            return
        try:
            self.repository.delete(codigo)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir:\n{e}")

    # ---------- Formulário de cadastro/edição ----------
    def _abrir_formulario(self, codigo):
        """Abre a janela de formulário para novo ou edição."""
        janela = ctk.CTkToplevel(self)
        janela.title(f"{'Editar' if codigo else 'Novo'} - {self.title}")
        janela.geometry("420x520")
        janela.grab_set()

        entradas = {}
        valores_atuais = {}
        if codigo:
            row = self.repository.get_by_id(codigo)[0]
            for i, f in enumerate(self.fields):
                # pula o codigo (coluna 0)
                valores_atuais[f["name"]] = row[i + 1]

        container = ctk.CTkScrollableFrame(janela, width=380, height=440)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # Monta os campos do formulário conforme a configuração
        for f in self.fields:
            ctk.CTkLabel(container, text=f["label"]).pack(
                anchor="w", pady=(8, 2))
            tipo = f.get("type", "text")

            if tipo == "select":
                # Campo de seleção (combobox) - ex.: gênero, autor, editora
                opcoes = f.get("options_loader", lambda: [])()
                nomes = [o[1] for o in opcoes]
                combo = ctk.CTkOptionMenu(container, values=nomes)
                combo.pack(fill="x")
                atual = valores_atuais.get(f["name"])
                if atual is not None:
                    for oid, onome in opcoes:
                        if str(oid) == str(atual):
                            combo.set(onome)
                            break
                entradas[f["name"]] = (combo, opcoes)
            else:
                # Campo de texto
                entry = ctk.CTkEntry(container)
                entry.pack(fill="x")
                atual = valores_atuais.get(f["name"])
                if atual is not None:
                    entry.insert(0, str(atual))
                entradas[f["name"]] = entry

        def salvar():
            """Coleta os dados do formulário e salva no banco."""
            dados = {}
            for f in self.fields:
                nome = f["name"]
                tipo = f.get("type", "text")
                if tipo == "select":
                    combo, opcoes = entradas[nome]
                    selecionado = combo.get()
                    oid = next((o[0]
                               for o in opcoes if o[1] == selecionado), None)
                    dados[nome] = oid
                elif tipo == "int":
                    val = entradas[nome].get().strip()
                    dados[nome] = int(val) if val else None
                else:
                    val = entradas[nome].get().strip()
                    dados[nome] = val if val else None

            try:
                if codigo:
                    self.repository.update(codigo, dados)
                else:
                    self.repository.insert(dados)
                janela.destroy()
                self._carregar()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

        ctk.CTkButton(janela, text="💾 Salvar", command=salvar).pack(pady=10)
