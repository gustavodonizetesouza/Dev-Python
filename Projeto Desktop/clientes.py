from tkinter import *
from tkinter import ttk
import mysql.connector

main = Tk()

class Funcoes():
    #Limpa os dados contidos nos campos de cadastro
    def limpa_campos(self):
        self.codigo_entry.delete(0, END)
        self.nome_cliente_entry.delete(0, END)
        self.data_nascimento_entry.delete(0, END)
        self.cpf_entry.delete(0, END)
        self.rg_entry.delete(0, END)
        self.cep_entry.delete(0, END)
        self.endereco_entry.delete(0, END)
        self.numero_entry.delete(0, END)
        self.bairro_entry.delete(0, END)
        self.cidade_entry.delete(0, END)
        self.estado_entry.delete(0, END) 

    #Conexao com o banco de dados
    def concta_banco_dados(self):
        self.conn = mysql.connector.connect(
            host='mysql248.umbler.com', user='wapsi', password='p28042019g*', db='gestao_essencial', port=41890)
        self.cursor = self.conn.cursor()
        print("Conectando ao banco de dados")

    #Fecha a conexao com o banco de dados
    def desconectar_banco_dados(self):
        self.conn.close()
        print("Desconectando o banco de dados")

    #Inseri cadastro clientes no banco
    def create_cliente(self):
        self.nome_cliente = self.nome_cliente_entry.get()
        self.data_nascimento = self.data_nascimento_entry.get()
        self.cpf = self.cpf_entry.get()
        self.rg = self.rg_entry.get()
        self.cep = self.cep_entry.get()
        self.endereco = self.endereco_entry.get()
        self.numero = self.numero_entry.get()
        self.bairro = self.bairro_entry.get()
        self.cidade = self.cidade_entry.get()
        self.estado = self.estado_entry.get()

        self.concta_banco_dados()
        comando = f'INSERT INTO cliente (cliente, data_nascimento, cpf, rg, cep, endereco, numero, bairro, cidade, estado) VALUE ("{self.nome_cliente}","{self.data_nascimento}", "{self.cpf}", "{self.rg}","{self.cep}", "{self.endereco}", "{self.numero}", "{self.bairro}", "{self.cidade}", "{self.estado}")'
        self.cursor.execute(comando)
        self.conn.commit()
        self.desconectar_banco_dados()
        self.limpa_campos()
        self.read_cliente()

    #Lista clientes cadastrados no banco
    def read_cliente(self):
        self.listaCliente.delete(*self.listaCliente.get_children())
        self.concta_banco_dados()

        comando = f'SELECT cliente_id, cliente, cidade FROM cliente;'
        self.cursor.execute(comando)
        lista = self.cursor.fetchall()
        print(lista)
        for i in lista:
            self.listaCliente.insert("", END, values=i)

        self.desconectar_banco_dados()

    def OnDoubleClik(self):
        self.limpa_campos()
        self.listaCliente.selection()

        for n in self.listaCliente.selection():
            col1, col2, col3 = self.listaCliente.item(n,'value')
            self.codigo_entry.insert(END, col1)
            self.nome_cliente_entry.insert(END, col2)
            self.cidade_entry.insert(END, col3)

    def

                                                    
class Application(Funcoes):
    def __init__(self):
        self.main = main
        self.tela()
        self.frame_tela()
        self.widgets_frame_campos()
        self.lista_cliente()
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

        self.bt_salvar = Button(self.main, text="Salvar", bd=2, fg='blue', font=('verdana', 8, 'bold'), command=self.create_cliente)
        self.bt_salvar.place(relx=0.35, rely=0.41, relwidth=0.1, relheight=0.05)

        self.bt_limpar = Button(self.main, text="Limpar", bd=2, fg='blue', font=('verdana', 8, 'bold'), command=self.limpa_campos)
        self.bt_limpar.place(relx=0.46, rely=0.41, relwidth=0.1, relheight=0.05)

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
    
        #Criando o Grid e informando a quantidade de colunas        
        self.listaCliente = ttk.Treeview(self.frame_lista, height=3, columns=("col1", "col2", "col3"))
        
        #Especificando o cabeçalho
        self.listaCliente.heading("#0", text="")
        self.listaCliente.heading("#1", text="Código")
        self.listaCliente.heading("#2", text="Nome")
        self.listaCliente.heading("#3", text="Cidade")
        

        #Definindo o espaço das colunas
        self.listaCliente.column("#0", width=1)
        self.listaCliente.column("#1", width=1)
        self.listaCliente.column("#2", width=350)
        self.listaCliente.column("#3", width=90)
        
        
        #Definindo a posição do Treeview
        self.listaCliente.place(relx=0.01, rely=0.01, relwidth=0.97, relheight=0.99)

        #barra de rolagem vertical
        self.scroolista = Scrollbar(self.frame_lista, orient='vertical')
        self.listaCliente.configure(yscroll=self.scroolista.set)
        self.scroolista.place(relx=0.98, rely=0.01, relwidth=0.02, relheight=0.99)



Application()