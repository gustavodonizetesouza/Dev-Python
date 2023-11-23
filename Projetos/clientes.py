from tkinter import *

main = Tk()

class Application():
    def __init__(self):
        self.main = main
        self.tela()
        self.frame_tela()
        main.mainloop()

    def tela(self): # contrução da tela

        #Titulo do Formulário
        self.main.title("Cadastro de Clientes")   

        #Configuração da cor do fundo do formulário
        self.main.configure(background='lightblue')

        #Configuração tamanho inicial do formulário
        # 1080 largura do formulario na tela e 550 é altura
        self.main.geometry("1080x550") 

        # esta permite ´pode ajustar o tamanho do form pelo mouse
        self.main.resizable(False, False)

        #permite maximizar e minimizar o form em um tamanho maximo e minimo
        #self.main.maxsize(width=900, height=700)
        #self.main.minsize(width=400, height=300)

    def frame_tela(self):
        self.frame_1 = Frame(self.main, bd = 4, bg='blue',highlightbackground='black', highlightthickness=3,)
        self.frame_1.place(relx= 0.01, rely=0.01, relwidth=0.98, relheight=0.46)
 
Application()