# ============================================================
#  LOTERIA APP - Python + CustomTkinter + SQLite (v12.1)
#  Cadastro, consulta, estatísticas, atraso, alerta,
#  gerador, meus jogos, estatísticas da sequência,
#  auto-avanço de campos, copiar entre Consulta/Alerta
#  e ACERTOS NO ÚLTIMO CONCURSO na aba Consulta
#  Banco: arquivo loteria.db (criado automaticamente)
# ============================================================

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import sqlite3
import csv
import os
import random
from collections import Counter
from datetime import datetime

# ---------- Configuração global do CustomTkinter ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loteria.db")

LOTERIAS_PADRAO = [
    ("Lotofácil", 15, 1, 25),
    ("Mega-Sena", 6, 1, 60),
]

# Estratégias do Gerador (rótulo -> chave)
ESTRATEGIAS = {
    "Equilibrado (padrão)": "equilibrado",
    "Ponderado por frequência": "ponderado",
    "Puro aleatório": "puro",
}

COLUNAS_D = ", ".join(f"D{i} INTEGER" for i in range(1, 21))

# ---------- Paleta de cores ----------
CORES = {
    "bg": "#14141f",
    "card": "#1f1f2e",
    "card2": "#2a2a3d",
    "borda": "#33334a",
    "texto": "#e8e8f2",
    "texto2": "#9a9ab0",
    "destaque": "#6c5ce7",
    "destaque2": "#5a4bd1",
    "verde": "#00b894",
    "verde2": "#00997c",
    "vermelho": "#e0534f",
    "quente": "#8a4a38",
    "frio": "#3d4f73",
    "melhor": "#1f3d2b",
    "top_atraso": "#5a2020",
    "header": "#26263a",
}

def centralizar_janela(janela, largura, altura):
    janela.update_idletasks()
    x = (janela.winfo_screenwidth() - largura) // 2
    y = (janela.winfo_screenheight() - altura) // 2
    janela.geometry(f"{largura}x{altura}+{x}+{y}")

