from tkinter import *
from tkinter import ttk

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
        self.main.geometry("1082x607")

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
        self.frame_lista.place(relx= 0.01, rely=0.55, relwidth=0.98, relheight=0.44)
    
    def widgets_frame_campos(self):

        self.bt_novo = Button(self.main, text="Novo", bd=2, fg='blue', font=('verdana', 8, 'bold'))
        self.bt_novo.place(relx=0.02, rely=0.41, relwidth=0.1, relheight=0.05)

        self.bt_alterar = Button(self.main, text="Alterar", bd=2, fg='blue', font=('verdana', 8, 'bold'))
        self.bt_alterar.place(relx=0.13, rely=0.41, relwidth=0.1, relheight=0.05)

        self.bt_excluir = Button(self.main, text="Excluir", bd=2, fg='blue', font=('verdana', 8, 'bold'))
        self.bt_excluir.place(relx=0.24, rely=0.41, relwidth=0.1, relheight=0.05)

        self.bt_salvar = Button(self.main, text="Salvar", bd=2, fg='blue', font=('verdana', 8, 'bold'))
        self.bt_salvar.place(relx=0.35, rely=0.41, relwidth=0.1, relheight=0.05)

        #Labels e Entry
        ## ------Código Cliente
        self.lbl_codigo = Label(self.frame_campos, text="Código Cliente", bg='#C0C0C0')
        self.lbl_codigo.place(relx=0.01, rely=0.02, )
        
        self.codigo_entry = Entry(self.frame_campos)
        self.codigo_entry.place(relx=0.01, rely=0.09, relwidth=0.08)
       
        ## ------Nome Cliente Cliente
        self.lbl_nome_cliente = Label(self.frame_campos, text="Nome Cliente", bg='#C0C0C0')
        self.lbl_nome_cliente.place(relx=0.10, rely=0.02)

        self.nome_cliente_entry = Entry(self.frame_campos)
        self.nome_cliente_entry.place(relx=0.10, rely=0.09, relwidth=0.34)
        
        ## ------Data Nascimento Cliente
        self.lbl_data_nascimento = Label(self.frame_campos, text="Data Nascimento", bg='#C0C0C0')
        self.lbl_data_nascimento.place(relx=0.45, rely=0.02)

        self.data_nascimento_entry = Entry(self.frame_campos)
        self.data_nascimento_entry.place(relx=0.45, rely=0.09)

        ## ------CPF
        self.lbl_cpf = Label(self.frame_campos, text="CPF", bg='#C0C0C0')
        self.lbl_cpf.place(relx=0.58, rely=0.02)

        self.cpf_entry = Entry(self.frame_campos)
        self.cpf_entry.place(relx=0.58, rely=0.09)

        ## ------RG
        self.lbl_rg = Label(self.frame_campos, text="RG", bg='#C0C0C0')
        self.lbl_rg.place(relx=0.71, rely=0.02)

        self.rg_entry = Entry(self.frame_campos)
        self.rg_entry.place(relx=0.71, rely=0.09)

        # ------CEP
        self.lbl_cep = Label(self.frame_campos, text="CEP", bg='#C0C0C0')
        self.lbl_cep.place(relx=0.01, rely=0.25)

        self.cep_entry = Entry(self.frame_campos)
        self.cep_entry.place(relx=0.01, rely=0.31, relwidth=0.08)

        # ------Endereço
        self.lbl_endereco = Label(self.frame_campos, text="Endereço", bg='#C0C0C0')
        self.lbl_endereco.place(relx=0.10, rely=0.25)

        self.endereco_entry = Entry(self.frame_campos)
        self.endereco_entry.place(relx=0.10, rely=0.31, relwidth=0.34)

        # ------numero
        self.lbl_numero = Label(self.frame_campos, text="Numero", bg='#C0C0C0')
        self.lbl_numero.place(relx=0.45, rely=0.25)

        self.numero_entry = Entry(self.frame_campos)
        self.numero_entry.place(relx=0.45, rely=0.31, relwidth=0.08)

        # ------bairro
        self.lbl_bairro = Label(self.frame_campos, text="Bairro", bg='#C0C0C0')
        self.lbl_bairro.place(relx=0.54, rely=0.25)

        self.bairro_entry = Entry(self.frame_campos)
        self.bairro_entry.place(relx=0.54, rely=0.31, relwidth=0.16)
        
        # ------ciade
        self.lbl_cidade = Label(self.frame_campos, text="Cidade", bg='#C0C0C0')
        self.lbl_cidade.place(relx=0.71, rely=0.25)

        self.cidade_entry = Entry(self.frame_campos)
        self.cidade_entry.place(relx=0.71, rely=0.31, relwidth=0.18)

        # ------Estado
        self.lbl_estado = Label(self.frame_campos, text="Estado", bg='#C0C0C0')
        self.lbl_estado.place(relx=0.90, rely=0.25)

        self.estado_entry = Entry(self.frame_campos)
        self.estado_entry.place(relx=0.90, rely=0.31, relwidth=0.10)

        self.lbl_lista_clientes = Label(self.main, text="Lista de Clientes Cadastrados", bg='#D3D3D3', font=('verdana', 25, 'bold'))
        self.lbl_lista_clientes.place(relx=0.01, rely=0.490, relwidth=0.510, relheight=0.05)

    def lista_cliente(self):
        self.listaCliente = ttk.Treeview(self.lista_cliente, height=3, columns=("col1", "col2", "col3", "col4"))


Application()