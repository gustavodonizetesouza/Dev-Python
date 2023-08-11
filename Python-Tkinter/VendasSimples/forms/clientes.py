from tkinter import *

master = Tk()

# Cores ----------------------
co0 = "#f0f3f5"  # Preto
co1 = "#f0f3f5"  # cinzeto / grey
co2 = "#feffff"  # Branco
co3 = "#38576b"  # Valor
co4 = "#403d3d"  # letras
co5 = "#6f9fbd"  # Azul
co6 = "#ef5350"  # verde


class Application():
    def __init__(self):
        self.master = master
        self.tela_principal()
        self.frames()
        self.widgets_frame_cima()
        self.widgets_frame_abaixo()
        self.botoes_frame_abaixo()
        master.mainloop()

    def tela_principal(self):
        self.master.title("Cadastro de Clientes")
        self.master.resizable(width=FALSE, height=FALSE)

        # dimensoes da janela
        largura = 1000
        altura = 550

        # resolução do nosso sistema
        largura_screen = master.winfo_screenwidth()
        altura_screen = master.winfo_screenheight()

        # posição da janela
        posx = largura_screen / 2 - largura / 2
        posy = altura_screen / 2 - altura / 2

        # definir geometry da tela
        self.master.geometry("%dx%d+%d+%d" % (largura, altura, posx, posy))

    def frames(self):
        # Frames----- configuração cores de fundo cabeçalho----------------
        self.frame_cima = Frame(self.master, width=1000,
                                height=50, bg=co3, relief="flat")
        self.frame_cima.grid(row=0, column=0, pady=1, padx=0, sticky=NSEW)

        # Frames----- configuração cores de fundo abaixo do cabeçalho----------------
        self.frame_baixo = Frame(
            self.master, width=1000, height=150, bg=co1, relief="flat")
        self.frame_baixo.grid(row=1, column=0, pady=1, padx=0, sticky=NSEW)

        # Frames----- configuração cores de fundo grid----------------
        self.frame_grid = Frame(self.master, width=1000,
                                height=350, bg=co2, relief="flat")
        self.frame_grid.grid(row=2, column=0, columnspan=2,
                             padx=2, pady=1, sticky=NW)

    def widgets_frame_cima(self):
        # Frames --------------Lablel Cadastro de Cliente no frama cabecalho----------
        self.l_nome = Label(self.frame_cima, text='Cadastro de Clientes',
                            anchor=NE, font=('arial 20 bold'), bg=co3, fg=co1)
        self.l_nome.place(x=5, y=5)
        # Frames --------------Linha de divisão entre Frame_Cima e o Frame_baixo----------
        self.l_linha = Label(self.frame_cima, text='', width=1000,
                             anchor=NE, font=('arial 1'), bg=co2, fg=co1)
        self.l_linha.place(x=0, y=46)

    def widgets_frame_abaixo(self):
        # Campo Nome do Cliente
        self.l_nome = Label(self.frame_baixo, text='Nome *',
                            anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_nome.place(x=5, y=5)
        self.nome_cliente_entry = Entry(
            self.frame_baixo, width=38, justify='left', font=('', 10), highlightthickness=1)
        self.nome_cliente_entry.place(x=5, y=25)

        # Campo Sexo do Cliente
        self.l_sexo = Label(self.frame_baixo, text='Sexo*',
                            anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_sexo.place(x=295, y=5)
        self.sexo_entry = Entry(self.frame_baixo, width=30)
        self.sexo_entry.place(x=295, y=25)

        # Campo Telefone do cliente
        self.l_telefone = Label(
            self.frame_baixo, text='Telefone*', anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_telefone.place(x=500, y=5)
        self.telefone_entry = Entry(
            self.frame_baixo, width=25, justify='left', font=('', 10), highlightthickness=1)
        self.telefone_entry.place(x=500, y=25)

        # Campo Email do Cliente
        self.l_cidade = Label(self.frame_baixo, text='Cidade*',
                              anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_cidade.place(x=5, y=50)
        self.cidade_entry = Entry(self.frame_baixo, width=67, justify='left', font=(
            '', 10), highlightthickness=1)
        self.cidade_entry.place(x=5, y=70)

        # Campo Codigo do cliente
        self.l_codigo = Label(self.frame_baixo, text='Codigo Cliente*',
                              anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_codigo.place(x=500, y=50)
        self.codigo_entry = Entry(
            self.frame_baixo, width=25, justify='left', font=('', 10), highlightthickness=1)
        self.codigo_entry.place(x=500, y=70)

    def botoes_frame_abaixo(self):
        # Campo Busca
        self.e_procurar = Entry(self.frame_baixo, width=34, justify='left', font=(
            '', 11), highlightthickness=1)
        self.e_procurar.place(x=5, y=120)

        # label e botão buscar dados
        self.l_pesquisa = Label(
            self.frame_baixo, text='Pesquisar*', anchor=NW, font=('Ivy 10'), bg=co1, fg=co4)
        self.l_pesquisa.place(x=5, y=98)

        self.b_ver = Button(self.frame_baixo, text='Buscar Dados', width=10, font=(
            'Ivy 8 bold'), bg=co2, fg=co4, relief=RAISED, overrelief=RIDGE) #command=self.lista_cliente)
        self.b_ver.place(x=290, y=120)

        # Campo Adicionar
        self.b_adicionar = Button(self.frame_baixo, text='Adicionar', width=10, font=(
            'Ivy 8 bold'), bg=co2, fg=co4, relief=RAISED, overrelief=RIDGE)# command=self.adicionar_novo_cliente)
        self.b_adicionar.place(x=430, y=120)

        # Campo Atualizar
        self.b_Atualizar = Button(self.frame_baixo, text='Atualizar', width=10, font=(
            'Ivy 8 bold'), bg=co2, fg=co4, relief=RAISED, overrelief=RIDGE)#, command=self.update)
        self.b_Atualizar.place(x=520, y=120)

        # Campo Deletar
        self.b_Deletar = Button(self.frame_baixo, text='Deletar', width=10, font=(
            'Ivy 8 bold'), bg=co2, fg=co4, relief=RAISED, overrelief=RIDGE)#, command=self.delete)
        self.b_Deletar.place(x=608, y=120)


Application()
