import re
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pdfplumber

ctk.set_appearance_mode("dark")   # "dark", "light" ou "system"
ctk.set_default_color_theme("blue")

NS_NFE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


# ============================================================
# UTILIDADES DE NOME
# ============================================================

def limpar_nome(texto: str) -> str:
    """Remove caracteres inválidos para nome de arquivo no Windows."""
    texto = re.sub(r'[\\/:*?"<>|]', '', texto or "")
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def primeiros_dois_nomes(texto: str) -> str:
    """Retorna apenas as duas primeiras palavras."""
    palavras = (texto or "").split()
    return " ".join(palavras[:2]) if palavras else texto


def montar_nome(info: dict, usar_destinatario: bool, usar_dois_nomes: bool) -> str:
    """Monta 'RAZAO_SOCIAL_NUMERO.pdf' a partir dos dados extraídos."""
    if usar_destinatario:
        razao = info.get("destinatario") or "SEM_RAZAO_SOCIAL"
    else:
        razao = info.get("emitente") or "SEM_RAZAO_SOCIAL"

    if usar_dois_nomes:
        razao = primeiros_dois_nomes(razao)

    numero = info.get("numero_nf") or ""
    if numero.isdigit():
        numero = numero.zfill(9)   # garante 9 dígitos com zero à esquerda
    else:
        numero = "SEM_NUMERO"

    return f"{limpar_nome(razao)}_{numero}.pdf"


# ============================================================
# MODO PDF — extrai dados da DANFE existente
# ============================================================

def extrair_info_pdf(caminho_pdf: Path) -> dict:
    info = {"chave": None, "numero_nf": None,
            "emitente": None, "destinatario": None}

    with pdfplumber.open(caminho_pdf) as pdf:
        texto = pdf.pages[0].extract_text() or ""
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]

    # Chave de acesso: 44 dígitos (pode quebrar de linha)
    m = re.search(r'\d{44}', re.sub(r'[\s.\-/]', '', texto))
    if m:
        info["chave"] = m.group(0)
        # número da NF embutido na chave
        info["numero_nf"] = m.group(0)[25:34]

    # Razão social do EMITENTE
    for linha in linhas[2:20]:
        if len(linha) >= 8 and not re.fullmatch(r'[\d\s./\-()]+', linha):
            if not re.match(
                r'^(DANFE|DOCUMENTO AUXILIAR|CHAVE|0\s*-|1\s*-|IDENTIFICA)',
                linha, re.IGNORECASE
            ):
                info["emitente"] = linha
                break

    # Razão social do DESTINATÁRIO
    for i, linha in enumerate(linhas):
        if "RAZ" in linha.upper() and ("NOME" in linha.upper() or "SOCIAL" in linha.upper()):
            for candidata in linhas[i + 1: i + 5]:
                if len(candidata) >= 5 and not re.fullmatch(r'[\d\s./\-()]+', candidata):
                    info["destinatario"] = candidata
                    break
            break

    return info


# ============================================================
# MODO XML — extrai dados estruturados do XML da NF-e
# ============================================================

def extrair_info_xml(caminho_xml: Path) -> dict:
    info = {"chave": None, "numero_nf": None,
            "emitente": None, "destinatario": None}

    root = ET.parse(caminho_xml).getroot()

    info["emitente"] = root.findtext(
        ".//nfe:emit/nfe:xNome", namespaces=NS_NFE)
    info["destinatario"] = root.findtext(
        ".//nfe:dest/nfe:xNome", namespaces=NS_NFE)

    nnf = root.findtext(".//nfe:ide/nfe:nNF", namespaces=NS_NFE)
    info["numero_nf"] = nnf.strip() if nnf else None

    # Chave: pega do protocolo se existir, senão localiza 44 dígitos no texto
    chave = root.findtext(".//nfe:chNFe", namespaces=NS_NFE)
    if not chave:
        m = re.search(r'\d{44}', caminho_xml.read_text(
            encoding="utf-8", errors="ignore"))
        chave = m.group(0) if m else None
    info["chave"] = chave

    return info


