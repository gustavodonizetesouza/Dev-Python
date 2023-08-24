import os 

os.system("cls") or None

##Entrada de Dados
num1 = input("Digite o primeiro numero: ")
num1 = int(num1)

num2 = input("Digite o segundo numero: ")
num2 = int(num2)

# Processamento de dados
mult = num1 * num2

# Sainda das informações processadas
print()
print("A multiplicação de", num1, "por", num2, "é:", mult)