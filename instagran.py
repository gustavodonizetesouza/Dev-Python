import time
import random
import threading
from datetime import datetime

import pyautogui
import pyperclip
from pynput import keyboard, mouse
from pynput.keyboard import Key
from pynput.mouse import Button

# ========== CONFIGURAÇÕES ==========
TEXTO_FIXO = "Eu"
POS_CAMPO = (980, 948)
POS_BOTAO = (1486, 959)
USAR_BOTAO = True

REPETICOES = 25  # quantos cadastros por ciclo
INTERVALO_ENTRE_CICLOS = (800, 1200)  # segundos entre ciclos (ex.: 1 a 1,5 minutos)

PAUSA_ENTRE_PASSOS = (0.2, 0.5)
PAUSA_ENTRE_REGISTROS = (1.5, 2.5)

MODO_DIGITAR = "paste"  # "type" ou "paste"
INTERVALO_DIGITO = 0.02

pyautogui.FAILSAFE = True
CONTAGEM_REGRESSIVA_INICIO = 7
# ==================================

stop_event = threading.Event()
_last_click_time = 0.0

def pausa(minmax):
    time.sleep(random.uniform(*minmax))

def on_key_press(key):
    if key == Key.esc:
        print("[STOP] ESC detectado.")
        stop_event.set()
        return False

def on_mouse_click(x, y, button, pressed):
    global _last_click_time
    if pressed and button == Button.left:
        now = time.perf_counter()
        if (now - _last_click_time) <= 0.30:
            print("[STOP] Duplo clique detectado.")
            stop_event.set()
            return False
        _last_click_time = now

def clicar(pos):
    pyautogui.moveTo(pos[0], pos[1], duration=random.uniform(0.12, 0.25))
    pausa(PAUSA_ENTRE_PASSOS)
    pyautogui.click()

def digitar_texto(texto):
    if MODO_DIGITAR == "paste":
        pyperclip.copy(texto)
        pausa(PAUSA_ENTRE_PASSOS)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        pausa(PAUSA_ENTRE_PASSOS)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        pausa(PAUSA_ENTRE_PASSOS)
        pyautogui.write(texto, interval=INTERVALO_DIGITO)

def cadastrar():
    if USAR_BOTAO and POS_BOTAO:
        clicar(POS_BOTAO)
    else:
        pyautogui.press("enter")

def fluxo_cadastro():
    clicar(POS_CAMPO)
    digitar_texto(TEXTO_FIXO)
    pausa(PAUSA_ENTRE_PASSOS)
    cadastrar()
    print(f"[OK] Cadastro enviado às {datetime.now().strftime('%H:%M:%S')}")

def main():
    print("Iniciando em:")
    for i in range(CONTAGEM_REGRESSIVA_INICIO, 0, -1):
        print(f"  {i}…")
        time.sleep(1)
    print("Rodando. Pare com ESC, duplo clique ou movendo para (0,0).")

    ciclo = 1
    while not stop_event.is_set():
        print(f"\n=== CICLO {ciclo} ===")
        for n in range(1, REPETICOES + 1):
            if stop_event.is_set(): break
            print(f"\n--- Registro {n}/{REPETICOES} ---")
            fluxo_cadastro()
            if n < REPETICOES:
                pausa(PAUSA_ENTRE_REGISTROS)

        if stop_event.is_set(): break

        # intervalo entre ciclos
        intervalo = random.uniform(*INTERVALO_ENTRE_CICLOS)
        print(f"[INFO] Ciclo {ciclo} finalizado. Aguardando {intervalo:.1f}s para reiniciar...")
        t0 = time.perf_counter()
        while not stop_event.is_set() and (time.perf_counter() - t0) < intervalo:
            time.sleep(0.5)
        ciclo += 1

    print("Encerrando execução.")

if __name__ == "__main__":
    kb_listener = keyboard.Listener(on_press=on_key_press)
    ms_listener = mouse.Listener(on_click=on_mouse_click)
    kb_listener.start()
    ms_listener.start()
    try:
        main()
    finally:
        if kb_listener.running: kb_listener.stop()
        if ms_listener.running: ms_listener.stop()
