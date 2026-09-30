import time
import pyautogui
import pyperclip
from openpyxl import load_workbook

# ============================================================
# 1. CONFIGURAÇÃO — ajuste estes valores
# ============================================================

# ARQUIVO = r"P:\24-TEMPORARIOS\Gustavo Souza\NF's\NFs Polysuture - Copia.xlsx"   # nome do arquivo
ABA = "Planilha1"       # nome da aba
COLUNA = "B"               # coluna que contém o código
LINHA_INICIO = 2                 # primeira linha com dados (1 = cabeçalho)

# Coordenadas (x, y) — use o modo calibração abaixo para descobrir
COORD_MENU = (327, 250)  # item do menu a acessar
COORD_NAV_ESQUERDA = (342, 358)  # navegação para a esquerda
COORD_NOVA = (434, 358)           # nova coordenada
COORD_BTN_OK_1 = (1063, 887)      # botão OK
COORD_CAMPO_CODIGO = (986, 473)  # campo onde o código é inserido
COORD_BTN_OK_2 = (1156, 782)  # botão OK (após inserir código)
COORD_ESPERA = (983, 436)  # campo de espera do clique
COORD_SETA_PASTA = (736, 508)  # seta que abre a pasta
COORD_SETA_SUBPASTA = (857, 564)  # seta que abre a subpasta
COORD_BTN_OK_3 = (958, 740)  # botão OK final

DELAY_ENTRE_ACOES = 3   # segundos entre cada ação
DELAY_INICIAL = 6    # segundos de espera antes de iniciar (conforme pedido)
DELAY_PASSO_6 = 4

# ============================================================
# 2. MODO CALIBRAÇÃO — rode este bloco para descobrir as coordenadas
# ============================================================


def modo_calibracao():
    """Move o mouse sobre cada elemento e anote o (x, y) exibido."""
    print("Modo calibração: posicione o mouse sobre cada elemento.")
    print("Pressione Ctrl+C para sair.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rPosição: ({x}, {y})", end="")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nCalibração encerrada.")

# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================


def clicar(coord, descricao, delay=None):
    """Clica em uma coordenada e aguarda."""
    pyautogui.click(coord[0], coord[1])
    print(f"  -> Cliquei em: {descricao}")

    if delay is None:
        delay = DELAY_ENTRE_ACOES

    time.sleep(delay)


# def inserir_codigo(codigo):
#     """Copia o código e cola no campo ativo."""
#     pyperclip.copy(codigo)
#     pyautogui.hotkey("ctrl", "v")
#     print(f"  -> Inseri o código: {codigo}")
#     time.sleep(DELAY_ENTRE_ACOES)


def inserir_codigo(codigo):
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(str("000" + codigo), interval=0.5)
    # pyautogui.press("tab")
    pyautogui.write(str("000" + codigo), interval=0.5)

    print(f"  -> Inseri o código: {codigo}")

    time.sleep(DELAY_ENTRE_ACOES)


15


def ler_codigos():
    """Lê os códigos da planilha e adiciona '000' à esquerda."""
    # wb = load_workbook(ARQUIVO)
    # ws = wb[ABA]
    codigos = ["175843", "175844", "175842", "178417", "178418", "175965", "175964", "177494", "177493", "177491", "177490", "177492", "177459", "177460", "177458", "176163", "176126", "176127", "176125", "176164", "176162", "177649", "177802", "177801", "177800", "178972", "178971", "178974", "178976", "178975", "178973", "178856", "178851", "178854", "178852", "178853", "178857", "178855", "176505", "176502", "176501", "176503", "176504", "179127", "179126", "179128", "179338", "179336", "179337", "176685", "176684", "179707", "179708", "179710", "179709", "178233", "180116", "180115", "180114", "180478", "180484", "180483", "180481", "180482", "180480", "180479", "164333", "175824", "175823", "175822", "175821", "175820", "175963", "176173",
               "176088", "176087", "176089", "176090", "176171", "176091", "176488", "176487", "176486", "176484", "176489", "176485", "176663", "176662", "177841", "177840", "177842", "177442", "177444", "177445", "177440", "177441", "177443", "178415", "178416", "179187", "179185", "179186", "179184", "179183", "179394", "179182", "179393", "179392", "179391", "179395", "179765", "179767", "179764", "179763", "179761", "179762", "179766", "178158", "178159", "178161", "178160", "179996", "179997", "180061", "180060", "180103", "180104", "180108", "180105", "180288", "180287", "180062", "180106", "180107", "180504", "180502", "180500", "180499", "180498", "180501", "180503", "172900", "171584", "171583", "171582", "173171", "173172", "171907", "171906", "177502", "176512", "176513", "175961", "179733", "180100"]

    # linha = LINHA_INICIO
    # while True:
    #     valor = ws[f"{COLUNA}{linha}"].value
    #     if valor is None or str(valor).strip() == "":
    #         break
    #     codigo = str(valor).strip()
    #     codigo_formatado = "000" + codigo   # adiciona 000 à esquerda
    #     codigos.append(codigo_formatado)
    #     linha = linha + 1

    return codigos


7
# ============================================================
# 4. FLUXO PRINCIPAL (uma execução = um código)
# ============================================================


def executar_fluxo(codigo):
    """Executa o fluxo completo para um único código."""
    print(f"\n=== Processando código: {codigo} ===")

    # Passo 2: navega no menu e clica
    clicar(COORD_MENU, "menu")
    clicar(COORD_NAV_ESQUERDA, "navegação esquerda")

    # Nova coordenada
    clicar(COORD_NOVA, "nova coordenada")

    # Passo 3: botão OK
    clicar(COORD_BTN_OK_1, "OK 1")

    # Passo 4: insere o código (com 000 à esquerda)
    clicar(COORD_CAMPO_CODIGO, "campo do código")
    inserir_codigo(codigo)

    # Passo 5: OK
    clicar(COORD_BTN_OK_2, "OK 2")

    # Passo 5.1: espera o Protheus processar
    clicar(COORD_ESPERA, "campo de espera", delay=DELAY_PASSO_6)

    # Passo 6: abre a pasta
    clicar(COORD_SETA_PASTA, "seta da pasta", delay=DELAY_PASSO_6)

    # Passo 7: abre a subpasta
    clicar(COORD_SETA_SUBPASTA, "seta da subpasta")

    # Passo 8: OK final
    clicar(COORD_BTN_OK_3, "OK final")

# ============================================================
# 5. EXECUÇÃO PRINCIPAL
# ============================================================


def main():
    # Descomente a linha abaixo para calibrar as coordenadas primeiro
    # modo_calibracao()

    codigos = ler_codigos()
    print(f"Encontrados {len(codigos)} códigos na planilha.")
    print(
        f"Aguardando {DELAY_INICIAL} segundos para você posicionar o Protheus...")
    time.sleep(DELAY_INICIAL)

    for codigo in codigos:
        executar_fluxo(codigo)
        # Ajuste este delay se o Protheus precisar de tempo entre execuções
        time.sleep(5)
        print(codigo)

    print("\nProcesso concluído!")


if __name__ == "__main__":
    main()