def gerar_danfe_de_xml(xml_path: Path, pdf_destino: Path) -> None:
    """Gera o PDF da DANFE a partir do XML (import lazy para não pesar o modo PDF)."""
    try:
        from brazilfiscalreport.danfe import Danfe
    except ModuleNotFoundError:
        raise RuntimeError(
            "Biblioteca brazilfiscalreport não instalada. "
            "Execute: pip install brazilfiscalreport")

    xml_content = xml_path.read_text(encoding="utf-8")
    danfe = Danfe(xml=xml_content)
    danfe.output(str(pdf_destino))


# ============================================================
# PROCESSAMENTO (comum aos dois modos)
# ============================================================

def processar_arquivo(caminho: Path, modo_xml: bool,
                      usar_destinatario: bool, usar_dois_nomes: bool) -> str:
    """Processa um arquivo: renomeia (PDF) ou gera+nomeia (XML). Retorna o nome final."""
    if modo_xml:
        info = extrair_info_xml(caminho)
    else:
        info = extrair_info_pdf(caminho)

    novo_nome = montar_nome(info, usar_destinatario, usar_dois_nomes)
    destino = caminho.with_name(novo_nome)

    # Evita sobrescrever arquivos já existentes
    contador = 1
    while destino.exists() and destino != caminho:
        destino = caminho.with_name(f"{novo_nome[:-4]}_{contador}.pdf")
        contador += 1

    if modo_xml:
        gerar_danfe_de_xml(caminho, destino)   # cria o PDF novo
    else:
        caminho.rename(destino)                # renomeia o PDF existente

    return destino.name


