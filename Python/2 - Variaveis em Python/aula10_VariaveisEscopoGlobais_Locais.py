# Variaves fora do escopo do bloco de código é global

# Variaveis dentro do escopo do bloco de código é local


x = 'incrivel'  # Variael Global
y = ' demais da conta' # Variael Global

def myFunc():  # Criação da Função - Bloco de códigos
    global w
    w = 'Fantastico'
    print("Python é " + x + y +". "+ w)


def myFunc1():
    x = 'muito '  # Variael Escopo
    y = 'bom demais da conta' # Variael de Escopo

    print('Python é ' + x + y)

myFunc()  # execução da função
myFunc1()# execução da função


print('Você é:' + x + y + ". " + w)
