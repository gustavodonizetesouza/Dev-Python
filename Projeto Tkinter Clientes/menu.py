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

    #variaveis cadastro cliente
    def variaveis(self):
        self.codigo = self.codigo_entry.get()
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
    
    #Inseri cadastro clientes no banco
    def create_cliente(self):
        self.variaveis()
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
    
    #Função para duplo click na linha e preencher os campos
    def OnDoubleClik(self, event):
        self.limpa_campos()
        self.listaCliente.selection()

        for n in self.listaCliente.selection():
            col1, col2, col3 = self.listaCliente.item(n,'value')
            self.codigo_entry.insert(END, col1)
            self.nome_cliente_entry.insert(END, col2)
            self.cidade_entry.insert(END, col3)
    
    #deletar clientes
    def delete_cliente(self):
        self.variaveis()
        self.concta_banco_dados()
        comando = f'DELETE FROM cliente WHERE cliente_id = "{self.codigo}"'
        self.cursor.execute(comando)
        self.conn.commit()
        self.desconectar_banco_dados()
        self.limpa_campos()
        self.read_cliente()
    
    #atualizar dados do cliente
    def update_cliente(self):
        self.variaveis()
        self.concta_banco_dados()
        comando = f'UPDATE cliente SET cliente = "{self.nome_cliente}", data_nascimento = "{self.data_nascimento}", cpf = "{self.cpf}", rg = "{self.rg}", cep = "{self.cep}", endereco = "{self.endereco}", numero = "{self.numero}", bairro = "{self.bairro}", cidade =  "{self.cidade}", estado = "{self.estado}" WHERE cliente_id = "{self.codigo}"'
        self.cursor.execute(comando)
        self.conn.commit()
        self.desconectar_banco_dados()
        self.limpa_campos()
        self.read_cliente()


                                                    
class Application(Funcoes):
    def __init__(self):
        self.main = main
        self.tela()       
       
        self.menus()
        main.mainloop()

    def tela(self): # contrução da tela

        main.title("Menu Principal")
        # master.geometry("700x450+420+170")
        main.resizable(width=FALSE, height=FALSE)
        #master.iconbitmap(default="icones\\icone_menu.ico")

        # dimensoes da janela
        largura = 1082
        altura = 607

        # resolução do nosso sistema
        largura_screen = main.winfo_screenwidth()
        altura_screen = main.winfo_screenheight()

        # posição da janela
        posx = largura_screen/2 - largura/2
        posy = altura_screen/2 - altura/2

        # definir geometry
        main.geometry("%dx%d+%d+%d" % (largura, altura, posx, posy))
    
    def menus(self):
        menubar = Menu(self.main)
        self.main.config(menu=menubar)
        filemenu = Menu(menubar)
        filemenu2 = Menu(menubar)
        filemenu3 = Menu(menubar)

        def Quit(): self.main.destroy() 

        menubar.add_cascade(label="Opções", menu= filemenu)
        menubar.add_cascade(label="Sobre", menu= filemenu2)
        menubar.add_cascade(label="Finalizar", menu=filemenu3)
       
        filemenu.add_command(label= "Listar Cliiente", command=self.read_cliente)
        filemenu2.add_command(label= "Sobre App")
        filemenu3.add_command(label= "Encerrar App", command=Quit)

    

Application()