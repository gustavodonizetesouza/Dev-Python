import time
import random
import threading
from datetime import datetime

import pyautogui
from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button

# --- Configurações ---
pyautogui.FAILSAFE = True  # mover para (0,0) encerra com exceção
MARGEM = 50                # margem para não ir colado nas bordas
DURACAO_MOV = (0.7, 1.4)   # tempo de movimentação (segundos) min/max
PAUSA_ENTRE_ACOES = (2, 5) # pausa aleatória entre ações (segundos)
PROB_CLique = 0.5          # probabilidade de clicar após um movimento
JANELA_DBLCLICK = 0.30     # segundos para detectar double-click manual

# --- Estado global de parada ---
stop_event = threading.Event()
_last_click_time = 0.0     # para detectar double-click

def on_key_press(key):
    """Para ao pressionar ESC."""
    if key == Key.esc:
        print("[STOP] ESC detectado.")
        stop_event.set()
        return False  # encerra o listener de teclado

def on_mouse_click(x, y, button, pressed):
    """Para ao detectar double-click do usuário (botão esquerdo)."""
    global _last_click_time
    if pressed and button == Button.left:
        now = time.perf_counter()
        if (now - _last_click_time) <= JANELA_DBLCLICK:
            print("[STOP] Duplo clique do mouse detectado.")
            stop_event.set()
            return False  # encerra o listener de mouse
        _last_click_time = now

def mover_mouse_e_clicar():
    print("Iniciado. Pare com: ESC, duplo clique, ou movendo o mouse para (0,0).")
    try:
        largura, altura = pyautogui.size()
        while not stop_event.is_set():
            # Gera uma posição aleatória dentro da tela com margem
            x = random.randint(MARGEM, max(MARGEM, largura - MARGEM))
            y = random.randint(MARGEM, max(MARGEM, altura - MARGEM))

            dur = random.uniform(*DURACAO_MOV)
            try:
                pyautogui.moveTo(x, y, duration=dur)
            except pyautogui.FailSafeException:
                print("[STOP] PyAutoGUI FailSafe acionado (mouse em (0,0)).")
                stop_event.set()
                break

            if stop_event.is_set():
                break

            # Em alguns casos, realiza clique
            if random.random() < PROB_CLique:
                pyautogui.click()
                print(f"↪ Clique em ({x}, {y})  às {datetime.now().strftime('%H:%M:%S')}")
            else:
                print(f"↪ Movimento para ({x}, {y}) às {datetime.now().strftime('%H:%M:%S')}")

            # Pausa entre ações, checando o stop a cada 0.1s
            pausa = random.uniform(*PAUSA_ENTRE_ACOES)
            t0 = time.perf_counter()
            while not stop_event.is_set() and (time.perf_counter() - t0) < pausa:
                time.sleep(0.1)

    finally:
        print("Encerrando execução.")

if __name__ == "__main__":
    # Listeners em threads separadas
    kb_listener = keyboard.Listener(on_press=on_key_press)
    ms_listener = mouse.Listener(on_click=on_mouse_click)
    kb_listener.start()
    ms_listener.start()

    try:
        mover_mouse_e_clicar()
    finally:
        # Garante que listeners terminem
        if kb_listener.running:
            kb_listener.stop()
        if ms_listener.running:
            ms_listener.stop()
