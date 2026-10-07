# ============================================================
# app.py - Protheus Reports (Biblioteca de Queries)
#   - Biblioteca de queries por PASTAS (árvore expansível)
#   - Botões de biblioteca NA PARTE DE BAIXO do painel
#   - Filtros dinâmicos (data e texto) com conversão Protheus
#   - Execução em thread + botão PARAR (cancela no servidor)
#   - Botão LIMPAR (zera o resultado para nova execução)
#   - Tela de configuração com validação + normalização do servidor
#   - Log automático de erros em erros.log
#   - Botão COPIAR ERRO (envia o erro para a área de transferência)
#   - Exportação XLSX e PDF (A4 paisagem)
#   - Janela abre maximizada (agendada pós-inicialização)
#   - Indicador de conclusão + contagem de linhas
#   - Atalhos: Ctrl+Enter executa | Ctrl+S salva
# ============================================================
import json
import os
import queue
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk

import config
import db
import pdf_export as pdf

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ARQUIVO_QUERIES = "queries.json"
ARQUIVO_ERROS = "erros.log"


def carregar_queries():
    """
    Carrega a biblioteca no formato:
      {"pastas": [{"nome": str, "queries": [...]}], "queries": [...]}
    Se o arquivo estiver no formato antigo (lista simples), converte sozinho.
    """
    if not os.path.exists(ARQUIVO_QUERIES):
        return {"pastas": [], "queries": []}
    try:
        with open(ARQUIVO_QUERIES, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {"pastas": [], "queries": []}

    # Formato novo (já com pastas)
    if "pastas" in dados and isinstance(dados.get("pastas"), list):
        estrutura = {
            "pastas": [p for p in dados["pastas"] if isinstance(p, dict)],
            "queries": dados.get("queries", [])
            if isinstance(dados.get("queries"), list) else [],
        }
        for pasta in estrutura["pastas"]:
            pasta.setdefault("nome", "Sem nome")
            pasta.setdefault("queries", [])
        return estrutura

    # Migração do formato antigo: {"queries": [ {...} ]} -> tudo na raiz
    queries_antigas = dados.get("queries", []) if isinstance(dados.get("queries"), list) else []
    raiz = []
    for q in queries_antigas:
        if isinstance(q, dict):
            q = dict(q)
            q.pop("pasta", None)
            raiz.append(q)
    return {"pastas": [], "queries": raiz}


def salvar_queries(estrutura):
    with open(ARQUIVO_QUERIES, "w", encoding="utf-8") as f:
        json.dump(estrutura, f, ensure_ascii=False, indent=2)


def registrar_erro(origem: str, mensagem: str):
    """Grava o erro em erros.log com data/hora (para diagnóstico)."""
    try:
        linha = f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {origem}: {mensagem}\n"
        with open(ARQUIVO_ERROS, "a", encoding="utf-8") as f:
            f.write(linha)
    except Exception:
        pass  # nunca deixa o log quebrar o app


class AppProtheus(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Protheus Reports - Biblioteca de Queries")
        self.geometry("1300x760")

        self.estrutura = carregar_queries()     # {"pastas": [...], "queries": [...]}
        self.local_atual = None                 # (pasta_idx, query_idx) da query aberta
        self.query_salva_atual = None           # dict da query aberta/salva
        self.pasta_nova_destino = None          # pasta destino ao criar query nova
        self.df_atual = None
        self.fila = queue.Queue()
        self.campos_param = {}                  # nome -> dict(label, entry, combos)
        self.execucao_atual = None              # ExecucaoQuery em andamento (ou None)
        self.ultimo_erro = None                 # último erro para o botão "Copiar erro"

        self.lbl_status = ctk.CTkLabel(self, text="Verificando conexão...", anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=(10, 0))
        threading.Thread(target=self._testar, daemon=True).start()

        self._montar_layout()
        self._atualizar_arvore()

        # Atalhos de teclado
        self.bind("<Control-Return>", lambda e: self._executar())
        self.bind("<Control-s>", lambda e: self._salvar())
        self.bind("<Control-S>", lambda e: self._salvar())

        # Maximiza a janela DEPOIS de tudo estar construído
        self.after(200, self._maximizar)

    def _maximizar(self):
        """Maximiza a janela de forma robusta (Windows)."""
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

    # ---------- Layout ----------
    def _montar_layout(self):
        # Estilo escuro para os Treeview (biblioteca + resultados)
        estilo_ttk = ttk.Style(self)
        try:
            estilo_ttk.theme_use("clam")
        except Exception:
            pass
        estilo_ttk.configure("Treeview",
                             background="#1e1e1e", fieldbackground="#1e1e1e",
                             foreground="#e6e6e6", font=("Segoe UI", 11),
                             rowheight=24, borderwidth=0)
        estilo_ttk.map("Treeview",
                       background=[("selected", "#3a7ebf")],
                       foreground=[("selected", "#ffffff")])
        estilo_ttk.configure("Treeview.Heading",
                             background="#2c2c2c", foreground="#e6e6e6",
                             font=("Segoe UI", 10, "bold"))
        estilo_ttk.map("Treeview.Heading", background=[("active", "#3a3a3a")])

        principal = ctk.CTkFrame(self)
        principal.pack(fill="both", expand=True, padx=10, pady=10)

        # Painel esquerdo: biblioteca com pastas
        esq = ctk.CTkFrame(principal, width=300)
        esq.pack(side="left", fill="y", padx=(0, 10))
        esq.pack_propagate(False)

        ctk.CTkLabel(esq, text="Queries Salvas", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))

        # ---- Container da árvore (expande e empurra os botões para baixo) ----
        tree_container = ctk.CTkFrame(esq)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree_lib = ttk.Treeview(tree_container, show="tree", selectmode="browse")
        sc_lib = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_lib.yview)
        self.tree_lib.configure(yscrollcommand=sc_lib.set)
        self.tree_lib.pack(side="left", fill="both", expand=True)
        sc_lib.pack(side="right", fill="y")
        self.tree_lib.bind("<<TreeviewSelect>>", self._abrir_selecionada)

        # ---- Botões de biblioteca NA PARTE DE BAIXO ----
        # Linha 1: Nova Query | Nova Pasta
        frame_bt1 = ctk.CTkFrame(esq)
        frame_bt1.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkButton(frame_bt1, text="Nova Query", command=self._nova,
                      width=130).pack(side="left", padx=3, expand=True)
        ctk.CTkButton(frame_bt1, text="Nova Pasta", command=self._nova_pasta,
                      width=130).pack(side="left", padx=3, expand=True)

        # Linha 2: Renomear Pasta | Excluir
        frame_bt2 = ctk.CTkFrame(esq)
        frame_bt2.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkButton(frame_bt2, text="Renomear Pasta", command=self._renomear_pasta,
                      width=130).pack(side="left", padx=3, expand=True)
        ctk.CTkButton(frame_bt2, text="Excluir", command=self._excluir,
                      width=130, fg_color="#a03030", hover_color="#c04040").pack(side="left", padx=3, expand=True)

        # Configurar Conexão (largura total)
        ctk.CTkButton(esq, text="⚙ Configurar Conexão", command=self._abrir_config,
                      fg_color="#3a3a3a", hover_color="#4a4a4a").pack(fill="x", padx=8, pady=(0, 8))

        # Painel direito: editor + resultados
        dir_ = ctk.CTkFrame(principal)
        dir_.pack(side="left", fill="both", expand=True)

        self.ent_nome = ctk.CTkEntry(dir_, placeholder_text="Nome da query")
        self.ent_nome.pack(fill="x", padx=10, pady=(10, 5))
        self.ent_desc = ctk.CTkEntry(dir_, placeholder_text="Descrição (opcional)")
        self.ent_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(dir_, text="SQL — use {{NOME}} sem aspas nos filtros:",
                     anchor="w").pack(fill="x", padx=10)
        self.txt_sql = ctk.CTkTextbox(dir_, height=160, font=("Consolas", 12))
        self.txt_sql.pack(fill="x", padx=10, pady=5)
        self.txt_sql.bind("<KeyRelease>", lambda e: self._gerar_parametros())

        ctk.CTkLabel(dir_, text="Filtros (para datas digite DD/MM/AAAA):",
                     anchor="w").pack(fill="x", padx=10)
        self.frame_params = ctk.CTkScrollableFrame(dir_, height=120)
        self.frame_params.pack(fill="x", padx=10, pady=5)

        frame_botoes = ctk.CTkFrame(dir_)
        frame_botoes.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(frame_botoes, text="Salvar Query", command=self._salvar,
                      width=120).pack(side="left", padx=5)
        self.btn_executar = ctk.CTkButton(frame_botoes, text="Executar",
                                          command=self._executar, width=100)
        self.btn_executar.pack(side="left", padx=5)
        self.btn_parar = ctk.CTkButton(frame_botoes, text="Parar",
                                       command=self._parar, width=90,
                                       fg_color="#a03030", hover_color="#c04040")
        self.btn_parar.pack(side="left", padx=5)
        self.btn_parar.configure(state="disabled")
        self.btn_limpar = ctk.CTkButton(frame_botoes, text="Limpar",
                                        command=self._limpar, width=90,
                                        fg_color="#5a5a5a", hover_color="#6f6f6f")
        self.btn_limpar.pack(side="left", padx=5)
        self.btn_limpar.configure(state="disabled")
        ctk.CTkButton(frame_botoes, text="Exportar XLSX", command=self._exportar,
                      width=130).pack(side="left", padx=5)
        ctk.CTkButton(frame_botoes, text="Exportar PDF", command=self._exportar_pdf,
                      width=130).pack(side="left", padx=5)

        # Barra de resultado (destaque de conclusão e contagem de linhas)
        frame_resultado = ctk.CTkFrame(dir_)
        frame_resultado.pack(fill="x", padx=10, pady=(5, 0))

        self.lbl_resultado = ctk.CTkLabel(
            frame_resultado, text="", anchor="w", font=("Segoe UI", 14, "bold"),
            text_color="#7fd47f",
        )
        self.lbl_resultado.pack(side="left", fill="x", expand=True)

        self.btn_copiar_erro = ctk.CTkButton(
            frame_resultado, text="📋 Copiar erro", command=self._copiar_erro,
            width=110, fg_color="#5a5a5a", hover_color="#6f6f6f")
        self.btn_copiar_erro.pack(side="right", padx=4)
        self.btn_copiar_erro.configure(state="disabled")

        # Tabela de resultados
        self.tree = ttk.Treeview(dir_, show="headings")
        sc_y = ttk.Scrollbar(dir_, orient="vertical", command=self.tree.yview)
        sc_x = ttk.Scrollbar(dir_, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sc_y.set, xscrollcommand=sc_x.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 0))
        sc_y.pack(side="right", fill="y")
        sc_x.pack(side="bottom", fill="x")

        self.lbl_info = ctk.CTkLabel(dir_, text="", anchor="w", text_color="gray")
        self.lbl_info.pack(fill="x", padx=10, pady=(5, 10))

    # ---------- Biblioteca (pastas + queries) ----------
    def _atualizar_arvore(self):
        self.tree_lib.delete(*self.tree_lib.get_children())
        for i, pasta in enumerate(self.estrutura["pastas"]):
            iid_p = f"pasta_{i}"
            self.tree_lib.insert("", "end", iid=iid_p,
                                 text=f"📁 {pasta['nome']}", open=True)
            for j, q in enumerate(pasta["queries"]):
                self.tree_lib.insert(iid_p, "end",
                                     iid=f"pq_{i}_{j}", text=f"    {q['nome']}")
        for i, q in enumerate(self.estrutura["queries"]):
            self.tree_lib.insert("", "end", iid=f"q_{i}", text=f"    {q['nome']}")

    def _item_selecionado(self):
        """Retorna (tipo, pasta_idx, query_idx): 'pasta' | 'query' | (None,None,None)."""
        sel = self.tree_lib.selection()
        if not sel:
            return (None, None, None)
        iid = sel[0]
        if iid.startswith("pasta_"):
            return ("pasta", int(iid.split("_")[1]), None)
        if iid.startswith("pq_"):
            partes = iid.split("_")
            return ("query", int(partes[1]), int(partes[2]))
        if iid.startswith("q_"):
            return ("query", None, int(iid.split("_")[1]))
        return (None, None, None)

    def _query_por_indice(self, pasta_idx, query_idx):
        if pasta_idx is None:
            if 0 <= query_idx < len(self.estrutura["queries"]):
                return self.estrutura["queries"][query_idx]
            return None
        if 0 <= pasta_idx < len(self.estrutura["pastas"]):
            pasta = self.estrutura["pastas"][pasta_idx]
            if 0 <= query_idx < len(pasta["queries"]):
                return pasta["queries"][query_idx]
        return None

    def _lista_da_pasta(self, pasta_idx):
        if pasta_idx is None:
            return self.estrutura["queries"]
        return self.estrutura["pastas"][pasta_idx]["queries"]

    def _adicionar_em_pasta(self, nova, pasta_idx):
        self._lista_da_pasta(pasta_idx).append(nova)

    def _iid_do_item_atual(self):
        if self.local_atual is None:
            return None
        pasta_idx, query_idx = self.local_atual
        if pasta_idx is None:
            return f"q_{query_idx}"
        return f"pq_{pasta_idx}_{query_idx}"

    def _selecionar_item_atual(self):
        iid = self._iid_do_item_atual()
        if iid:
            try:
                self.tree_lib.selection_set(iid)
                self.tree_lib.see(iid)
            except Exception:
                pass

    def _nova(self):
        tipo, pasta_idx, _q = self._item_selecionado()
        # Ao criar, a nova query entra na pasta do item selecionado (ou raiz)
        self.pasta_nova_destino = pasta_idx if tipo in ("pasta", "query") else None
        self.local_atual = None
        self.query_salva_atual = None
        self.ent_nome.delete(0, "end")
        self.ent_desc.delete(0, "end")
        self.txt_sql.delete("1.0", "end")
        self.tree_lib.selection_remove(self.tree_lib.selection())
        self._gerar_parametros()
        self.lbl_resultado.configure(text="")
        self.lbl_info.configure(text="")
        self.btn_copiar_erro.configure(state="disabled")

    def _abrir_selecionada(self, _event=None):
        tipo, pasta_idx, query_idx = self._item_selecionado()
        if tipo != "query":
            return  # pasta selecionada: não carrega nada no editor
        q = self._query_por_indice(pasta_idx, query_idx)
        if q is None:
            return
        self.local_atual = (pasta_idx, query_idx)
        self.query_salva_atual = q
        self.ent_nome.delete(0, "end")
        self.ent_nome.insert(0, q["nome"])
        self.ent_desc.delete(0, "end")
        self.ent_desc.insert(0, q.get("descricao", ""))
        self.txt_sql.delete("1.0", "end")
        self.txt_sql.insert("1.0", q["sql"])
        self._gerar_parametros()
        self.lbl_resultado.configure(text="")
        self.lbl_info.configure(text="")
        self.btn_copiar_erro.configure(state="disabled")

    def _nova_pasta(self):
        nome = simpledialog.askstring("Nova Pasta", "Nome da pasta:", parent=self)
        if not nome or not nome.strip():
            return
        nome = nome.strip()
        if any(p["nome"].lower() == nome.lower() for p in self.estrutura["pastas"]):
            messagebox.showwarning("Atenção", "Já existe uma pasta com esse nome.")
            return
        self.estrutura["pastas"].append({"nome": nome, "queries": []})
        salvar_queries(self.estrutura)
        self._atualizar_arvore()

    def _renomear_pasta(self):
        tipo, pasta_idx, _q = self._item_selecionado()
        if tipo != "pasta":
            messagebox.showwarning("Atenção", "Selecione uma pasta para renomear.")
            return
        atual = self.estrutura["pastas"][pasta_idx]["nome"]
        novo = simpledialog.askstring("Renomear Pasta", "Novo nome da pasta:",
                                      initialvalue=atual, parent=self)
        if not novo or not novo.strip():
            return
        novo = novo.strip()
        if any(p["nome"].lower() == novo.lower() and i != pasta_idx
               for i, p in enumerate(self.estrutura["pastas"])):
            messagebox.showwarning("Atenção", "Já existe uma pasta com esse nome.")
            return
        self.estrutura["pastas"][pasta_idx]["nome"] = novo
        salvar_queries(self.estrutura)
        self._atualizar_arvore()

    def _excluir(self):
        tipo, pasta_idx, query_idx = self._item_selecionado()
        if tipo == "query":
            q = self._query_por_indice(pasta_idx, query_idx)
            if q is None:
                return
            nome = q["nome"]
            if messagebox.askyesno("Excluir", f"Excluir a query '{nome}'?"):
                if pasta_idx is None:
                    del self.estrutura["queries"][query_idx]
                else:
                    del self.estrutura["pastas"][pasta_idx]["queries"][query_idx]
                salvar_queries(self.estrutura)
                self._atualizar_arvore()
                self._nova()
        elif tipo == "pasta":
            pasta = self.estrutura["pastas"][pasta_idx]
            n = len(pasta["queries"])
            if messagebox.askyesno(
                    "Excluir",
                    f"Excluir a pasta '{pasta['nome']}' com {n} query(s)?\n"
                    "As queries dentro dela também serão excluídas."):
                del self.estrutura["pastas"][pasta_idx]
                salvar_queries(self.estrutura)
                self._atualizar_arvore()
                self._nova()
        else:
            messagebox.showwarning("Atenção", "Selecione uma query ou pasta.")

    def _salvar(self):
        nome = self.ent_nome.get().strip()
        sql = self.txt_sql.get("1.0", "end").strip()
        if not nome:
            messagebox.showwarning("Atenção", "Informe o nome da query.")
            return
        if not sql:
            messagebox.showwarning("Atenção", "Informe o SQL.")
            return

        parametros = []
        for nome_p, cfg in self.campos_param.items():
            parametros.append({
                "nome": nome_p,
                "label": cfg["label"],
                "tipo": cfg["combo_tipo"].get(),
                "formato": cfg["combo_formato"].get(),
            })

        nova = {
            "nome": nome,
            "descricao": self.ent_desc.get().strip(),
            "sql": sql,
            "parametros": parametros,
        }

        if self.local_atual is not None:
            pasta_idx, query_idx = self.local_atual
            alvo = self._query_por_indice(pasta_idx, query_idx)
            if alvo is not None:
                alvo.update(nova)  # atualiza no lugar (mantém posição)
                self.query_salva_atual = alvo
            else:
                self._adicionar_em_pasta(nova, self.pasta_nova_destino)
                self.local_atual = (
                    self.pasta_nova_destino,
                    len(self._lista_da_pasta(self.pasta_nova_destino)) - 1)
                self.query_salva_atual = nova
        else:
            self._adicionar_em_pasta(nova, self.pasta_nova_destino)
            self.local_atual = (
                self.pasta_nova_destino,
                len(self._lista_da_pasta(self.pasta_nova_destino)) - 1)
            self.query_salva_atual = nova

        salvar_queries(self.estrutura)
        self._atualizar_arvore()
        self._selecionar_item_atual()
        self._gerar_parametros()  # recarrega combos com os tipos salvos

    # ---------- Parâmetros dinâmicos ----------
    def _gerar_parametros(self):
        sql = self.txt_sql.get("1.0", "end")
        placeholders = set(re.findall(r"\{\{(\w+)\}\}", sql))

        # Remove campos que não existem mais
        for nome_p in list(self.campos_param):
            if nome_p not in placeholders:
                for widget in self.campos_param[nome_p]["widgets"]:
                    widget.destroy()
                del self.campos_param[nome_p]

        # Cria campos novos (usa tipo/formato salvos quando existem)
        for nome_p in placeholders:
            if nome_p in self.campos_param:
                continue
            label = nome_p.replace("_", " ").title()
            tipo, formato = "texto", "cyymmdd"
            if self.query_salva_atual is not None:
                for p in self.query_salva_atual.get("parametros", []):
                    if p["nome"] == nome_p:
                        tipo = p.get("tipo", "texto")
                        formato = p.get("formato", "cyymmdd")
            self._criar_campo(nome_p, label, tipo, formato)

    def _criar_campo(self, nome_p, label, tipo, formato):
        linha = ctk.CTkFrame(self.frame_params)
        linha.pack(fill="x", pady=2)

        ctk.CTkLabel(linha, text=f"{label}:", width=170, anchor="w").pack(side="left", padx=5)

        entry = ctk.CTkEntry(linha, placeholder_text="DD/MM/AAAA" if tipo == "data" else "valor")
        entry.pack(side="left", fill="x", expand=True, padx=5)

        combo_tipo = ctk.CTkComboBox(linha, values=["texto", "data"], width=90,
                                     state="readonly", command=lambda _v: None)
        combo_tipo.set(tipo)
        combo_tipo.pack(side="left", padx=3)

        combo_formato = ctk.CTkComboBox(linha, values=["aaaammdd", "cyymmdd"], width=110,
                                        state="readonly", command=lambda _v: None)
        combo_formato.set(formato)
        combo_formato.pack(side="left", padx=3)

        self.campos_param[nome_p] = {
            "label": label,
            "entry": entry,
            "combo_tipo": combo_tipo,
            "combo_formato": combo_formato,
            "widgets": [linha, entry, combo_tipo, combo_formato],
        }

    def _montar_sql_final(self) -> str:
        sql = self.txt_sql.get("1.0", "end")
        for nome_p, cfg in self.campos_param.items():
            valor = cfg["entry"].get().strip()
            if cfg["combo_tipo"].get() == "data":
                if not valor:
                    raise ValueError(f"Preencha o campo '{cfg['label']}'.")
                valor = db.data_para_protheus(valor, cfg["combo_formato"].get())
            valor = valor.replace("'", "''")  # protege contra aspas no valor
            sql = sql.replace("{{" + nome_p + "}}", f"'{valor}'")

        # Detecta placeholders que sobraram (não preenchidos)
        sobrou = re.findall(r"\{\{(\w+)\}\}", sql)
        if sobrou:
            raise ValueError(f"Placeholders sem campo de filtro: {', '.join(sobrou)}")
        return sql

    # ---------- Execução / Parar / Limpar / Exportação ----------
    def _set_executando(self, ativo: bool):
        """Habilita/desabilita os botões conforme o estado de execução."""
        self.btn_executar.configure(state="disabled" if ativo else "normal")
        self.btn_parar.configure(state="normal" if ativo else "disabled")
        # Limpar só fica ativo quando há resultado e não está executando
        if ativo:
            self.btn_limpar.configure(state="disabled")
        else:
            self.btn_limpar.configure(state="normal" if self.df_atual is not None else "disabled")

    def _executar(self):
        if self.execucao_atual is not None:
            return  # já existe uma consulta em andamento

        try:
            sql = self._montar_sql_final()
        except ValueError as e:
            messagebox.showwarning("Atenção", str(e))
            return

        # Limpa resultado anterior para não misturar dados
        self.df_atual = None
        self.tree.delete(*self.tree.get_children())

        self.execucao_atual = db.ExecucaoQuery()
        self.lbl_resultado.configure(text="⏳ Executando consulta...", text_color="#e0b84c")
        self.lbl_info.configure(text="Aguardando resposta do banco...")
        self._inicio_execucao = time.time()
        self._set_executando(True)

        threading.Thread(target=self._worker, args=(sql, self.execucao_atual),
                         daemon=True).start()

    def _parar(self):
        if self.execucao_atual is None:
            return
        self.lbl_resultado.configure(text="⏹ Parando consulta...", text_color="#e0b84c")
        self.lbl_info.configure(text="Cancelando consulta no servidor...")
        self.execucao_atual.cancelar()

    def _limpar(self):
        """Limpa o resultado atual para iniciar uma nova execução."""
        if self.execucao_atual is not None:
            return  # não limpa durante a execução
        self.df_atual = None
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []
        self.lbl_resultado.configure(text="")
        self.lbl_info.configure(text="")
        self.btn_limpar.configure(state="disabled")
        self.btn_copiar_erro.configure(state="disabled")

    def _copiar_erro(self):
        """Copia o último erro para a área de transferência."""
        if not self.ultimo_erro:
            return
        self.clipboard_clear()
        self.clipboard_append(self.ultimo_erro)
        self.lbl_info.configure(text="Erro copiado para a área de transferência. Cole aqui no chat.")
        messagebox.showinfo("Copiado", "Erro copiado. Cole no chat para eu analisar.")

    def _worker(self, sql, execucao):
        try:
            df = db.executar_query(sql, execucao)
            self.fila.put(("ok", df))
        except db.CancelaConsulta:
            self.fila.put(("cancelado", None))
        except Exception as e:
            self.fila.put(("erro", str(e)))
        self.after(100, self._processar)

    def _processar(self):
        try:
            status, payload = self.fila.get_nowait()
        except queue.Empty:
            return

        if status == "cancelado":
            self.execucao_atual = None
            self._set_executando(False)
            self.lbl_resultado.configure(text="⏹ Consulta cancelada", text_color="#e0b84c")
            self.lbl_info.configure(text="A execução foi interrompida antes da conclusão.")
            return

        if status == "erro":
            self.execucao_atual = None
            self._set_executando(False)
            self.ultimo_erro = payload
            registrar_erro("Consulta", payload)
            self.lbl_resultado.configure(text="❌ Erro na consulta", text_color="#e05b5b")
            self.lbl_info.configure(text=f"{payload}")
            self.btn_copiar_erro.configure(state="normal")
            messagebox.showerror("Erro", payload)
            return

        # status == "ok"
        self.execucao_atual = None
        self.df_atual = payload
        self.ultimo_erro = None
        self.btn_copiar_erro.configure(state="disabled")

        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [str(c) for c in payload.columns]
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="w")

        for _, row in payload.head(500).iterrows():
            valores = ["" if v is None else str(v) for v in row]
            self.tree.insert("", "end", values=valores)

        tempo = time.time() - getattr(self, "_inicio_execucao", time.time())
        n_linhas = len(payload)
        n_colunas = len(payload.columns)

        self.lbl_resultado.configure(
            text=f"✅ Consulta concluída em {tempo:.1f}s — {n_linhas:,} linhas".replace(",", "."),
            text_color="#7fd47f",
        )

        texto = f"{n_colunas} colunas"
        if n_linhas == db.LIMITE_PADRAO:
            texto += "  (resultado limitado a 5000 linhas — ajuste LIMITE_PADRAO em db.py)"
        self.lbl_info.configure(text=texto)

        self._set_executando(False)  # reativa o Limpar (agora há resultado)

    # ---------- Configuração da conexão ----------
    @staticmethod
    def _drivers_instalados():
        """Lista os drivers ODBC instalados na máquina."""
        try:
            import pyodbc
            return list(pyodbc.drivers())
        except Exception:
            return []

    def _abrir_config(self):
        """Abre a tela de configuração da conexão com o banco."""
        janela = ctk.CTkToplevel(self)
        janela.title("Configuração da Conexão")
        janela.geometry("560x500")
        janela.transient(self)
        janela.grab_set()  # modal
        janela.after(100, janela.lift)

        cfg_atual = config.carregar_config()
        drivers = self._drivers_instalados()
        if not drivers:
            drivers = ["ODBC Driver 18 for SQL Server",
                       "ODBC Driver 17 for SQL Server",
                       "SQL Server Native Client 11.0"]

        ctk.CTkLabel(janela, text="Configuração do Banco de Dados (SQL Server)",
                     font=("Segoe UI", 14, "bold")).pack(pady=(12, 6))

        frame = ctk.CTkFrame(janela)
        frame.pack(fill="both", expand=True, padx=14, pady=4)

        def _linha(label):
            lin = ctk.CTkFrame(frame)
            lin.pack(fill="x", pady=3)
            ctk.CTkLabel(lin, text=label, width=120, anchor="w").pack(side="left", padx=(6, 4))
            ent = ctk.CTkEntry(lin)
            ent.pack(side="left", fill="x", expand=True, padx=(0, 6))
            return ent

        ent_server = _linha("Servidor:")
        ent_server.configure(
            placeholder_text="ex.: 10.0.0.15, 10.0.0.15\\DB01 ou 10.0.0.15,1433")
        ent_server.insert(0, cfg_atual.get("server", ""))

        hint = ctk.CTkLabel(frame,
                            text="Formatos aceitos: IP | IP\\INSTANCIA | IP,porta",
                            text_color="gray", font=("Segoe UI", 10))
        hint.pack(anchor="w", padx=14)

        ent_banco = _linha("Banco:")
        ent_banco.insert(0, cfg_atual.get("database", ""))

        ent_usuario = _linha("Usuário:")
        ent_usuario.insert(0, cfg_atual.get("username", ""))

        ent_senha = _linha("Senha:")
        ent_senha.configure(show="*")
        ent_senha.insert(0, cfg_atual.get("password", ""))

        lin_driver = ctk.CTkFrame(frame)
        lin_driver.pack(fill="x", pady=3)
        ctk.CTkLabel(lin_driver, text="Driver:", width=120, anchor="w").pack(side="left", padx=(6, 4))
        combo_driver = ctk.CTkComboBox(lin_driver, values=drivers, width=280)
        combo_driver.set(cfg_atual.get("driver", drivers[0]))
        combo_driver.pack(side="left", fill="x", expand=True, padx=(0, 6))

        var_trust = tk.BooleanVar(value=cfg_atual.get("trust_certificate", True))
        ctk.CTkCheckBox(frame, text="TrustServerCertificate (confiar no certificado SSL)",
                        variable=var_trust).pack(anchor="w", padx=12, pady=6)

        lbl_teste = ctk.CTkLabel(janela, text="", anchor="w", text_color="gray")
        lbl_teste.pack(fill="x", padx=14)

        def _cfg_da_tela():
            return {
                "server": config.normalizar_servidor(ent_server.get()),
                "database": ent_banco.get().strip(),
                "username": ent_usuario.get().strip(),
                "password": ent_senha.get().strip(),
                "driver": combo_driver.get().strip(),
                "trust_certificate": bool(var_trust.get()),
                "timeout": cfg_atual.get("timeout", 30),
            }

        def _validar_obrigatorios(nova_cfg):
            faltando = []
            for rotulo, valor in (("Servidor", nova_cfg["server"]),
                                  ("Banco", nova_cfg["database"]),
                                  ("Usuário", nova_cfg["username"])):
                if not valor:
                    faltando.append(rotulo)
            return faltando

        def _testar_da_tela():
            nova_cfg = _cfg_da_tela()
            faltando = _validar_obrigatorios(nova_cfg)
            if faltando:
                lbl_teste.configure(
                    text="⚠ Preencha os campos obrigatórios: " + ", ".join(faltando) + ".",
                    text_color="#e0b84c")
                return
            lbl_teste.configure(text="⏳ Testando conexão...", text_color="#e0b84c")
            threading.Thread(target=_worker_teste, args=(nova_cfg,), daemon=True).start()

        def _worker_teste(nova_cfg):
            msg = db.testar_conexao(nova_cfg)
            janela.after(0, lambda: _mostrar_teste(msg))

        def _mostrar_teste(msg):
            ok = msg.startswith("Conectado")
            lbl_teste.configure(text=msg,
                                text_color="#7fd47f" if ok else "#e05b5b")

        def _salvar_config():
            nova_cfg = _cfg_da_tela()
            faltando = _validar_obrigatorios(nova_cfg)
            if faltando:
                lbl_teste.configure(
                    text="⚠ Preencha os campos obrigatórios: " + ", ".join(faltando) + ".",
                    text_color="#e0b84c")
                return
            config.salvar_config(nova_cfg)
            janela.destroy()
            # Repete o teste de conexão na barra de status principal
            threading.Thread(target=self._testar, daemon=True).start()
            messagebox.showinfo("Salvo", "Conexão salva. Testando nova configuração...")

        frame_botoes = ctk.CTkFrame(janela)
        frame_botoes.pack(fill="x", padx=14, pady=(6, 12))
        ctk.CTkButton(frame_botoes, text="Testar Conexão", command=_testar_da_tela,
                      width=130).pack(side="left", padx=5)
        ctk.CTkButton(frame_botoes, text="Salvar", command=_salvar_config,
                      width=110, fg_color="#2c5f8a", hover_color="#3a6f9e").pack(side="left", padx=5)
        ctk.CTkButton(frame_botoes, text="Cancelar", command=janela.destroy,
                      width=100).pack(side="left", padx=5)

    # ---------- Exportação ----------
    def _exportar(self):
        if self.df_atual is None:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return
        nome_base = (self.ent_nome.get().strip() or "relatorio").replace(" ", "_")
        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"{nome_base}_{datetime.now():%Y%m%d_%H%M}.xlsx",
        )
        if not caminho:
            return
        try:
            db.exportar_xlsx(self.df_atual, caminho)
            messagebox.showinfo("Sucesso", f"Exportado:\n{caminho}")
        except Exception as e:
            registrar_erro("Exportar XLSX", str(e))
            messagebox.showerror("Erro", f"Falha ao exportar XLSX:\n{e}")

    def _exportar_pdf(self):
        if self.df_atual is None:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return
        nome_sugerido = (self.ent_nome.get().strip() or "relatorio").replace(" ", "_")
        caminho = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{nome_sugerido}_{datetime.now():%Y%m%d_%H%M}.pdf",
        )
        if not caminho:
            return
        try:
            titulo = self.ent_nome.get().strip() or "Relatório Protheus"
            pdf.exportar_pdf(self.df_atual, caminho, titulo=titulo)
            messagebox.showinfo("Sucesso", f"PDF gerado:\n{caminho}")
        except Exception as e:
            registrar_erro("Exportar PDF", str(e))
            messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

    def _testar(self):
        msg = db.testar_conexao()
        self.after(0, lambda: self.lbl_status.configure(text=msg))
        if not msg.startswith("Conectado"):
            self.ultimo_erro = msg
            registrar_erro("Conexão", msg)
            self.after(0, lambda: self.btn_copiar_erro.configure(state="normal"))


if __name__ == "__main__":
    AppProtheus().mainloop()