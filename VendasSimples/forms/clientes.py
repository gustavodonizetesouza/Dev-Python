from tkinter import *

master = Tk()

class Application():
    def __init__(self):
        self.master = master
        self.tela_principal()
        master.mainloop()

    def tela_principal(self):
        self.master.title("Cadastro de Clientes")


Application()
