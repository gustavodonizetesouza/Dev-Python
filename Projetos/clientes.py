from tkinter import *

main = Tk()

class Application():
    def __init__(self):
        self.main = main
        self.tela()
        main.mainloop()

    def tela(self):
        #Titulo do Formulário
        self.main.title("Cadastro de Clientes")        
        #Configuração da cor do fundo do formulário
        self.main.configure(background='lightblue')
        #Configuração tamanho inicial do formulário
        # 1080 largura do formulario na tela e 
        self.main.geometry("1080x550") 
        #self.main.resizable(False, False)
        #self.main.maxsize(width=900, height=700)
        #self.main.minsize(width=400, height=300)


Application()