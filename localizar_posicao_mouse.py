import pyautogui
import time

print("Movimente o mouse (CTRL + C para parar):")
try:
    while True:
        x, y = pyautogui.position()
        print(f"({x}, {y})", end="\r")  # sobrescreve na mesma linha
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nFinalizado.")
