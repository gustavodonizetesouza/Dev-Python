# ============================================================
#  LOTERIA APP - Python + Tkinter + SQLite (Dark Modern v6)
#  Cadastro, consulta, estatísticas, ATRASO e ALERTA
#  Banco: arquivo loteria.db (criado automaticamente)
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import os
from collections import Counter
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "loteria.db")

LOTERIAS_PADRAO = [
    ("Lotofácil", 15, 1, 25),
    ("Mega-Sena", 6, 1, 60),
]

COLUNAS_D = ", ".join(f"D{i} INTEGER" for i in range(1, 21))

# ---------- Paleta de cores (dark mode) ----------
CORES = {
    "bg": "#1e1e2e",
    "card": "#2a2a3c",
    "card2": "#33334a",
    "borda": "#3f3f5a",
    "texto": "#e4e4ef",
    "texto2": "#a0a0b8",
    "destaque": "#6c5ce7",
    "destaque2": "#5a4bd1",
    "verde": "#00b894",
    "verde2": "#00997c",
    "vermelho": "#d63031",
    "selecao": "#4a4a6a",
    "quente": "#8a4a38",
    "frio": "#3d4f73",
    "atraso_top": "#5a2020",
}


def centralizar_janela(janela, largura, altura):
    """Posiciona a janela no centro da tela."""
    janela.update_idletasks()
    x = (janela.winfo_screenwidth() - largura) // 2
    y = (janela.winfo_screenheight() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{x}+{y}")


class Database:
    """Camada de dados: cria o banco e faz todas as operacoes."""

    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._criar_estrutura()

    def _criar_estrutura(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS Loterias (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Nome TEXT NOT NULL UNIQUE,
                QtdDezenas INTEGER NOT NULL,
                MinNumero INTEGER NOT NULL,
                MaxNumero INTEGER NOT NULL
            )
        """)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS Concursos (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                LoteriaId INTEGER NOT NULL,
                NumeroConcurso INTEGER NOT NULL,
                DataSorteio TEXT NOT NULL,
                DezenasKey TEXT NOT NULL,
                {COLUNAS_D},
                UNIQUE (LoteriaId, NumeroConcurso),
                FOREIGN KEY (LoteriaId) REFERENCES Loterias(Id)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS IX_Concursos_Loteria_Dezenas
            ON Concursos (LoteriaId, DezenasKey)
        """)
        for nome, qtd, mn, mx in LOTERIAS_PADRAO:
            c.execute(
                "INSERT OR IGNORE INTO Loterias (Nome, QtdDezenas, MinNumero, MaxNumero) VALUES (?,?,?,?)",
                (nome, qtd, mn, mx),
            )
        self._conn.commit()
        c.close()

    def listar_loterias(self):
        rows = self._conn.execute(
            "SELECT Id, Nome, QtdDezenas, MinNumero, MaxNumero FROM Loterias ORDER BY Nome"
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def normalizar(dezenas):
        ordenadas = sorted(int(d) for d in dezenas)
        return "-".join(f"{d:02d}" for d in ordenadas)

    @staticmethod
    def parse_data(texto):
        texto = texto.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
                    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(texto, fmt).date().isoformat()
            except ValueError:
                pass
        raise ValueError("Data inválida: " + texto)

    def salvar_concurso(self, loteria_id, numero, data, dezenas):
        key = self.normalizar(dezenas)
        cols = ", ".join(f"D{i+1}" for i in range(len(dezenas)))
        vals = ", ".join("?" for _ in dezenas)
        sql = (f"INSERT INTO Concursos (LoteriaId, NumeroConcurso, DataSorteio, "
               f"DezenasKey, {cols}) VALUES (?,?,?,?,{vals})")
        try:
            self._conn.execute(
                sql, [loteria_id, numero, data, key] + [int(d) for d in dezenas])
            self._conn.commit()
            return True, "Sorteio cadastrado com sucesso!"
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False, f"Concurso {numero} já existe para esta loteria."

    def importar_csv(self, caminho, loteria_id, qtd):
        inseridos, erros = 0, []
        # 1) Detecta a codificação do arquivo
        with open(caminho, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            # salvo como Unicode (Excel)
            conteudo = raw.decode("utf-16")
        else:
            try:
                conteudo = raw.decode("utf-8-sig")   # UTF-8 (com ou sem BOM)
            except UnicodeDecodeError:
                conteudo = raw.decode("latin-1")     # fallback Latin-1
        # 2) Detecta o separador: ; , ou TAB (arquivos salvos pelo Excel)
        primeira = conteudo.splitlines()[0] if conteudo.splitlines() else ""
        n_pv, n_virgula, n_tab = primeira.count(
            ";"), primeira.count(","), primeira.count("\t")
        if n_pv >= n_virgula and n_pv >= n_tab and n_pv > 0:
            sep = ";"
        elif n_virgula >= n_tab and n_virgula > 0:
            sep = ","
        elif n_tab > 0:
            sep = "\t"
        else:
            sep = ";"
        linhas = list(csv.reader(conteudo.splitlines(), delimiter=sep))
        if not linhas:
            return 0, ["Arquivo vazio."]
        # 3) Normaliza o cabeçalho (remove BOM, aspas e espaços)

        def limpar(nome):
            return nome.strip().strip('"').strip("'").lstrip("\ufeff").lower()
        idx = {limpar(nome): i for i, nome in enumerate(linhas[0])}

        def col(*nomes):
            for n in nomes:
                if n in idx:
                    return idx[n]
            return None

        i_conc = col("concurso", "numero", "numero_concurso", "sorteio", "n")
        i_dat = col("data", "data_sorteio", "data_sorteada", "dt", "date")
        i_d1 = col("d1", "dezena1", "bola1", "bola_1", "b1", "dezena_1")
        if i_conc is None or i_dat is None or i_d1 is None:
            # 4) Fallback posicional: col0=concurso, col1=data, col2..=dezenas
            if len(linhas[0]) >= qtd + 2:
                i_conc, i_dat, i_d1 = 0, 1, 2
            else:
                return 0, ["Cabeçalho não reconhecido. Confira o separador do arquivo."]

        for n, linha in enumerate(linhas[1:], 2):
            if not linha or not linha[0].strip():
                continue
            try:
                dezenas = [int(x) for x in linha[i_d1:i_d1 + qtd]]
                if len(dezenas) != qtd:
                    erros.append(
                        f"Linha {n}: esperava {qtd} dezenas, achou {len(dezenas)}")
                    continue
                numero = int(
                    float(str(linha[i_conc]).strip().replace(",", ".")))
                ok, msg = self.salvar_concurso(loteria_id, numero,
                                               self.parse_data(linha[i_dat]), dezenas)
                if ok:
                    inseridos += 1
                else:
                    erros.append(f"Linha {n}: {msg}")
            except Exception as e:
                erros.append(f"Linha {n}: {e}")
        return inseridos, erros

    def consultar_sequencia(self, loteria_id, dezenas):
        rows = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos "
            "WHERE LoteriaId = ? AND DezenasKey = ? ORDER BY NumeroConcurso",
            (loteria_id, self.normalizar(dezenas)),
        ).fetchall()
        return [dict(r) for r in rows]

    def listar_concursos(self, loteria_id, limite=200):
        rows = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos "
            "WHERE LoteriaId = ? ORDER BY NumeroConcurso DESC LIMIT ?",
            (loteria_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]

    def estatisticas(self, loteria_id):
        rows = self._conn.execute(
            "SELECT DezenasKey FROM Concursos WHERE LoteriaId = ?",
            (loteria_id,),
        ).fetchall()
        if not rows:
            return None
        total = len(rows)
        contador = Counter()
        for r in rows:
            for d in r["DezenasKey"].split("-"):
                contador[int(d)] += 1
        pares = sorted(contador.items(), key=lambda x: (-x[1], x[0]))
        n = len(pares)
        corte_frio = n // 4
        corte_quente = n - n // 4
        classificacao = []
        for i, (dezena, count) in enumerate(pares):
            if i >= corte_quente:
                classe = "quente"
            elif i < corte_frio:
                classe = "frio"
            else:
                classe = "morno"
            classificacao.append((dezena, count, classe))
        frequencia = [(dezena, count, round(count / total * 100, 1))
                      for dezena, count in pares]
        return {
            "total": total,
            "frequencia": frequencia,
            "classificacao": classificacao,
            "corte_frio": corte_frio,
            "corte_quente": corte_quente,
        }

    def atraso_dezenas(self, loteria_id, min_num, max_num):
        """Calcula há quantos concursos cada dezena não aparece.

        Atraso = último concurso registrado - último concurso em que a dezena saiu.
        Dezena que nunca saiu: atraso = total de concursos (marcada como 'nunca').
        """
        rows = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos "
            "WHERE LoteriaId = ? ORDER BY NumeroConcurso ASC",
            (loteria_id,),
        ).fetchall()
        if not rows:
            return None
        total = len(rows)
        ultimo_concurso = rows[-1]["NumeroConcurso"]
        ultima_data = rows[-1]["DataSorteio"]
        ultima_aparicao = {}
        for r in rows:
            for d in r["DezenasKey"].split("-"):
                ultima_aparicao[int(d)] = (
                    r["NumeroConcurso"], r["DataSorteio"])
        linhas = []
        for dezena in range(min_num, max_num + 1):
            if dezena in ultima_aparicao:
                conc, data = ultima_aparicao[dezena]
                linhas.append({"dezena": dezena, "ultimo_concurso": conc,
                               "ultima_data": data, "atraso": ultimo_concurso - conc,
                               "nunca": False})
            else:
                linhas.append({"dezena": dezena, "ultimo_concurso": None,
                               "ultima_data": None, "atraso": total, "nunca": True})
        linhas.sort(key=lambda x: (-x["atraso"], x["dezena"]))
        return {"total": total, "ultimo_concurso": ultimo_concurso,
                "ultima_data": ultima_data, "linhas": linhas}

    def similaridade(self, loteria_id, dezenas):
        """Compara a aposta com todo o histórico e retorna o Top 10 por interseção."""
        aposta = set(int(d) for d in dezenas)
        rows = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos WHERE LoteriaId = ?",
            (loteria_id,),
        ).fetchall()
        resultados = []
        for r in rows:
            conc = set(int(d) for d in r["DezenasKey"].split("-"))
            acertadas = sorted(aposta & conc)
            resultados.append({
                "concurso": r["NumeroConcurso"],
                "data": r["DataSorteio"],
                "dezenas_key": r["DezenasKey"],
                "acertos": len(aposta & conc),
                "acertadas": "-".join(f"{d:02d}" for d in acertadas) if acertadas else "—",
            })
        resultados.sort(key=lambda x: (-x["acertos"], -x["concurso"]))
        return resultados[:10]

    def fechar(self):
        try:
            self._conn.close()
        except Exception:
            pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("Loteria Manager")
        root.configure(bg=CORES["bg"])
        root.protocol("WM_DELETE_WINDOW", self._sair)

        self._estilo()
        self.db = Database()
        self.loterias = self.db.listar_loterias()
        self.lot = self.loterias[0]

        self._montar_ui()
        self._atualizar_historico()
        self._atualizar_estatisticas()
        self._atualizar_atraso()

        centralizar_janela(root, 960, 680)
        root.minsize(840, 580)

    def _estilo(self):
        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", background=CORES["bg"], foreground=CORES["texto"],
                     fieldbackground=CORES["card2"], bordercolor=CORES["borda"])
        st.configure("TFrame", background=CORES["bg"])
        st.configure("Card.TFrame", background=CORES["card"])
        st.configure("TLabel", background=CORES["bg"], foreground=CORES["texto"], font=(
            "Segoe UI", 10))
        st.configure("Card.TLabel", background=CORES["card"], foreground=CORES["texto"], font=(
            "Segoe UI", 10))
        st.configure("Title.TLabel", background=CORES["bg"], foreground=CORES["texto"],
                     font=("Segoe UI", 16, "bold"))
        st.configure("Sub.TLabel", background=CORES["bg"], foreground=CORES["texto2"],
                     font=("Segoe UI", 9))
        st.configure("TEntry", fieldbackground=CORES["card2"], foreground=CORES["texto"],
                     insertcolor=CORES["texto"], bordercolor=CORES["borda"], padding=6)
        st.configure("TCombobox", fieldbackground=CORES["card2"], foreground=CORES["texto"],
                     arrowcolor=CORES["texto"], bordercolor=CORES["borda"])
        st.map("TCombobox", fieldbackground=[("readonly", CORES["card2"])],
               foreground=[("readonly", CORES["texto"])])
        st.configure("TNotebook", background=CORES["bg"], borderwidth=0)
        st.configure("TNotebook.Tab", background=CORES["card"], foreground=CORES["texto2"],
                     padding=(22, 9), font=("Segoe UI", 10, "bold"), borderwidth=0)
        st.map("TNotebook.Tab",
               background=[("selected", CORES["destaque"]),
                           ("active", CORES["card2"])],
               foreground=[("selected", "#ffffff"), ("active", CORES["texto"])])
        st.configure("Treeview", background=CORES["card"], fieldbackground=CORES["card"],
                     foreground=CORES["texto"], bordercolor=CORES["borda"], rowheight=28)
        st.configure("Treeview.Heading", background=CORES["card2"], foreground=CORES["texto"],
                     font=("Segoe UI", 10, "bold"), bordercolor=CORES["borda"])
        st.map("Treeview", background=[("selected", CORES["selecao"])],
               foreground=[("selected", "#ffffff")])
        st.configure("TButton", background=CORES["destaque"], foreground="#ffffff",
                     font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=0)
        st.map("TButton", background=[("active", CORES["destaque2"]),
                                      ("pressed", CORES["destaque2"])])
        st.configure("Destaque.TButton", background=CORES["verde"])
        st.map("Destaque.TButton", background=[("active", CORES["verde2"]),
                                               ("pressed", CORES["verde2"])])

    def _montar_ui(self):
        cab = ttk.Frame(self.root, padding=(20, 14, 20, 6))
        cab.pack(fill="x")
        ttk.Label(cab, text="🎯 Loteria Manager",
                  style="Title.TLabel").pack(side="left")
        ttk.Label(cab, text="Registre, consulte e analise sorteios", style="Sub.TLabel").pack(
            side="left", padx=(12, 0), pady=(6, 0))

        barra = ttk.Frame(self.root, padding=(20, 4, 20, 8))
        barra.pack(fill="x")
        ttk.Label(barra, text="Loteria:", style="TLabel").pack(side="left")
        self.cmb = ttk.Combobox(barra, values=[l["Nome"] for l in self.loterias],
                                state="readonly", width=18)
        self.cmb.current(0)
        self.cmb.pack(side="left", padx=8)
        self.cmb.bind("<<ComboboxSelected>>", self._trocar_loteria)
        ttk.Button(barra, text="⬆ Importar CSV",
                   command=self._importar_csv).pack(side="right")

        self.ab = ttk.Notebook(self.root)
        self.ab.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.tab_cadastro = ttk.Frame(self.ab)
        self.tab_consulta = ttk.Frame(self.ab)
        self.tab_historico = ttk.Frame(self.ab)
        self.tab_estatisticas = ttk.Frame(self.ab)
        self.tab_atraso = ttk.Frame(self.ab)
        self.tab_alerta = ttk.Frame(self.ab)
        self.ab.add(self.tab_cadastro, text="  Cadastrar Sorteio  ")
        self.ab.add(self.tab_consulta, text="  Consultar Sequência  ")
        self.ab.add(self.tab_historico, text="  Histórico  ")
        self.ab.add(self.tab_estatisticas, text="  Estatísticas  ")
        self.ab.add(self.tab_atraso, text="  Atraso  ")
        self.ab.add(self.tab_alerta, text="  Alerta  ")

        self._montar_cadastro()
        self._montar_consulta()
        self._montar_historico()
        self._montar_estatisticas()
        self._montar_atraso()
        self._montar_alerta()

    def _grade(self, container):
        for w in container.winfo_children():
            w.destroy()
        entradas, linha = [], None
        qtd = self.lot["QtdDezenas"]
        por_linha = qtd if qtd <= 10 else 5
        for i in range(qtd):
            if i % por_linha == 0:
                linha = ttk.Frame(container)
                linha.pack(fill="x", pady=4)
            ent = ttk.Entry(linha, width=5, justify="center",
                            font=("Segoe UI", 12, "bold"))
            ent.pack(side="left", padx=4)
            entradas.append(ent)
        return entradas

    def _montar_cadastro(self):
        box = ttk.Frame(self.tab_cadastro, style="Card.TFrame", padding=20)
        box.pack(fill="x", padx=16, pady=16)
        ttk.Label(box, text="Dados do Sorteio", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        l1 = ttk.Frame(box, style="Card.TFrame")
        l1.pack(fill="x", pady=4)
        ttk.Label(l1, text="Nº do Concurso:",
                  style="Card.TLabel").pack(side="left")
        self.ent_num = ttk.Entry(l1, width=10)
        self.ent_num.pack(side="left", padx=8)
        ttk.Label(l1, text="Data (dd/mm/aaaa):",
                  style="Card.TLabel").pack(side="left", padx=(24, 8))
        self.ent_data = ttk.Entry(l1, width=12)
        self.ent_data.pack(side="left")
        ttk.Label(box, text="Dezenas sorteadas:", style="Card.TLabel").pack(
            anchor="w", pady=(16, 6))
        self.box_dezenas = ttk.Frame(box, style="Card.TFrame")
        self.box_dezenas.pack(fill="x")
        self.ent_dezenas = self._grade(self.box_dezenas)
        ttk.Button(box, text="💾 Salvar Sorteio", style="Destaque.TButton",
                   command=self._salvar).pack(anchor="w", pady=(20, 0))

    def _montar_consulta(self):
        box = ttk.Frame(self.tab_consulta, style="Card.TFrame", padding=20)
        box.pack(fill="x", padx=16, pady=16)
        ttk.Label(box, text="Verificar se uma sequência já foi sorteada",
                  style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Label(box, text="Digite as dezenas (a ordem não importa):",
                  style="Card.TLabel").pack(anchor="w", pady=(0, 8))
        self.box_consulta = ttk.Frame(box, style="Card.TFrame")
        self.box_consulta.pack(fill="x")
        self.ent_consulta = self._grade(self.box_consulta)
        ttk.Button(box, text="🔍 Verificar Sequência", command=self._verificar).pack(
            anchor="w", pady=(16, 10))
        self.lbl_res = ttk.Label(box, text="", style="Card.TLabel",
                                 font=("Segoe UI", 10, "bold"))
        self.lbl_res.pack(anchor="w")

    def _montar_historico(self):
        cols = ("concurso", "data", "dezenas")
        self.tree = ttk.Treeview(
            self.tab_historico, columns=cols, show="headings")
        for col, txt, w in (("concurso", "Concurso", 100), ("data", "Data", 120),
                            ("dezenas", "Dezenas", 460)):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        sb = ttk.Scrollbar(self.tab_historico,
                           orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both",
                       expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16)

    def _montar_estatisticas(self):
        f = self.tab_estatisticas
        self.lbl_est_resumo = ttk.Label(
            f, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_est_resumo.pack(anchor="w", padx=16, pady=(14, 6))
        corpo = ttk.Frame(f)
        corpo.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        box_freq = ttk.LabelFrame(corpo, text="  Frequência das dezenas  ")
        box_freq.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.tree_freq = ttk.Treeview(box_freq, columns=("pos", "dezena", "vezes", "pct"),
                                      show="headings", height=18)
        for col, txt, w in (("pos", "Pos", 60), ("dezena", "Dezena", 90),
                            ("vezes", "Vezes", 90), ("pct", "% Sorteios", 120)):
            self.tree_freq.heading(col, text=txt)
            self.tree_freq.column(col, width=w, anchor="center")
        sb1 = ttk.Scrollbar(box_freq, orient="vertical",
                            command=self.tree_freq.yview)
        self.tree_freq.configure(yscrollcommand=sb1.set)
        self.tree_freq.pack(side="left", fill="both",
                            expand=True, padx=(8, 0), pady=8)
        sb1.pack(side="right", fill="y", pady=8)
        box_clas = ttk.LabelFrame(
            corpo, text="  Quentes vs Frias (percentil)  ")
        box_clas.pack(side="left", fill="both", expand=True, padx=(8, 0))
        ttk.Label(box_clas,
                  text="Top 25% = 🔥 quentes  |  meio = 🌤️ mornas  |  últimos 25% = ❄️ frias",
                  font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(8, 2))
        self.tree_clas = ttk.Treeview(box_clas, columns=("dezena", "vezes", "classe"),
                                      show="headings", height=18)
        for col, txt, w in (("dezena", "Dezena", 90), ("vezes", "Vezes", 80),
                            ("classe", "Classificação", 200)):
            self.tree_clas.heading(col, text=txt)
            self.tree_clas.column(col, width=w, anchor="center")
        self.tree_clas.column("classe", anchor="w")
        self.tree_clas.tag_configure(
            "t_quente", background=CORES["quente"], foreground="#ffffff")
        self.tree_clas.tag_configure(
            "t_morno", background=CORES["card"], foreground=CORES["texto"])
        self.tree_clas.tag_configure(
            "t_frio", background=CORES["frio"], foreground="#ffffff")
        sb2 = ttk.Scrollbar(box_clas, orient="vertical",
                            command=self.tree_clas.yview)
        self.tree_clas.configure(yscrollcommand=sb2.set)
        self.tree_clas.pack(side="left", fill="both",
                            expand=True, padx=(8, 0), pady=8)
        sb2.pack(side="right", fill="y", pady=8)

    def _montar_atraso(self):
        f = self.tab_atraso
        self.lbl_atraso_resumo = ttk.Label(
            f, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_atraso_resumo.pack(anchor="w", padx=16, pady=(14, 6))
        cols = ("dezena", "ultimo", "atraso")
        self.tree_atraso = ttk.Treeview(f, columns=cols, show="headings")
        for col, txt, w in (("dezena", "Dezena", 130), ("ultimo", "Última saída", 300),
                            ("atraso", "Atraso (concursos)", 220)):
            self.tree_atraso.heading(col, text=txt)
            self.tree_atraso.column(col, width=w, anchor="center")
        self.tree_atraso.column("ultimo", anchor="w")
        self.tree_atraso.tag_configure("top_atraso", background=CORES["atraso_top"],
                                       foreground="#ffb3b3")
        sb = ttk.Scrollbar(f, orient="vertical",
                           command=self.tree_atraso.yview)
        self.tree_atraso.configure(yscrollcommand=sb.set)
        self.tree_atraso.pack(side="left", fill="both",
                              expand=True, padx=(16, 0), pady=16)
        sb.pack(side="right", fill="y", pady=16)

    def _montar_alerta(self):
        f = self.tab_alerta
        box = ttk.Frame(f, style="Card.TFrame", padding=20)
        box.pack(fill="x", padx=16, pady=16)
        ttk.Label(box, text="🎯 Alerta de Similaridade", style="Card.TLabel",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(box,
                  text="Digite a sua aposta e veja os concursos históricos que mais se aproximaram dela. "
                       "Análise descritiva (não previsão): mostra o que já aconteceu na base.",
                  style="Card.TLabel", wraplength=820).pack(anchor="w", pady=(0, 10))
        self.box_alerta = ttk.Frame(box, style="Card.TFrame")
        self.box_alerta.pack(fill="x")
        self.ent_alerta = self._grade(self.box_alerta)
        self.lbl_alerta_resumo = ttk.Label(box, text="", style="Card.TLabel",
                                           font=("Segoe UI", 10, "bold"))
        self.lbl_alerta_resumo.pack(anchor="w", pady=(10, 6))
        ttk.Button(box, text="🔍 Comparar Aposta", command=self._analisar_aposta).pack(
            anchor="w", pady=(0, 6))

        cols = ("concurso", "data", "dezenas", "acertos", "acertadas")
        self.tree_alerta = ttk.Treeview(
            f, columns=cols, show="headings", height=12)
        for col, txt, w in (("concurso", "Concurso", 90), ("data", "Data", 110),
                            ("dezenas", "Dezenas do Concurso", 300),
                            ("acertos", "Acertos", 80),
                            ("acertadas", "Dezenas em Comum", 280)):
            self.tree_alerta.heading(col, text=txt)
            self.tree_alerta.column(col, width=w, anchor="center")
        self.tree_alerta.column("dezenas", anchor="w")
        self.tree_alerta.column("acertadas", anchor="w")
        self.tree_alerta.tag_configure(
            "melhor", background="#1f3d2b", foreground="#7dffb0")
        sb = ttk.Scrollbar(f, orient="vertical",
                           command=self.tree_alerta.yview)
        self.tree_alerta.configure(yscrollcommand=sb.set)
        self.tree_alerta.pack(side="left", fill="both",
                              expand=True, padx=(16, 0), pady=(0, 16))
        sb.pack(side="right", fill="y", pady=(0, 16))

    def _trocar_loteria(self, _e=None):
        nome = self.cmb.get()
        self.lot = next(l for l in self.loterias if l["Nome"] == nome)
        self.ent_dezenas = self._grade(self.box_dezenas)
        self.ent_consulta = self._grade(self.box_consulta)
        self.ent_alerta = self._grade(self.box_alerta)
        self._atualizar_historico()
        self._atualizar_estatisticas()
        self._atualizar_atraso()

    def _salvar(self):
        try:
            numero = int(self.ent_num.get().strip())
            data = self.db.parse_data(self.ent_data.get().strip())
            dezenas = [int(e.get().strip()) for e in self.ent_dezenas]
        except ValueError as ex:
            messagebox.showerror("Erro", f"Valores inválidos: {ex}")
            return
        qtd, mn, mx = self.lot["QtdDezenas"], self.lot["MinNumero"], self.lot["MaxNumero"]
        if len(dezenas) != qtd:
            messagebox.showerror("Erro", f"Informe exatamente {qtd} dezenas.")
            return
        if len(set(dezenas)) != qtd:
            messagebox.showerror("Erro", "Existem dezenas repetidas.")
            return
        if not all(mn <= d <= mx for d in dezenas):
            messagebox.showerror(
                "Erro", f"As dezenas devem estar entre {mn} e {mx}.")
            return
        ok, msg = self.db.salvar_concurso(
            self.lot["Id"], numero, data, dezenas)
        if ok:
            messagebox.showinfo("Sucesso", msg)
            for e in self.ent_dezenas:
                e.delete(0, "end")
            self.ent_num.delete(0, "end")
            self.ent_data.delete(0, "end")
            self.ent_num.focus_set()
            self._atualizar_historico()
            self._atualizar_estatisticas()
            self._atualizar_atraso()
        else:
            messagebox.showwarning("Atenção", msg)

    def _verificar(self):
        try:
            dezenas = [int(e.get().strip()) for e in self.ent_consulta]
        except ValueError:
            messagebox.showerror(
                "Erro", "Preencha todos os números corretamente.")
            return
        qtd = self.lot["QtdDezenas"]
        if len(dezenas) != qtd or len(set(dezenas)) != qtd:
            messagebox.showerror("Erro", f"Informe {qtd} números distintos.")
            return
        res = self.db.consultar_sequencia(self.lot["Id"], dezenas)
        if res:
            texto = f"✅ JÁ FOI sorteada {len(res)} vez(es):\n"
            for r in res[:10]:
                texto += f"  • Concurso {r['NumeroConcurso']} em {self._fmt(r['DataSorteio'])} ({r['DezenasKey']})\n"
            if len(res) > 10:
                texto += f"  ... mais {len(res) - 10} ocorrência(s)."
            self.lbl_res.config(text=texto, foreground=CORES["verde"])
        else:
            self.lbl_res.config(text="❌ NUNCA foi sorteada nesta loteria.",
                                foreground=CORES["vermelho"])

    def _importar_csv(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo CSV",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            inseridos, erros = self.db.importar_csv(
                caminho, self.lot["Id"], self.lot["QtdDezenas"])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na importação:\n{e}")
            return
        msg = f"Importação concluída: {inseridos} sorteio(s) inserido(s)."
        if erros:
            msg += f"\n\n{len(erros)} erro(s):\n" + "\n".join(erros[:15])
        messagebox.showinfo("Resultado", msg)
        self._atualizar_historico()
        self._atualizar_estatisticas()
        self._atualizar_atraso()

    def _fmt(self, iso):
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(iso)

    def _atualizar_historico(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in self.db.listar_concursos(self.lot["Id"]):
            self.tree.insert("", "end",
                             values=(r["NumeroConcurso"], self._fmt(r["DataSorteio"]), r["DezenasKey"]))

    def _atualizar_estatisticas(self):
        for w in (self.tree_freq, self.tree_clas):
            for item in w.get_children():
                w.delete(item)
        res = self.db.estatisticas(self.lot["Id"])
        if not res or res["total"] == 0:
            self.lbl_est_resumo.config(
                text="📭 Nenhum sorteio cadastrado ainda para esta loteria.")
            return
        self.lbl_est_resumo.config(
            text=f"📈 {res['total']} concursos analisados — {self.lot['Nome']} (histórico completo)")
        for i, (dezena, vezes, pct) in enumerate(res["frequencia"], 1):
            self.tree_freq.insert("", "end", values=(
                i, f"{dezena:02d}", vezes, f"{pct}%"))
        rotulos = {"quente": "🔥 Quente (top 25%)",
                   "morno": "🌤️ Morna (meio)",
                   "frio": "❄️ Fria (últimos 25%)"}
        for dezena, vezes, classe in res["classificacao"]:
            self.tree_clas.insert("", "end",
                                  values=(f"{dezena:02d}", vezes,
                                          rotulos[classe]),
                                  tags=(f"t_{classe}",))

    def _atualizar_atraso(self):
        for item in self.tree_atraso.get_children():
            self.tree_atraso.delete(item)
        res = self.db.atraso_dezenas(
            self.lot["Id"], self.lot["MinNumero"], self.lot["MaxNumero"])
        if not res:
            self.lbl_atraso_resumo.config(
                text="📭 Nenhum sorteio cadastrado para esta loteria.")
            return
        top = ", ".join(f"{l['dezena']:02d}" for l in res["linhas"][:5])
        self.lbl_atraso_resumo.config(
            text=f"📅 {res['total']} concursos · último: {res['ultimo_concurso']} "
            f"({self._fmt(res['ultima_data'])}) · mais atrasadas: {top}")
        for i, linha in enumerate(res["linhas"]):
            if linha["nunca"]:
                ultimo = "Nunca saiu"
                atraso = f"desde o início ({linha['atraso']} concursos)"
            else:
                ultimo = f"Concurso {linha['ultimo_concurso']} ({self._fmt(linha['ultima_data'])})"
                atraso = f"{linha['atraso']}"
            tags = ("top_atraso",) if i < 5 else ()
            self.tree_atraso.insert("", "end",
                                    values=(
                                        f"{linha['dezena']:02d}", ultimo, atraso),
                                    tags=tags)

    def _analisar_aposta(self):
        try:
            dezenas = [int(e.get().strip()) for e in self.ent_alerta]
        except ValueError:
            messagebox.showerror(
                "Erro", "Preencha todos os números corretamente.")
            return
        qtd, mn, mx = self.lot["QtdDezenas"], self.lot["MinNumero"], self.lot["MaxNumero"]
        if len(dezenas) != qtd:
            messagebox.showerror("Erro", f"Informe exatamente {qtd} números.")
            return
        if len(set(dezenas)) != qtd:
            messagebox.showerror(
                "Erro", "Existem números repetidos na aposta.")
            return
        if not all(mn <= d <= mx for d in dezenas):
            messagebox.showerror(
                "Erro", f"Os números devem estar entre {mn} e {mx}.")
            return
        resultado = self.db.similaridade(self.lot["Id"], dezenas)
        for item in self.tree_alerta.get_children():
            self.tree_alerta.delete(item)
        if not resultado:
            self.lbl_alerta_resumo.config(
                text="📭 Nenhum concurso no histórico ainda para comparar.")
            return
        aposta_txt = " · ".join(f"{d:02d}" for d in sorted(dezenas))
        melhor = resultado[0]
        self.lbl_alerta_resumo.config(
            text=f"Sua aposta: {aposta_txt}  →  melhor similaridade: "
            f"{melhor['acertos']}/{qtd} acertos no concurso {melhor['concurso']}")
        for i, r in enumerate(resultado):
            tags = ("melhor",) if i == 0 else ()
            self.tree_alerta.insert("", "end", values=(
                r["concurso"], self._fmt(r["data"]), r["dezenas_key"],
                f"{r['acertos']}/{qtd}", r["acertadas"]), tags=tags)

    def _sair(self):
        self.db.fechar()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
