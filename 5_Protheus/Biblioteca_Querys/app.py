# ============================================================
# app.py - Protheus Reports (Biblioteca de Queries)
#   - Biblioteca de queries persistente (queries.json)
#   - Filtros dinâmicos (data e texto) com conversão Protheus
#   - Execução em thread + botão PARAR (cancela no servidor)
#   - Botão LIMPAR (zera o resultado para nova execução)
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
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import db
import pdf_export as pdf

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ARQUIVO_QUERIES = "queries.json"


def carregar_queries():
    if not os.path.exists(ARQUIVO_QUERIES):
        return []
    with open(ARQUIVO_QUERIES, "r", encoding="utf-8") as f:
        return json.load(f).get("queries", [])


def salvar_queries(queries):
    with open(ARQUIVO_QUERIES, "w", encoding="utf-8") as f:
        json.dump({"queries": queries}, f, ensure_ascii=False, indent=2)


class AppProtheus(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Protheus Reports - Biblioteca de Queries")
        self.geometry("1300x760")

        self.queries = carregar_queries()
        self.indice_atual = None
        self.df_atual = None
        self.fila = queue.Queue()
        self.campos_param = {}          # nome -> dict(label, entry, combos)
        self.execucao_atual = None      # ExecucaoQuery em andamento (ou None)

        self.lbl_status = ctk.CTkLabel(
            self, text="Verificando conexão...", anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=(10, 0))
        threading.Thread(target=self._testar, daemon=True).start()

        self._montar_layout()
        self._atualizar_lista()

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
        principal = ctk.CTkFrame(self)
        principal.pack(fill="both", expand=True, padx=10, pady=10)

        # Painel esquerdo: biblioteca
        esq = ctk.CTkFrame(principal, width=280)
        esq.pack(side="left", fill="y", padx=(0, 10))
        esq.pack_propagate(False)

        ctk.CTkLabel(esq, text="Queries Salvas", font=(
            "Segoe UI", 14, "bold")).pack(pady=(10, 5))

        self.lista = tk_Listbox(esq)
        self.lista.pack(fill="both", expand=True, padx=8)
        self.lista.bind("<<ListboxSelect>>", self._abrir_selecionada)

        frame_bt = ctk.CTkFrame(esq)
        frame_bt.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(frame_bt, text="Nova", command=self._nova,
                      width=70).pack(side="left", padx=2)
        ctk.CTkButton(frame_bt, text="Excluir", command=self._excluir,
                      width=70).pack(side="left", padx=2)

        # Painel direito: editor + resultados
        dir_ = ctk.CTkFrame(principal)
        dir_.pack(side="left", fill="both", expand=True)

        self.ent_nome = ctk.CTkEntry(dir_, placeholder_text="Nome da query")
        self.ent_nome.pack(fill="x", padx=10, pady=(10, 5))
        self.ent_desc = ctk.CTkEntry(
            dir_, placeholder_text="Descrição (opcional)")
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
        self.lbl_resultado = ctk.CTkLabel(
            dir_, text="", anchor="w", font=("Segoe UI", 14, "bold"),
            text_color="#7fd47f",
        )
        self.lbl_resultado.pack(fill="x", padx=10, pady=(5, 0))

        # Tabela de resultados
        self.tree = ttk.Treeview(dir_, show="headings")
        sc_y = ttk.Scrollbar(dir_, orient="vertical", command=self.tree.yview)
        sc_x = ttk.Scrollbar(dir_, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=sc_y.set, xscrollcommand=sc_x.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 0))
        sc_y.pack(side="right", fill="y")
        sc_x.pack(side="bottom", fill="x")

        self.lbl_info = ctk.CTkLabel(
            dir_, text="", anchor="w", text_color="gray")
        self.lbl_info.pack(fill="x", padx=10, pady=(5, 10))

    # ---------- Biblioteca ----------
    def _atualizar_lista(self):
        self.lista.delete(0, "end")
        for q in self.queries:
            self.lista.insert("end", q["nome"])

    def _nova(self):
        self.indice_atual = None
        self.ent_nome.delete(0, "end")
        self.ent_desc.delete(0, "end")
        self.txt_sql.delete("1.0", "end")
        self.lista.selection_clear(0, "end")
        self._gerar_parametros()
        self.lbl_resultado.configure(text="")
        self.lbl_info.configure(text="")

    def _abrir_selecionada(self, _event=None):
        sel = self.lista.curselection()
        if not sel:
            return
        self.indice_atual = sel[0]
        q = self.queries[self.indice_atual]
        self.ent_nome.delete(0, "end")
        self.ent_nome.insert(0, q["nome"])
        self.ent_desc.delete(0, "end")
        self.ent_desc.insert(0, q.get("descricao", ""))
        self.txt_sql.delete("1.0", "end")
        self.txt_sql.insert("1.0", q["sql"])
        self._gerar_parametros()
        self.lbl_resultado.configure(text="")
        self.lbl_info.configure(text="")

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

        if self.indice_atual is not None:
            self.queries[self.indice_atual] = nova
        else:
            self.queries.append(nova)
            self.indice_atual = len(self.queries) - 1

        salvar_queries(self.queries)
        self._atualizar_lista()
        self.lista.selection_set(self.indice_atual)
        self._gerar_parametros()  # recarrega combos com os tipos salvos

    def _excluir(self):
        sel = self.lista.curselection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma query.")
            return
        idx = sel[0]
        nome = self.queries[idx]["nome"]
        if messagebox.askyesno("Excluir", f"Excluir '{nome}'?"):
            del self.queries[idx]
            salvar_queries(self.queries)
            self._atualizar_lista()
            self._nova()

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
            if self.indice_atual is not None:
                for p in self.queries[self.indice_atual].get("parametros", []):
                    if p["nome"] == nome_p:
                        tipo = p.get("tipo", "texto")
                        formato = p.get("formato", "cyymmdd")
            self._criar_campo(nome_p, label, tipo, formato)

    def _criar_campo(self, nome_p, label, tipo, formato):
        linha = ctk.CTkFrame(self.frame_params)
        linha.pack(fill="x", pady=2)

        ctk.CTkLabel(linha, text=f"{label}:", width=170,
                     anchor="w").pack(side="left", padx=5)

        entry = ctk.CTkEntry(
            linha, placeholder_text="DD/MM/AAAA" if tipo == "data" else "valor")
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
                valor = db.data_para_protheus(
                    valor, cfg["combo_formato"].get())
            valor = valor.replace("'", "''")  # protege contra aspas no valor
            sql = sql.replace("{{" + nome_p + "}}", f"'{valor}'")

        # Detecta placeholders que sobraram (não preenchidos)
        sobrou = re.findall(r"\{\{(\w+)\}\}", sql)
        if sobrou:
            raise ValueError(
                f"Placeholders sem campo de filtro: {', '.join(sobrou)}")
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
            self.btn_limpar.configure(
                state="normal" if self.df_atual is not None else "disabled")

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
        self.lbl_resultado.configure(
            text="⏳ Executando consulta...", text_color="#e0b84c")
        self.lbl_info.configure(text="Aguardando resposta do banco...")
        self._inicio_execucao = time.time()
        self._set_executando(True)

        threading.Thread(target=self._worker, args=(sql, self.execucao_atual),
                         daemon=True).start()

    def _parar(self):
        if self.execucao_atual is None:
            return
        self.lbl_resultado.configure(
            text="⏹ Parando consulta...", text_color="#e0b84c")
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
            self.lbl_resultado.configure(
                text="⏹ Consulta cancelada", text_color="#e0b84c")
            self.lbl_info.configure(
                text="A execução foi interrompida antes da conclusão.")
            return

        if status == "erro":
            self.execucao_atual = None
            self._set_executando(False)
            self.lbl_resultado.configure(
                text="❌ Erro na consulta", text_color="#e05b5b")
            self.lbl_info.configure(text=f"{payload}")
            messagebox.showerror("Erro", payload)
            return

        # status == "ok"
        self.execucao_atual = None
        self.df_atual = payload

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
            text=f"✅ Consulta concluída em {tempo:.1f}s — {n_linhas:,} linhas".replace(
                ",", "."),
            text_color="#7fd47f",
        )

        texto = f"{n_colunas} colunas"
        if n_linhas == db.LIMITE_PADRAO:
            texto += "  (resultado limitado a 5000 linhas — ajuste LIMITE_PADRAO em db.py)"
        self.lbl_info.configure(text=texto)

        self._set_executando(False)  # reativa o Limpar (agora há resultado)

    def _exportar(self):
        if self.df_atual is None:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return
        nome_base = (self.ent_nome.get().strip()
                     or "relatorio").replace(" ", "_")
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
            messagebox.showerror("Erro", f"Falha ao exportar XLSX:\n{e}")

    def _exportar_pdf(self):
        if self.df_atual is None:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return
        nome_sugerido = (self.ent_nome.get().strip()
                         or "relatorio").replace(" ", "_")
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
            messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

    def _testar(self):
        msg = db.testar_conexao()
        self.after(0, lambda: self.lbl_status.configure(text=msg))


def tk_Listbox(parent):
    """Listbox escura compatível com o tema do customtkinter."""
    import tkinter as tk
    return tk.Listbox(parent, bg="#1e1e1e", fg="white", selectbackground="#3a7ebf",
                      font=("Segoe UI", 11), activestyle="none")


if __name__ == "__main__":
    AppProtheus().mainloop()
