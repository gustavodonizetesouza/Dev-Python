#idade = "37"
#txt = "Me chamo Gustavo e tenho" + id # não pode ser feito, gera errado
#print(txt)

idade = "37"
txt = "Me chamo Gustavo e tenho {} anos de idade"
print(txt.format(idade))# as {} permite combinar as string com valores numericos

print("-------------------------------------------------")

qte = 3
item = "bolo"
valor = 14.99
pedido = "Eu quero {} pedaço de {} por {} reais."
print(pedido.format(qte, item, valor))

print("-------------------------------------------------")

qte = 3
item = "bolo"
valor = 14.99
pedido = "Eu quero {2} reais pelos {0} pedaços {1}."
print(pedido.format(qte, item, valor))