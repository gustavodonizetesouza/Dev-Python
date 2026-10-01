# ============================================================
# APP PROTHEUS REPORTS - Interface Gráfica
# Aba 1: Consulta SQL (colar query, executar, exportar XLSX)
# Aba 2: Dashboard (gráficos a partir do resultado)
# ============================================================
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import db

# ---------------- Tema ----------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppProtheus(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Protheus Reports")
        self.geometry("1100x700")

        self.fila_resultado = queue.Queue()
        self.df_atual = None

        # ------- Barra de status / conexão -------
        self.lbl_status = ctk.CTkLabel(
            self, text="Verificando conexão...", anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=(10, 0))
        self._testar_conexao_async()

        # ------- Abas -------
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_consulta = self.tabs.add("Consulta SQL")
        self.tab_dashboard = self.tabs.add("Dashboard")
        self._montar_aba_consulta()
        self._montar_aba_dashboard()

    # ========== ABA CONSULTA ==========
    def _montar_aba_consulta(self):
        # Área de texto para colar a query
        self.txt_query = ctk.CTkTextbox(
            self.tab_consulta, height=180, font=("Consolas", 12))
        self.txt_query.pack(fill="x", padx=10, pady=(10, 5))
        self.txt_query.insert("1.0", self._query_exemplo())

        # Botões
        frame_botoes = ctk.CTkFrame(self.tab_consulta)
        frame_botoes.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(frame_botoes, text="▶ Executar", command=self._executar,
                      width=120).pack(side="left", padx=5)
        ctk.CTkButton(frame_botoes, text="📥 Exportar XLSX", command=self._exportar,
                      width=140).pack(side="left", padx=5)
        ctk.CTkButton(frame_botoes, text="📊 Ver Dashboard", command=self._gerar_dashboard,
                      width=150).pack(side="left", padx=5)

        # Tabela de resultados
        self.tree = ttk.Treeview(self.tab_consulta, show="headings")
        scroll_y = ttk.Scrollbar(
            self.tab_consulta, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(
            self.tab_consulta, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set,
                            xscrollcommand=scroll_x.set)

        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.lbl_info = ctk.CTkLabel(self.tab_consulta, text="", anchor="w")
        self.lbl_info.pack(fill="x", padx=10, pady=(0, 10))

    def _executar(self):
        sql = self.txt_query.get("1.0", "end").strip()
        if not sql:
            messagebox.showwarning(
                "Atenção", "Cole uma query antes de executar.")
            return

        self.lbl_info.configure(text="⏳ Executando consulta...")
        threading.Thread(target=self._worker_executar,
                         args=(sql,), daemon=True).start()

    def _worker_executar(self, sql):
        try:
            df = db.executar_query(sql)
            self.fila_resultado.put(("ok", df))
        except Exception as e:
            self.fila_resultado.put(("erro", str(e)))
        self.after(100, self._processar_resultado)

    def _processar_resultado(self):
        try:
            status, payload = self.fila_resultado.get_nowait()
        except queue.Empty:
            return

        if status == "erro":
            self.lbl_info.configure(text=f"❌ Erro: {payload}")
            messagebox.showerror("Erro", payload)
            return

        self.df_atual = payload
        self._preencher_tabela(self.df_atual)
        self.lbl_info.configure(
            text=f"✅ {len(self.df_atual)} registros retornados em {len(self.df_atual.columns)} colunas."
        )

    def _preencher_tabela(self, df):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=str(col))
            self.tree.column(col, width=120, anchor="w")
        for _, row in df.head(500).iterrows():
            self.tree.insert("", "end", values=list(row))

    def _exportar(self):
        if self.df_atual is None:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return
        caminho = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="relatorio_protheus.xlsx",
        )
        if not caminho:
            return
        try:
            db.exportar_xlsx(self.df_atual, caminho)
            messagebox.showinfo("Sucesso", f"Exportado para:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível exportar:\n{e}")

    # ========== ABA DASHBOARD ==========
    def _montar_aba_dashboard(self):
        self.frame_grafico = ctk.CTkFrame(self.tab_dashboard)
        self.frame_grafico.pack(fill="both", expand=True, padx=10, pady=10)
        self.lbl_dash = ctk.CTkLabel(
            self.tab_dashboard,
            text="Execute uma consulta e clique em 'Ver Dashboard'.",
            text_color="gray",
        )
        self.lbl_dash.pack(pady=20)

    def _gerar_dashboard(self):
        if self.df_atual is None or self.df_atual.empty:
            messagebox.showwarning("Atenção", "Execute uma consulta primeiro.")
            return

        for widget in self.frame_grafico.winfo_children():
            widget.destroy()
        self.lbl_dash.pack_forget()

        df = self.df_atual
        fig = Figure(figsize=(9, 5), dpi=100)
        ax = fig.add_subplot(111)

        # Escolhe a primeira coluna numérica para o gráfico
        col_numerica = df.select_dtypes(include="number").columns
        if len(col_numerica) > 0:
            col = col_numerica[0]
            ax.bar(df[df.columns[0]].astype(str).head(20), df[col].head(20))
            ax.set_title(f"Distribuição por {col}")
            ax.tick_params(axis="x", rotation=45)
        else:
            # Sem coluna numérica: mostra contagem por categoria
            col = df.columns[0]
            contagem = df[col].value_counts().head(15)
            ax.bar(contagem.index.astype(str), contagem.values)
            ax.set_title(f"Contagem por {col}")
            ax.tick_params(axis="x", rotation=45)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ========== UTILITÁRIOS ==========
    def _testar_conexao_async(self):
        def worker():
            msg = db.testar_conexao()
            self.after(0, lambda: self.lbl_status.configure(text=msg))
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _query_exemplo() -> str:
        return """SELECT
    F1_EMISSAO AS 'EMISSÃO',
    F1_DOC     AS 'DOCUMENTO',
    F1_FORNECE AS 'FORNECEDOR',
    A2.A2_NOME    AS 'NOME FORNECEDOR',
    F8_NFDIFRE AS 'DOCUMENTO FRETE',
    F8_TRANSP  AS 'TRANSPORTADORA',
    A4.A2_NOME    AS 'NOME TRANSPORTADORA',
    F8_DTDIGIT AS 'DATA DIGITAÇÃO'
FROM SF8010 F8
INNER JOIN SF1010 F1
    ON F1.F1_DOC = F8.F8_NFORIG
    AND F1.D_E_L_E_T_ = ''
INNER JOIN SA2010 A2
    ON A2.A2_COD = F8.F8_FORNECE
INNER JOIN SA2010 A4
    ON A4.A2_COD = F8.F8_TRANSP
WHERE F8_DTDIGIT BETWEEN '20260428' AND '20260728'
    AND F8.D_E_L_E_T_ = ''"""


if __name__ == "__main__":
    app = AppProtheus()
    app.mainloop()
