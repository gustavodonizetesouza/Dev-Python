a = 'Gustavo'
b = 'Seja Bem Vido'
c = '''Gustavo Donizete de Souza
        Rua Vereador Antonio Pavan Capatti, 65
        São Sebastião do Paraiso
        Minas Gerais - 37.950-000 '''

print(c)

print('----------------------------------------------')

print(c[2]) # Imprime apenas a letra da posição da variavel

print('----------------------------------------------')

for x in "Gustavo": # o sistema irá varrer toda a variavel
    print(x + " - ")

print('----------------------------------------------')

x = len(c) # len realiza a contagem de caracteres
print(x)

print('----------------------------------------------')

txt = " Seja bem vindo ao curso de Python."

x = "vindo" in txt # in retorna se o valor vindo contem no texto da variavel x -> trabalha como estrutura de condição
print(x)

y = "CSharp" in txt
print(y)

print ("JavaScript" in txt)

print('----------------------------------------------')

if "vindo" in txt:
    print("Sim, 'vindo' está presente")

if "JavaScript" not in txt:
    print("'JavaScript' não está presente")