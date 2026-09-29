# ============================================================
# Monitor de cliques do mouse (pynput + pyautogui)
#
# Uso: mapa de coordenadas para automações de QA / PyAutoGUI
# Encerrar: Ctrl+C no terminal
# ============================================================

# Biblioteca de automação de tela (ler posição, clicar, mover)
import pyautogui
# Biblioteca para escutar eventos globais do mouse (cliques, movimento)
from pynput import mouse


def ao_clicar(x, y, button, pressed):
    """
    Callback disparado pelo pynput a CADA evento de clique.

    Parâmetros (fornecidos automaticamente pelo listener):
      x, y    -> coordenadas do cursor no momento do evento
      button  -> qual botão foi acionado (left, right, middle)
      pressed -> True se o botão foi PRESSIONADO, False se foi SOLTO
    """
    # Só queremos capturar o momento de PRESSIONAR o botão
    # (sem isso, cada clique geraria 2 prints: pressionar + soltar)
    if pressed:
        # Coordenadas vindas direto do evento do pynput
        print(f"Clique em: X={x}, Y={y}")

        # CONFIRMAÇÃO com o PyAutoGUI:
        # Lê a posição ATUAL do cursor (tela inteira, em pixels)
        posicao = pyautogui.position()
        print(f"PyAutoGUI: X={posicao.x}, Y={posicao.y}\n")


# Cria o listener de mouse usando o callback definido acima.
# O bloco "with" garante que o listener seja iniciado e ENCERRADO
# automaticamente (recurso de contexto), mesmo em caso de exceção.
with mouse.Listener(on_click=ao_clicar) as listener:

    # Mensagens de orientação exibidas antes de começar a escutar
    print("Clique em qualquer lugar para ver as coordenadas.")
    print("Pressione Ctrl+C no terminal para encerrar.\n")

    # listener.join() bloqueia o programa aqui, mantendo o processo
    # vivo e escutando os eventos. Sem ele, o script terminaria na hora.
    listener.join()