# ============================================================
# INTERFACE GRÁFICA
# ============================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Renomeador / Gerador de DANFE")
        self.geometry("780x580")
        self.minsize(680, 500)

        self.var_pasta = ctk.StringVar()
        self.var_modo_xml = ctk.BooleanVar(
            value=False)   # True = XML | False = PDF
        # "emitente" | "destinatario"
        self.var_modo = ctk.StringVar(value="emitente")
        self.var_dois_nomes = ctk.BooleanVar(value=True)

        # ---------- Linha 0: pasta ----------
        ctk.CTkLabel(self, text="Pasta:").grid(
            row=0, column=0, padx=(15, 5), pady=(15, 5), sticky="w")

        self.entry_pasta = ctk.CTkEntry(self, textvariable=self.var_pasta)
        self.entry_pasta.grid(row=0, column=1, padx=5,
                              pady=(15, 5), sticky="ew")

        ctk.CTkButton(self, text="Procurar", width=90,
                      command=self.escolher_pasta).grid(
            row=0, column=2, padx=(5, 15), pady=(15, 5))

        # ---------- Linha 1: modo de leitura (PDF x XML) ----------
        ctk.CTkLabel(self, text="Modo de leitura:").grid(
            row=1, column=0, padx=(15, 5), pady=5, sticky="w")

        ctk.CTkCheckBox(
            self,
            text="Buscar por XML (gerar a DANFE a partir do XML)",
            variable=self.var_modo_xml,
            command=self.atualizar_placeholder
        ).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # ---------- Linha 2: emitente x destinatário ----------
        ctk.CTkLabel(self, text="Renomear por:").grid(
            row=2, column=0, padx=(15, 5), pady=5, sticky="w")

        frame_modo = ctk.CTkFrame(self, fg_color="transparent")
        frame_modo.grid(row=2, column=1, columnspan=2,
                        padx=5, pady=5, sticky="w")
        ctk.CTkRadioButton(frame_modo, text="Emitente (Fornecedor)",
                           variable=self.var_modo, value="emitente").pack(
            side="left", padx=(0, 20))
        ctk.CTkRadioButton(frame_modo, text="Destinatário (Cliente)",
                           variable=self.var_modo, value="destinatario").pack(
            side="left")

        # ---------- Linha 3: 2 primeiros nomes ----------
        ctk.CTkCheckBox(self, text="Usar apenas os 2 primeiros nomes",
                        variable=self.var_dois_nomes).grid(
            row=3, column=1, columnspan=2, padx=5, pady=(0, 10), sticky="w")

        # ---------- Linha 4: botão processar ----------
        self.botao_processar = ctk.CTkButton(
            self, height=40, command=self.processar)
        self.botao_processar.grid(row=4, column=1, columnspan=2,
                                  padx=5, pady=(5, 10), sticky="ew")

        # ---------- Linha 5: log ----------
        self.textbox_log = ctk.CTkTextbox(
            self, font=("Consolas", 12), state="disabled")
        self.textbox_log.grid(row=5, column=0, columnspan=3,
                              padx=15, pady=(0, 10), sticky="nsew")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self.atualizar_placeholder()
        self.log(
            "Aguardando... selecione a pasta, escolha o modo (PDF ou XML) e clique em Processar.\n")
        self.after(50, self.centralizar_janela)

    # ---------- Métodos da interface ----------

    def centralizar_janela(self):
        """Posiciona a janela no centro da tela."""
        self.update_idletasks()
        largura = self.winfo_width()
        altura = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (largura // 2)
        y = (self.winfo_screenheight() // 2) - (altura // 2)
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def atualizar_placeholder(self):
        """Ajusta placeholder e texto do botão conforme o modo selecionado."""
        if self.var_modo_xml.get():
            self.entry_pasta.configure(
                placeholder_text="Selecione a pasta com os arquivos XML...")
            self.botao_processar.configure(text="▶  Gerar DANFEs dos XMLs")
        else:
            self.entry_pasta.configure(
                placeholder_text="Selecione a pasta com as DANFEs em PDF...")
            self.botao_processar.configure(text="▶  Processar DANFEs (PDF)")

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta")
        if pasta:
            self.var_pasta.set(pasta)
            self.log(f"Pasta selecionada: {pasta}")

    def log(self, mensagem: str):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", mensagem + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def processar(self):
        pasta = self.var_pasta.get().strip()
        if not pasta or not Path(pasta).exists():
            messagebox.showerror("Pasta inválida",
                                 "Selecione uma pasta válida com os arquivos.")
            return

        self.botao_processar.configure(state="disabled")
        threading.Thread(target=self._worker, args=(
            pasta,), daemon=True).start()

    def _worker(self, pasta: str):
        modo_xml = self.var_modo_xml.get()
        usar_dest = self.var_modo.get() == "destinatario"
        dois_nomes = self.var_dois_nomes.get()

        diretorio = Path(pasta)
        arquivos = sorted(diretorio.glob("*.xml" if modo_xml else "*.pdf"))
        tipo = "XML" if modo_xml else "PDF"

        verbo = "Gerando DANFEs a partir" if modo_xml else "Renomeando arquivos"
        self.after(0, lambda: self.log(
            f"\n{verbo} de {len(arquivos)} arquivo(s) {tipo}..."))

        ok, erros = 0, 0
        for arquivo in arquivos:
            try:
                novo = processar_arquivo(
                    arquivo, modo_xml, usar_dest, dois_nomes)
                self.after(0, lambda a=arquivo, n=novo: self.log(
                    f"  OK   {a.name}\n        → {n}"))
                ok += 1
            except Exception as e:
                self.after(0, lambda a=arquivo, e=e: self.log(
                    f"  ERRO {a.name}: {e}"))
                erros += 1

        self.after(0, lambda: self.log(
            f"\nConcluído! {ok} processado(s), {erros} com erro."))
        self.after(0, lambda: self.botao_processar.configure(state="normal"))


if __name__ == "__main__":
    app = App()
    app.mainloop()