class TabelaCTk(ctk.CTkScrollableFrame):
    """Tabela moderna: cabeçalho fixo + linhas roláveis, com cores por linha
    e botão de ação opcional (ex.: excluir)."""

    def __init__(self, master, colunas, larguras, altura_linha=32, alinhamentos=None,
                 btn_texto=None, btn_comando=None):
        super().__init__(master, fg_color="transparent")
        self.colunas = colunas
        self.larguras = larguras
        self.alinhamentos = alinhamentos or ["center"] * len(colunas)
        self.btn_texto = btn_texto
        self.btn_comando = btn_comando

        cab = ctk.CTkFrame(self, fg_color=CORES["header"], corner_radius=8)
        cab.pack(fill="x", pady=(0, 4))
        for col, w, al in zip(colunas, larguras, self.alinhamentos):
            ctk.CTkLabel(cab, text=col, width=w, anchor=al,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=CORES["texto"]).pack(side="left", padx=2, pady=4)
        if btn_texto:
            ctk.CTkLabel(cab, text="Ação", width=80, anchor="center",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=CORES["texto"]).pack(side="left", padx=2, pady=4)

        self.linhas_box = ctk.CTkFrame(self, fg_color="transparent")
        self.linhas_box.pack(fill="x")

    def limpar(self):
        for w in self.linhas_box.winfo_children():
            w.destroy()

    def adicionar(self, valores, fg=None, text_color=None, btn_dado=None):
        linha = ctk.CTkFrame(self.linhas_box,
                             fg_color=fg or CORES["card"],
                             corner_radius=6)
        linha.pack(fill="x", pady=1)
        for val, w, al in zip(valores, self.larguras, self.alinhamentos):
            ctk.CTkLabel(linha, text=str(val), width=w, anchor=al,
                         font=ctk.CTkFont(size=12),
                         text_color=text_color or CORES["texto"]).pack(side="left", padx=2, pady=2)
        if self.btn_texto:
            ctk.CTkButton(linha, text=self.btn_texto, width=74, height=26,
                          fg_color=CORES["vermelho"], hover_color="#a03532",
                          corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
                          command=lambda: self.btn_comando(btn_dado)).pack(side="left", padx=4)

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
        c.execute("""
            CREATE TABLE IF NOT EXISTS Jogos (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                LoteriaId INTEGER NOT NULL,
                DataRegistro TEXT NOT NULL,
                DezenasKey TEXT NOT NULL,
                Observacao TEXT,
                FOREIGN KEY (LoteriaId) REFERENCES Loterias(Id)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS IX_Jogos_Loteria
            ON Jogos (LoteriaId, DezenasKey)
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
            self._conn.execute(sql, [loteria_id, numero, data, key] + [int(d) for d in dezenas])
            self._conn.commit()
            return True, "Sorteio cadastrado com sucesso!"
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return False, f"Concurso {numero} já existe para esta loteria."

    def importar_csv(self, caminho, loteria_id, qtd):
        inseridos, erros = 0, []
        with open(caminho, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            conteudo = raw.decode("utf-16")
        else:
            try:
                conteudo = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                conteudo = raw.decode("latin-1")
        primeira = conteudo.splitlines()[0] if conteudo.splitlines() else ""
        n_pv, n_virgula, n_tab = primeira.count(";"), primeira.count(","), primeira.count("\t")
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
                    erros.append(f"Linha {n}: esperava {qtd} dezenas, achou {len(dezenas)}")
                    continue
                numero = int(float(str(linha[i_conc]).strip().replace(",", ".")))
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

    def estatisticas_sequencia(self, loteria_id, dezenas):
        """Retorna estatísticas (frequência, classe, atraso) APENAS das dezenas informadas."""
        dezenas = sorted(int(d) for d in dezenas)
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
        contador = Counter()
        ultima_aparicao = {}
        for r in rows:
            for d in r["DezenasKey"].split("-"):
                d = int(d)
                contador[d] += 1
                ultima_aparicao[d] = (r["NumeroConcurso"], r["DataSorteio"])
        pares = sorted(contador.items(), key=lambda x: (-x[1], x[0]))
        n = len(pares)
        corte_frio = n // 4
        corte_quente = n - n // 4
        classe_map = {}
        for i, (dezena, count) in enumerate(pares):
            if i >= corte_quente:
                classe_map[dezena] = "quente"
            elif i < corte_frio:
                classe_map[dezena] = "frio"
            else:
                classe_map[dezena] = "morno"
        linhas = []
        for d in dezenas:
            vezes = contador.get(d, 0)
            pct = round(vezes / total * 100, 1) if total else 0
            classe = classe_map.get(d, "morno")
            if d in ultima_aparicao:
                conc, data = ultima_aparicao[d]
                linhas.append({"dezena": d, "vezes": vezes, "pct": pct, "classe": classe,
                               "atraso": ultimo_concurso - conc,
                               "ultimo_concurso": conc, "ultima_data": data, "nunca": False})
            else:
                linhas.append({"dezena": d, "vezes": vezes, "pct": pct, "classe": classe,
                               "atraso": total, "ultimo_concurso": None,
                               "ultima_data": None, "nunca": True})
        return {"total": total, "ultimo_concurso": ultimo_concurso,
                "ultima_data": ultima_data, "linhas": linhas}

    def listar_concursos(self, loteria_id, limite=200):
        rows = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos "
            "WHERE LoteriaId = ? ORDER BY NumeroConcurso DESC LIMIT ?",
            (loteria_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]

    def ultimo_concurso(self, loteria_id):
        row = self._conn.execute(
            "SELECT NumeroConcurso, DataSorteio, DezenasKey FROM Concursos "
            "WHERE LoteriaId = ? ORDER BY NumeroConcurso DESC LIMIT 1",
            (loteria_id,),
        ).fetchone()
        return dict(row) if row else None

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
        frequencia = [(dezena, count, round(count / total * 100, 1)) for dezena, count in pares]
        return {
            "total": total,
            "frequencia": frequencia,
            "classificacao": classificacao,
        }

    def atraso_dezenas(self, loteria_id, min_num, max_num):
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
                ultima_aparicao[int(d)] = (r["NumeroConcurso"], r["DataSorteio"])
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

    def gerar_jogos(self, loteria_id, quantidade, estrategia):
        """Gera jogos — análise descritiva, NÃO previsão.

        'equilibrado': mistura quente/morno/frio + tenta soma central e par/ímpar.
        'ponderado'  : sorteio com peso = frequência histórica.
        'puro'       : quick pick 100% aleatório (controle).
        """
        lot = self._conn.execute(
            "SELECT QtdDezenas, MinNumero, MaxNumero FROM Loterias WHERE Id = ?",
            (loteria_id,),
        ).fetchone()
        if not lot:
            return []
        qtd = lot["QtdDezenas"]
        mn, mx = lot["MinNumero"], lot["MaxNumero"]
        todas = list(range(mn, mx + 1))

        rows = self._conn.execute(
            "SELECT DezenasKey FROM Concursos WHERE LoteriaId = ?",
            (loteria_id,),
        ).fetchall()
        sorteadas = {r["DezenasKey"] for r in rows}

        freq = {d: {"vezes": 0, "classe": "morno"} for d in todas}
        quentes, mornas, frias = [], [], []
        if rows:
            contador = Counter()
            for r in rows:
                for d in r["DezenasKey"].split("-"):
                    contador[int(d)] += 1
            pares = sorted(contador.items(), key=lambda x: (-x[1], x[0]))
            n = len(pares)
            corte_frio = max(1, n // 4)
            corte_quente = n - max(1, n // 4)
            for i, (dezena, count) in enumerate(pares):
                if i >= corte_quente:
                    classe = "quente"
                elif i < corte_frio:
                    classe = "frio"
                else:
                    classe = "morno"
                freq[dezena] = {"vezes": count, "classe": classe}
            quentes = [d for d, v in freq.items() if v["classe"] == "quente"]
            mornas = [d for d, v in freq.items() if v["classe"] == "morno"]
            frias = [d for d, v in freq.items() if v["classe"] == "frio"]

        alvo_soma = (mn + mx) / 2 * qtd
        alvo_par = qtd // 2

        def sorteio_ponderado(pool, pesos, k):
            pool, pesos = pool[:], pesos[:]
            escolhidos = []
            for _ in range(k):
                if not pool:
                    break
                total = sum(pesos)
                alvo = random.uniform(0, total)
                acum = 0
                for i in range(len(pool)):
                    acum += pesos[i]
                    if acum >= alvo:
                        escolhidos.append(pool[i])
                        pool.pop(i)
                        pesos.pop(i)
                        break
            return escolhidos

        def montar_jogo():
            """Monta um jogo seguindo a estratégia (sem filtros rígidos)."""
            if estrategia == "puro" or not rows:
                return sorted(random.sample(todas, qtd))
            if estrategia == "ponderado":
                pesos = [max(freq[d]["vezes"], 1) for d in todas]
                return sorted(sorteio_ponderado(todas, pesos, qtd))
            n_q = min(max(1, round(qtd * 0.4)), len(quentes)) if quentes else 0
            n_f = min(max(1, round(qtd * 0.3)), len(frias)) if frias else 0
            if n_q + n_f > qtd:
                n_q = max(1, qtd // 3)
                n_f = max(1, qtd // 4)
            n_m = max(0, qtd - n_q - n_f)
            jogo = []
            if quentes and n_q:
                jogo += random.sample(quentes, n_q)
            if frias and n_f:
                jogo += random.sample(frias, n_f)
            usadas = set(jogo)
            pool = [d for d in (mornas + quentes + frias) if d not in usadas]
            random.shuffle(pool)
            jogo = jogo + pool[:n_m]
            if len(jogo) < qtd:
                faltam = [d for d in todas if d not in set(jogo)]
                random.shuffle(faltam)
                jogo = jogo + faltam[:qtd - len(jogo)]
            return jogo

        def corrigir_perfil(jogo, tentativas=150):
            """Ajusta soma e paridade SEM descartar o jogo."""
            jogo = list(jogo)
            meio = (mn + mx) / 2
            for _ in range(tentativas):
                soma = sum(jogo)
                pares_n = sum(1 for x in jogo if x % 2 == 0)
                if abs(soma - alvo_soma) <= 0.08 * alvo_soma and \
                   abs(pares_n - alvo_par) <= 1:
                    return sorted(jogo)
                usados = set(jogo)
                candidatos = [x for x in todas if x not in usados]
                if not candidatos:
                    return sorted(jogo)
                if abs(pares_n - alvo_par) > 1:
                    if pares_n > alvo_par:
                        idxs = [i for i, x in enumerate(jogo) if x % 2 == 0]
                        cand = [x for x in candidatos if x % 2 == 1]
                    else:
                        idxs = [i for i, x in enumerate(jogo) if x % 2 == 1]
                        cand = [x for x in candidatos if x % 2 == 0]
                else:
                    if sum(jogo) > alvo_soma:
                        idxs = [i for i, x in enumerate(jogo) if x > meio]
                        cand = [x for x in candidatos if x < meio]
                    else:
                        idxs = [i for i, x in enumerate(jogo) if x < meio]
                        cand = [x for x in candidatos if x > meio]
                if not idxs or not cand:
                    return sorted(jogo)
                jogo[random.choice(idxs)] = random.choice(cand)
            return sorted(jogo)

        jogos = []
        chaves = set()
        tentativas = 0
        while len(jogos) < quantidade and tentativas < 800:
            tentativas += 1
            bruto = montar_jogo()
            if len(set(bruto)) != qtd:
                continue
            if estrategia == "puro":
                jogo = sorted(bruto)
            else:
                jogo = corrigir_perfil(bruto)
            if len(set(jogo)) != qtd:
                jogo = bruto
            key = self.normalizar(jogo)
            if key in chaves:
                continue
            if key in sorteadas and len(sorteadas) < 100000:
                continue
            chaves.add(key)
            q, m, f = 0, 0, 0
            for d in jogo:
                classe = freq[d]["classe"]
                if classe == "quente":
                    q += 1
                elif classe == "frio":
                    f += 1
                else:
                    m += 1
            jogos.append({"jogo": jogo, "key": key, "quentes": q,
                          "mornas": m, "frias": f})

        while len(jogos) < quantidade:
            jogo = sorted(random.sample(todas, qtd))
            key = self.normalizar(jogo)
            if key in chaves:
                continue
            chaves.add(key)
            q = sum(1 for d in jogo if freq[d]["classe"] == "quente")
            f = sum(1 for d in jogo if freq[d]["classe"] == "frio")
            jogos.append({"jogo": jogo, "key": key, "quentes": q,
                          "mornas": qtd - q - f, "frias": f})
        return jogos[:quantidade]

    # ---------- Meus Jogos ----------
    def salvar_jogo(self, loteria_id, dezenas, observacao=""):
        key = self.normalizar(dezenas)
        dup = self._conn.execute(
            "SELECT COUNT(*) AS c FROM Jogos WHERE LoteriaId = ? AND DezenasKey = ?",
            (loteria_id, key),
        ).fetchone()["c"]
        hoje = datetime.now().date().isoformat()
        try:
            self._conn.execute(
                "INSERT INTO Jogos (LoteriaId, DataRegistro, DezenasKey, Observacao) "
                "VALUES (?,?,?,?)",
                (loteria_id, hoje, key, observacao),
            )
            self._conn.commit()
            return True, "Jogo gravado com sucesso!", dup > 0
        except sqlite3.Error as e:
            self._conn.rollback()
            return False, f"Erro ao gravar: {e}", False

    def listar_jogos(self, loteria_id, limite=300):
        rows = self._conn.execute(
            "SELECT Id, DataRegistro, DezenasKey, Observacao FROM Jogos "
            "WHERE LoteriaId = ? ORDER BY DataRegistro DESC, Id DESC LIMIT ?",
            (loteria_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]

    def status_jogos(self, loteria_id, chaves):
        if not chaves:
            return {}
        placeholders = ", ".join("?" for _ in chaves)
        rows = self._conn.execute(
            f"SELECT DezenasKey, MAX(NumeroConcurso) AS UltimoConcurso FROM Concursos "
            f"WHERE LoteriaId = ? AND DezenasKey IN ({placeholders}) GROUP BY DezenasKey",
            [loteria_id] + list(chaves),
        ).fetchall()
        return {r["DezenasKey"]: r["UltimoConcurso"] for r in rows}

    def excluir_jogo(self, jogo_id):
        self._conn.execute("DELETE FROM Jogos WHERE Id = ?", (jogo_id,))
        self._conn.commit()

    def fechar(self):
        try:
            self._conn.close()
        except Exception:
            pass

class App:
    def __init__(self, root):
        self.root = root
        root.title("Loteria Manager")
        root.protocol("WM_DELETE_WINDOW", self._sair)

        self.db = Database()
        self.loterias = self.db.listar_loterias()
        self.lot = self.loterias[0]

        self._montar_ui()
        self._atualizar_historico()
        self._atualizar_estatisticas()
        self._atualizar_atraso()
        self._atualizar_jogos()

        centralizar_janela(root, 1060, 740)
        root.minsize(900, 620)

    # ---------- Interface ----------
    def _montar_ui(self):
        cab = ctk.CTkFrame(self.root, fg_color="transparent")
        cab.pack(fill="x", padx=24, pady=(18, 4))
        ctk.CTkLabel(cab, text="🎯 Loteria Manager",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(cab, text="Registre, consulte, analise e acompanhe seus jogos",
                     font=ctk.CTkFont(size=12), text_color=CORES["texto2"]).pack(
            side="left", padx=(14, 0), pady=(6, 0))

        barra = ctk.CTkFrame(self.root, fg_color="transparent")
        barra.pack(fill="x", padx=24, pady=(6, 10))
        ctk.CTkLabel(barra, text="Loteria:",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.cmb = ctk.CTkComboBox(barra, values=[l["Nome"] for l in self.loterias],
                                   width=180, state="readonly",
                                   command=self._trocar_loteria)
        self.cmb.set(self.lot["Nome"])
        self.cmb.pack(side="left", padx=10)
        ctk.CTkButton(barra, text="⬆  Importar CSV",
                      command=self._importar_csv, width=150,
                      fg_color=CORES["destaque"], hover_color=CORES["destaque2"],
                      corner_radius=10).pack(side="right")

        self.ab = ctk.CTkTabview(self.root, corner_radius=12,
                                 segmented_button_selected_color=CORES["destaque"],
                                 segmented_button_selected_hover_color=CORES["destaque2"])
        self.ab.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        for nome in ("Cadastrar Sorteio", "Consultar Sequência", "Histórico",
                     "Estatísticas", "Atraso", "Alerta", "Gerador", "Meus Jogos"):
            self.ab.add(nome)

        self._montar_cadastro()
        self._montar_consulta()
        self._montar_historico()
        self._montar_estatisticas()
        self._montar_atraso()
        self._montar_alerta()
        self._montar_gerador()
        self._montar_meus_jogos()

    def _grade(self, container):
        """Cria/recria os campos de dezenas, com auto-avanço ao digitar 2 dígitos."""
        for w in container.winfo_children():
            w.destroy()
        entradas, linha = [], None
        qtd = self.lot["QtdDezenas"]
        por_linha = qtd if qtd <= 10 else 5
        for i in range(qtd):
            if i % por_linha == 0:
                linha = ctk.CTkFrame(container, fg_color="transparent",
                                     corner_radius=0)
                linha.pack(fill="x", pady=3)
            ent = ctk.CTkEntry(linha, width=64, height=38, justify="center",
                               font=ctk.CTkFont(size=15, weight="bold"),
                               corner_radius=8)
            ent.pack(side="left", padx=4)
            entradas.append(ent)
        # Auto-avanço: ao completar 2 dígitos, pula para o próximo campo
        for idx, ent in enumerate(entradas):
            prox = entradas[idx + 1] if idx + 1 < len(entradas) else None
            ent.bind("<KeyRelease>", lambda e, p=prox: self._auto_avancar(e, p))
        return entradas

    def _auto_avancar(self, evento, proximo):
        if proximo is None:
            return
        if len(evento.widget.get().strip()) >= 2:
            proximo.focus_set()

    def _montar_cadastro(self):
        tab = self.ab.tab("Cadastrar Sorteio")
        box = ctk.CTkFrame(tab, fg_color=CORES["card"], corner_radius=14)
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="Dados do Sorteio",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 4))

        l1 = ctk.CTkFrame(box, fg_color="transparent")
        l1.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(l1, text="Nº do Concurso:",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.ent_num = ctk.CTkEntry(l1, width=110, corner_radius=8)
        self.ent_num.pack(side="left", padx=8)
        ctk.CTkLabel(l1, text="Data (dd/mm/aaaa):",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(28, 8))
        self.ent_data = ctk.CTkEntry(l1, width=130, corner_radius=8)
        self.ent_data.pack(side="left")

        ctk.CTkLabel(box, text="Dezenas sorteadas:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(14, 4))
        self.box_dezenas = ctk.CTkFrame(box, fg_color="transparent")
        self.box_dezenas.pack(fill="x", padx=16)
        self.ent_dezenas = self._grade(self.box_dezenas)

        ctk.CTkButton(box, text="💾  Salvar Sorteio", command=self._salvar,
                      fg_color=CORES["verde"], hover_color=CORES["verde2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=180).pack(anchor="w", padx=20, pady=(18, 20))

    def _montar_consulta(self):
        tab = self.ab.tab("Consultar Sequência")
        box = ctk.CTkFrame(tab, fg_color=CORES["card"], corner_radius=14)
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="Verificar se uma sequência já foi sorteada",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(box, text="Digite as dezenas (a ordem não importa):",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(0, 8))
        self.box_consulta = ctk.CTkFrame(box, fg_color="transparent")
        self.box_consulta.pack(fill="x", padx=16)
        self.ent_consulta = self._grade(self.box_consulta)

        l_btns = ctk.CTkFrame(box, fg_color="transparent")
        l_btns.pack(anchor="w", padx=20, pady=(12, 10))
        ctk.CTkButton(l_btns, text="🔍  Verificar Sequência", command=self._verificar,
                      fg_color=CORES["destaque"], hover_color=CORES["destaque2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=210).pack(side="left")
        ctk.CTkButton(l_btns, text="⬇  Copiar p/ Alerta", command=self._copiar_para_alerta,
                      fg_color=CORES["card2"], hover_color=CORES["borda"],
                      corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
                      width=160).pack(side="left", padx=(10, 0))
        ctk.CTkButton(l_btns, text="🧹  Limpar", command=self._limpar_consulta,
                      fg_color=CORES["card2"], hover_color=CORES["borda"],
                      corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
                      width=100).pack(side="left", padx=(10, 0))

        self.lbl_res = ctk.CTkLabel(box, text="", anchor="w", justify="left",
                                    font=ctk.CTkFont(size=13))
        self.lbl_res.pack(anchor="w", padx=20, pady=(0, 4))
        self.lbl_res_ultimo = ctk.CTkLabel(box, text="", anchor="w", justify="left",
                                           font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_res_ultimo.pack(anchor="w", padx=20, pady=(0, 18))

        # Estatísticas da sequência consultada
        self.lbl_seq_est = ctk.CTkLabel(tab, text="", anchor="w",
                                        font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_seq_est.pack(anchor="w", padx=16, pady=(0, 6))
        self.tbl_seq_est = TabelaCTk(tab, ("Dezena", "Vezes", "% Sorteios", "Classe",
                                           "Atraso", "Última saída"),
                                     (80, 80, 110, 180, 90, 210),
                                     alinhamentos=("center", "center", "center", "w",
                                                   "center", "w"))
        self.tbl_seq_est.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _montar_historico(self):
        tab = self.ab.tab("Histórico")
        self.tbl_historico = TabelaCTk(tab, ("Concurso", "Data", "Dezenas"),
                                       (110, 130, 520), alinhamentos=("center", "center", "w"))
        self.tbl_historico.pack(fill="both", expand=True, padx=14, pady=14)

    def _montar_estatisticas(self):
        tab = self.ab.tab("Estatísticas")
        self.lbl_est = ctk.CTkLabel(tab, text="", anchor="w",
                                    font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_est.pack(anchor="w", padx=16, pady=(14, 6))

        corpo = ctk.CTkFrame(tab, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=8, pady=(0, 14))

        col_esq = ctk.CTkFrame(corpo, fg_color="transparent")
        col_esq.pack(side="left", fill="both", expand=True, padx=6)
        ctk.CTkLabel(col_esq, text="Frequência das dezenas",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 6))
        self.tbl_freq = TabelaCTk(col_esq, ("Pos", "Dezena", "Vezes", "% Sorteios"),
                                  (70, 110, 100, 150))
        self.tbl_freq.pack(fill="both", expand=True)

        col_dir = ctk.CTkFrame(corpo, fg_color="transparent")
        col_dir.pack(side="left", fill="both", expand=True, padx=6)
        ctk.CTkLabel(col_dir, text="Quentes vs Frias (percentil)",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(col_dir, text="Top 25% = 🔥 quentes · meio = 🌤️ mornas · últimos 25% = ❄️ frias",
                     font=ctk.CTkFont(size=11), text_color=CORES["texto2"]).pack(anchor="w", pady=(0, 6))
        self.tbl_clas = TabelaCTk(col_dir, ("Dezena", "Vezes", "Classificação"),
                                  (110, 90, 240), alinhamentos=("center", "center", "w"))
        self.tbl_clas.pack(fill="both", expand=True)

    def _montar_atraso(self):
        tab = self.ab.tab("Atraso")
        self.lbl_atraso = ctk.CTkLabel(tab, text="", anchor="w",
                                       font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_atraso.pack(anchor="w", padx=16, pady=(14, 6))
        self.tbl_atraso = TabelaCTk(tab, ("Dezena", "Última saída", "Atraso (concursos)"),
                                    (140, 340, 260), alinhamentos=("center", "w", "center"))
        self.tbl_atraso.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _montar_alerta(self):
        tab = self.ab.tab("Alerta")
        box = ctk.CTkFrame(tab, fg_color=CORES["card"], corner_radius=14)
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="🎯 Alerta de Similaridade",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(box,
                     text="Digite a sua aposta e veja os concursos históricos que mais se aproximaram dela. "
                          "Análise descritiva (não previsão): mostra o que já aconteceu na base.",
                     font=ctk.CTkFont(size=12), text_color=CORES["texto2"],
                     wraplength=900).pack(anchor="w", padx=20, pady=(0, 10))
        self.box_alerta = ctk.CTkFrame(box, fg_color="transparent")
        self.box_alerta.pack(fill="x", padx=16)
        self.ent_alerta = self._grade(self.box_alerta)
        self.lbl_alerta = ctk.CTkLabel(box, text="", anchor="w", justify="left",
                                       font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_alerta.pack(anchor="w", padx=20, pady=(10, 6))

        l_btns = ctk.CTkFrame(box, fg_color="transparent")
        l_btns.pack(anchor="w", padx=20, pady=(0, 18))
        ctk.CTkButton(l_btns, text="🔍  Comparar Aposta", command=self._analisar_aposta,
                      fg_color=CORES["destaque"], hover_color=CORES["destaque2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=210).pack(side="left")
        ctk.CTkButton(l_btns, text="⬆  Copiar p/ Consulta", command=self._copiar_para_consulta,
                      fg_color=CORES["card2"], hover_color=CORES["borda"],
                      corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
                      width=170).pack(side="left", padx=(10, 0))
        ctk.CTkButton(l_btns, text="🧹  Limpar", command=self._limpar_alerta,
                      fg_color=CORES["card2"], hover_color=CORES["borda"],
                      corner_radius=10, font=ctk.CTkFont(size=12, weight="bold"),
                      width=100).pack(side="left", padx=(10, 0))

        self.tbl_alerta = TabelaCTk(tab, ("Concurso", "Data", "Dezenas do Concurso",
                                          "Acertos", "Dezenas em Comum"),
                                    (100, 120, 320, 90, 320),
                                    alinhamentos=("center", "center", "w", "center", "w"))
        self.tbl_alerta.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _montar_gerador(self):
        tab = self.ab.tab("Gerador")
        box = ctk.CTkFrame(tab, fg_color=CORES["card"], corner_radius=14)
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="🎲 Gerador de Jogos",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(box,
                     text="Gera jogos com base no histórico da loteria selecionada. "
                          "Análise descritiva (não previsão): os jogos seguem perfis típicos "
                          "e evitam viéses comuns — não aumentam a chance de ganhar, "
                          "mas dão disciplina e variedade à sua aposta.",
                     font=ctk.CTkFont(size=12), text_color=CORES["texto2"],
                     wraplength=900).pack(anchor="w", padx=20, pady=(0, 12))

        linha = ctk.CTkFrame(box, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(linha, text="Estratégia:", font=ctk.CTkFont(size=13)).pack(side="left")
        self.cmb_estrategia = ctk.CTkOptionMenu(
            linha, values=list(ESTRATEGIAS.keys()), width=230,
            fg_color=CORES["card2"], button_color=CORES["destaque"],
            button_hover_color=CORES["destaque2"])
        self.cmb_estrategia.set("Equilibrado (padrão)")
        self.cmb_estrategia.pack(side="left", padx=8)

        ctk.CTkLabel(linha, text="Quantidade:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(28, 8))
        self.cmb_qtd = ctk.CTkOptionMenu(
            linha, values=[str(i) for i in range(1, 11)], width=80,
            fg_color=CORES["card2"], button_color=CORES["destaque"],
            button_hover_color=CORES["destaque2"])
        self.cmb_qtd.set("5")
        self.cmb_qtd.pack(side="left")

        ctk.CTkButton(box, text="🎲  Gerar Jogos", command=self._gerar_jogos,
                      fg_color=CORES["destaque"], hover_color=CORES["destaque2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=190).pack(anchor="w", padx=20, pady=(14, 16))

        self.lbl_gerador = ctk.CTkLabel(tab, text="", anchor="w",
                                        font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_gerador.pack(anchor="w", padx=16, pady=(0, 6))
        self.tbl_gerador = TabelaCTk(tab, ("#", "Jogo", "Composição"),
                                     (45, 460, 300), alinhamentos=("center", "w", "w"))
        self.tbl_gerador.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _montar_meus_jogos(self):
        tab = self.ab.tab("Meus Jogos")
        box = ctk.CTkFrame(tab, fg_color=CORES["card"], corner_radius=14)
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="📋 Meus Jogos",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(box,
                     text="Grave as suas apostas e confira cada jogo contra o ÚLTIMO sorteio cadastrado. "
                          "O status e os acertos atualizam sozinhos ao salvar/importar concursos — "
                          "use o botão Atualizar para conferir manualmente a qualquer momento.",
                     font=ctk.CTkFont(size=12), text_color=CORES["texto2"],
                     wraplength=940).pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(box, text="Dezenas do jogo:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(0, 4))
        self.box_jogos = ctk.CTkFrame(box, fg_color="transparent")
        self.box_jogos.pack(fill="x", padx=16)
        self.ent_jogos = self._grade(self.box_jogos)

        l_obs = ctk.CTkFrame(box, fg_color="transparent")
        l_obs.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(l_obs, text="Observação (opcional):",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self.ent_jogo_obs = ctk.CTkEntry(l_obs, width=420, corner_radius=8)
        self.ent_jogo_obs.pack(side="left", padx=8)

        l_btns = ctk.CTkFrame(box, fg_color="transparent")
        l_btns.pack(anchor="w", padx=20, pady=(12, 16))
        ctk.CTkButton(l_btns, text="💾  Gravar Jogo", command=self._gravar_jogo,
                      fg_color=CORES["verde"], hover_color=CORES["verde2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=180).pack(side="left")
        ctk.CTkButton(l_btns, text="🔄  Atualizar", command=self._atualizar_jogos,
                      fg_color=CORES["destaque"], hover_color=CORES["destaque2"],
                      corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"),
                      width=150).pack(side="left", padx=(12, 0))

        self.lbl_jogos = ctk.CTkLabel(tab, text="", anchor="w",
                                      font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_jogos.pack(anchor="w", padx=16, pady=(0, 6))
        self.tbl_jogos = TabelaCTk(tab, ("Data", "Jogo", "Status", "Acertos no último sorteio",
                                         "Observação"),
                                   (90, 260, 200, 190, 170),
                                   alinhamentos=("center", "w", "w", "center", "w"),
                                   btn_texto="🗑 Excluir", btn_comando=self._excluir_jogo)
        self.tbl_jogos.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    # ---------- Ações ----------
    def _trocar_loteria(self, escolha=None):
        nome = escolha or self.cmb.get()
        self.lot = next(l for l in self.loterias if l["Nome"] == nome)
        self.ent_dezenas = self._grade(self.box_dezenas)
        self.ent_consulta = self._grade(self.box_consulta)
        self.ent_alerta = self._grade(self.box_alerta)
        self.ent_jogos = self._grade(self.box_jogos)
        self.ent_jogo_obs.delete(0, "end")
        self.tbl_gerador.limpar()
        self.lbl_gerador.configure(text="")
        self.lbl_res.configure(text="")
        self.lbl_res_ultimo.configure(text="")
        self.tbl_seq_est.limpar()
        self.lbl_seq_est.configure(text="")
        self._atualizar_historico()
        self._atualizar_estatisticas()
        self._atualizar_atraso()
        self._atualizar_jogos()

    def _copiar_para_alerta(self):
        for origem, destino in zip(self.ent_consulta, self.ent_alerta):
            destino.delete(0, "end")
            destino.insert(0, origem.get().strip())

    def _copiar_para_consulta(self):
        for origem, destino in zip(self.ent_alerta, self.ent_consulta):
            destino.delete(0, "end")
            destino.insert(0, origem.get().strip())

    def _limpar_consulta(self):
        for e in self.ent_consulta:
            e.delete(0, "end")
        self.lbl_res.configure(text="")
        self.lbl_res_ultimo.configure(text="")
        self.tbl_seq_est.limpar()
        self.lbl_seq_est.configure(text="")

    def _limpar_alerta(self):
        for e in self.ent_alerta:
            e.delete(0, "end")
        self.lbl_alerta.configure(text="")
        self.tbl_alerta.limpar()

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
            messagebox.showerror("Erro", f"As dezenas devem estar entre {mn} e {mx}.")
            return
        ok, msg = self.db.salvar_concurso(self.lot["Id"], numero, data, dezenas)
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
            self._atualizar_jogos()
        else:
            messagebox.showwarning("Atenção", msg)

    def _verificar(self):
        try:
            dezenas = [int(e.get().strip()) for e in self.ent_consulta]
        except ValueError:
            messagebox.showerror("Erro", "Preencha todos os números corretamente.")
            return
        qtd = self.lot["QtdDezenas"]
        if len(dezenas) != qtd or len(set(dezenas)) != qtd:
            messagebox.showerror("Erro", f"Informe {qtd} números distintos.")
            return
        res = self.db.consultar_sequencia(self.lot["Id"], dezenas)
        if res:
            texto = f"✅ JÁ FOI sorteada {len(res)} vez(es):\n"
            for r in res[:10]:
                texto += f"   • Concurso {r['NumeroConcurso']} em {self._fmt(r['DataSorteio'])} ({r['DezenasKey']})\n"
            if len(res) > 10:
                texto += f"   ... mais {len(res) - 10} ocorrência(s)."
            self.lbl_res.configure(text=texto, text_color=CORES["verde"])
        else:
            self.lbl_res.configure(text="❌ NUNCA foi sorteada nesta loteria.",
                                   text_color=CORES["vermelho"])
        # Acertos no último concurso (apenas a quantidade)
        ultimo = self.db.ultimo_concurso(self.lot["Id"])
        if ultimo:
            conj_ultimo = set(int(d) for d in ultimo["DezenasKey"].split("-"))
            acertadas = sorted(set(dezenas) & conj_ultimo)
            self.lbl_res_ultimo.configure(
                text=f"🎯 Acertos no último concurso {ultimo['NumeroConcurso']} "
                     f"({self._fmt(ultimo['DataSorteio'])}): {len(acertadas)}/{qtd}",
                text_color=CORES["texto"])
        else:
            self.lbl_res_ultimo.configure(
                text="🎯 Nenhum concurso cadastrado ainda para esta loteria.",
                text_color=CORES["texto2"])
        # Estatísticas apenas dos números informados
        self.tbl_seq_est.limpar()
        est = self.db.estatisticas_sequencia(self.lot["Id"], dezenas)
        if not est:
            self.lbl_seq_est.configure(
                text="📭 Nenhum concurso cadastrado para esta loteria ainda.")
            return
        self.lbl_seq_est.configure(
            text=f"📊 Estatísticas dos {len(dezenas)} números consultados "
                 f"(base: {est['total']} concursos · último: concurso "
                 f"{est['ultimo_concurso']} em {self._fmt(est['ultima_data'])})")
        rotulos = {"quente": "🔥 Quente (top 25%)",
                   "morno": "🌤️ Morna (meio)",
                   "frio": "❄️ Fria (últimos 25%)"}
        cores = {"quente": CORES["quente"], "morno": CORES["card"], "frio": CORES["frio"]}
        for linha in est["linhas"]:
            if linha["nunca"]:
                ultimo = "Nunca saiu"
                atraso = "desde o início"
            else:
                ultimo = f"Concurso {linha['ultimo_concurso']} ({self._fmt(linha['ultima_data'])})"
                atraso = f"{linha['atraso']}"
            self.tbl_seq_est.adicionar(
                (f"{linha['dezena']:02d}", linha["vezes"], f"{linha['pct']}%",
                 rotulos[linha["classe"]], atraso, ultimo),
                fg=cores[linha["classe"]])

    def _importar_csv(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo CSV",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            inseridos, erros = self.db.importar_csv(caminho, self.lot["Id"], self.lot["QtdDezenas"])
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
        self._atualizar_jogos()

    def _fmt(self, iso):
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(iso)

    def _atualizar_historico(self):
        self.tbl_historico.limpar()
        for r in self.db.listar_concursos(self.lot["Id"]):
            self.tbl_historico.adicionar(
                (r["NumeroConcurso"], self._fmt(r["DataSorteio"]), r["DezenasKey"]))

    def _atualizar_estatisticas(self):
        self.tbl_freq.limpar()
        self.tbl_clas.limpar()
        res = self.db.estatisticas(self.lot["Id"])
        if not res or res["total"] == 0:
            self.lbl_est.configure(text="📭 Nenhum sorteio cadastrado ainda para esta loteria.")
            return
        self.lbl_est.configure(
            text=f"📈 {res['total']} concursos analisados — {self.lot['Nome']} (histórico completo)")
        for i, (dezena, vezes, pct) in enumerate(res["frequencia"], 1):
            self.tbl_freq.adicionar((i, f"{dezena:02d}", vezes, f"{pct}%"))
        rotulos = {"quente": "🔥 Quente (top 25%)",
                   "morno": "🌤️ Morna (meio)",
                   "frio": "❄️ Fria (últimos 25%)"}
        cores = {"quente": CORES["quente"], "morno": CORES["card"], "frio": CORES["frio"]}
        for dezena, vezes, classe in res["classificacao"]:
            self.tbl_clas.adicionar((f"{dezena:02d}", vezes, rotulos[classe]),
                                    fg=cores[classe])

    def _atualizar_atraso(self):
        self.tbl_atraso.limpar()
        res = self.db.atraso_dezenas(self.lot["Id"], self.lot["MinNumero"], self.lot["MaxNumero"])
        if not res:
            self.lbl_atraso.configure(text="📭 Nenhum sorteio cadastrado para esta loteria.")
            return
        top = ", ".join(f"{l['dezena']:02d}" for l in res["linhas"][:5])
        self.lbl_atraso.configure(
            text=f"📅 {res['total']} concursos · último: {res['ultimo_concurso']} "
                 f"({self._fmt(res['ultima_data'])}) · mais atrasadas: {top}")
        for i, linha in enumerate(res["linhas"]):
            if linha["nunca"]:
                ultimo = "Nunca saiu"
                atraso = f"desde o início ({linha['atraso']} concursos)"
            else:
                ultimo = f"Concurso {linha['ultimo_concurso']} ({self._fmt(linha['ultima_data'])})"
                atraso = f"{linha['atraso']}"
            self.tbl_atraso.adicionar((f"{linha['dezena']:02d}", ultimo, atraso),
                                      fg=(CORES["top_atraso"] if i < 5 else CORES["card"]))

    def _analisar_aposta(self):
        try:
            dezenas = [int(e.get().strip()) for e in self.ent_alerta]
        except ValueError:
            messagebox.showerror("Erro", "Preencha todos os números corretamente.")
            return
        qtd, mn, mx = self.lot["QtdDezenas"], self.lot["MinNumero"], self.lot["MaxNumero"]
        if len(dezenas) != qtd:
            messagebox.showerror("Erro", f"Informe exatamente {qtd} números.")
            return
        if len(set(dezenas)) != qtd:
            messagebox.showerror("Erro", "Existem números repetidos na aposta.")
            return
        if not all(mn <= d <= mx for d in dezenas):
            messagebox.showerror("Erro", f"Os números devem estar entre {mn} e {mx}.")
            return
        resultado = self.db.similaridade(self.lot["Id"], dezenas)
        self.tbl_alerta.limpar()
        if not resultado:
            self.lbl_alerta.configure(text="📭 Nenhum concurso no histórico ainda para comparar.")
            return
        aposta_txt = " · ".join(f"{d:02d}" for d in sorted(dezenas))
        melhor = resultado[0]
        self.lbl_alerta.configure(
            text=f"Sua aposta: {aposta_txt}   →   melhor similaridade: "
                 f"{melhor['acertos']}/{qtd} acertos no concurso {melhor['concurso']}")
        for i, r in enumerate(resultado):
            self.tbl_alerta.adicionar(
                (r["concurso"], self._fmt(r["data"]), r["dezenas_key"],
                 f"{r['acertos']}/{qtd}", r["acertadas"]),
                fg=(CORES["melhor"] if i == 0 else CORES["card"]))

    def _gerar_jogos(self):
        estrategia = ESTRATEGIAS[self.cmb_estrategia.get()]
        quantidade = int(self.cmb_qtd.get())
        resultado = self.db.gerar_jogos(self.lot["Id"], quantidade, estrategia)
        self.tbl_gerador.limpar()
        if not resultado:
            self.lbl_gerador.configure(
                text="⚠️ Não foi possível gerar os jogos. Cadastre/importe concursos "
                     "ou tente outra estratégia.")
            return
        rot = {"equilibrado": "Equilibrado",
               "ponderado": "Ponderado por frequência",
               "puro": "Puro aleatório"}
        self.lbl_gerador.configure(
            text=f"🎲 {len(resultado)} jogo(s) gerado(s) · estratégia: {rot[estrategia]} "
                 f"· {self.lot['Nome']} (análise descritiva, não previsão)")
        for i, g in enumerate(resultado, 1):
            jogo_txt = " · ".join(f"{d:02d}" for d in g["jogo"])
            comp_txt = f"🔥 {g['quentes']} quentes · 🌤️ {g['mornas']} mornas · ❄️ {g['frias']} frias"
            self.tbl_gerador.adicionar((i, jogo_txt, comp_txt))

    # ---------- Meus Jogos ----------
    def _gravar_jogo(self):
        try:
            dezenas = [int(e.get().strip()) for e in self.ent_jogos]
        except ValueError:
            messagebox.showerror("Erro", "Preencha todos os números corretamente.")
            return
        qtd, mn, mx = self.lot["QtdDezenas"], self.lot["MinNumero"], self.lot["MaxNumero"]
        if len(dezenas) != qtd:
            messagebox.showerror("Erro", f"Informe exatamente {qtd} números.")
            return
        if len(set(dezenas)) != qtd:
            messagebox.showerror("Erro", "Existem números repetidos no jogo.")
            return
        if not all(mn <= d <= mx for d in dezenas):
            messagebox.showerror("Erro", f"Os números devem estar entre {mn} e {mx}.")
            return
        observacao = self.ent_jogo_obs.get().strip()
        ok, msg, duplicado = self.db.salvar_jogo(self.lot["Id"], dezenas, observacao)
        if not ok:
            messagebox.showerror("Erro", msg)
            return
        res = self.db.consultar_sequencia(self.lot["Id"], dezenas)
        texto = msg
        if duplicado:
            texto += "\n\n⚠️ Já existe um jogo idêntico gravado (mantive mesmo assim)."
        if res:
            texto += (f"\n\nℹ️ Atenção: essa sequência JÁ foi sorteada no concurso "
                      f"{res[0]['NumeroConcurso']}.")
        messagebox.showinfo("Jogo gravado", texto)
        for e in self.ent_jogos:
            e.delete(0, "end")
        self.ent_jogo_obs.delete(0, "end")
        self._atualizar_jogos()

    def _excluir_jogo(self, jogo_id):
        if not messagebox.askyesno("Excluir jogo", "Deseja excluir este jogo gravado?"):
            return
        self.db.excluir_jogo(jogo_id)
        self._atualizar_jogos()

    def _atualizar_jogos(self):
        self.tbl_jogos.limpar()
        jogos = self.db.listar_jogos(self.lot["Id"])
        ultimo = self.db.ultimo_concurso(self.lot["Id"])
        if not jogos:
            if ultimo:
                self.lbl_jogos.configure(
                    text=f"📋 Nenhum jogo gravado para {self.lot['Nome']}. "
                         f"Último sorteio cadastrado: concurso {ultimo['NumeroConcurso']} "
                         f"({self._fmt(ultimo['DataSorteio'])}).")
            else:
                self.lbl_jogos.configure(
                    text=f"📋 Nenhum jogo gravado para {self.lot['Nome']}.")
            return
        chaves = [j["DezenasKey"] for j in jogos]
        sorteadas = self.db.status_jogos(self.lot["Id"], chaves)
        n_sorteados = sum(1 for k in chaves if k in sorteadas)
        if ultimo:
            conj_ultimo = set(int(d) for d in ultimo["DezenasKey"].split("-"))
            suf = (f" · último sorteio: concurso {ultimo['NumeroConcurso']} "
                   f"({self._fmt(ultimo['DataSorteio'])})")
        else:
            conj_ultimo = None
            suf = " · nenhum concurso cadastrado ainda"
        self.lbl_jogos.configure(
            text=f"📋 {len(jogos)} jogo(s) · ✅ {n_sorteados} já sorteados"
                 f" · ❌ {len(jogos) - n_sorteados} nunca sorteados{suf}")
        for j in jogos:
            if j["DezenasKey"] in sorteadas:
                status = f"✅ Já sorteado (concurso {sorteadas[j['DezenasKey']]})"
                cor = CORES["melhor"]
            else:
                status = "❌ Nunca sorteado"
                cor = CORES["card"]
            if conj_ultimo is not None:
                dezs_jogo = set(int(d) for d in j["DezenasKey"].split("-"))
                txt_ac = f"{len(conj_ultimo & dezs_jogo)}"
            else:
                txt_ac = "—"
            obs = j["Observacao"] or "—"
            self.tbl_jogos.adicionar(
                (self._fmt(j["DataRegistro"]), j["DezenasKey"], status, txt_ac, obs),
                fg=cor, btn_dado=j["Id"])

    def _sair(self):
        self.db.fechar()
        self.root.destroy()

if __name__ == "__main__":
    import traceback as _tb

    app = ctk.CTk()

    def _reportar_erro(exc, val, tbk):
        texto = "".join(_tb.format_exception(exc, val, tbk))
        try:
            print("===== ERRO NO APP =====")
            print(texto)
            print("=======================")
        except Exception:
            pass
        try:
            messagebox.showerror(
                "Erro inesperado",
                f"{exc.__name__}: {val}\n\nRastreamento completo no console (terminal).")
        except Exception:
            pass

    app.report_callback_exception = _reportar_erro
    App(app)
    app.mainloop()