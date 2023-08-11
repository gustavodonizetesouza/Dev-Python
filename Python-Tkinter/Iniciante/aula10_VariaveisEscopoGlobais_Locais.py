# Variaves fora do escopo do bloco de código é global

# Variaveis dentro do escopo do bloco de código é local


x = 'incrivel'


def myFunc(): # Criação da Função - Bloco de códigos
    print ("Python é " + x) 


myFunc() # execução da função


print('Você é:' + x)




