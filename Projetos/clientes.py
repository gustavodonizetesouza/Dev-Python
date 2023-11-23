from tkinter import *

main = Tk()

class Application():
    def __init__(self):
        self.main = main
        self.tela()
        self.frame_tela()
        self.widgets_frame_campos();
        main.mainloop()

    def tela(self): # contrução da tela

        #Titulo do Formulário
        self.main.title("Cadastro de Clientes")

        #Configuração da cor do fundo do formulário
        self.main.configure(background='#D3D3D3')

        #Configuração tamanho inicial do formulário
        # 1080 largura do formulario na tela e 550 é altura
        self.main.geometry("1080x550")

        # esta permite ´pode ajustar o tamanho do form pelo mouse
        self.main.resizable(False, False)

        # permite maximizar e minimizar o form em um tamanho maximo e minimo
        # self.main.maxsize(width=900, height=700)
        # self.main.minsize(width=400, height=300)

    def frame_tela(self):

        # relx -> distancia da borda esquerda, 
        # rely -> distancia da borda superior

        # relwidth  -> distancia da borda direita   
        # relheight -> distancia da borda inferior
        
        # bg: cor de fundo frame
        # highlightbackground: cor da borda frame
        # highlightthickness: espessura da borda

        self.frame_campos = Frame(self.main, bd = 4, bg='#C0C0C0',highlightbackground='#E6E6FA', highlightthickness=1,)
        self.frame_campos.place(relx= 0.01, rely=0.01, relwidth=0.98, relheight=0.46)

        self.frame_lista = Frame(self.main, bd = 4, bg='#C0C0C0',highlightbackground='#E6E6FA', highlightthickness=2,)
        self.frame_lista.place(relx= 0.01, rely=0.58, relwidth=0.98, relheight=0.4)
    
    def widgets_frame_campos(self):

        self.bt_novo = Button(self.main, text="Novo")
        self.bt_novo.place(relx=0.02, rely=0.40, relwidth=0.1, relheight=0.06)

        self.bt_alterar = Button(self.main, text="Alterar")
        self.bt_alterar.place(relx=0.13, rely=0.40, relwidth=0.1, relheight=0.06)

        self.bt_excluir = Button(self.main, text="Excluir")
        self.bt_excluir.place(relx=0.24, rely=0.40, relwidth=0.1, relheight=0.06)

        self.bt_salvar = Button(self.main, text="Salvar")
        self.bt_salvar.place(relx=0.35, rely=0.40, relwidth=0.1, relheight=0.06)

        #Labels e Entry
        self.lbl_codigo = Label(self.frame_campos, text="Código Cliente", bg='#C0C0C0')
        self.lbl_codigo.place(relx=0.01, rely=0.01)

        self.codigo_entry = Entry(self.frame_campos)
        self.codigo_entry.place(relx=0.01, rely=0.10)
 
Application()