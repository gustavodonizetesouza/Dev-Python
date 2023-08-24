# Caractere de Scape representa caracteres especiais, que não pode se inseridos

# txt = "Somo os chamados "vikings" do norte." # forma que irá da erro

txt = "Somo os chamados \"vikings\" do norte."
print(txt)

print("--------------------------------------------------------------")

txt = "Ola \nMundo!"
print(txt)  # quebra de linha

print("--------------------------------------------------------------")

txt = "Ola \rMundo!"
print(txt)  # retira o que está a frente da Caractere de escape

print("--------------------------------------------------------------")

txt = "Ola \tMundo!"
print(txt)  # tabulação, como se tivesse acinado a tecla tab do teclado

print("--------------------------------------------------------------")

# Barra Invertida, é necessário colocar duas para dar certo no código
txt = "Isso irá inserir uma \\"
print(txt)

print("--------------------------------------------------------------")

txt = "Ola\'s Mundo!"
print(txt)  # insere uma aspas simples.

print("--------------------------------------------------------------")

txt = "Ola \bMundo!"
print(txt)  # apaga o espaço antrior

print("--------------------------------------------------------------")

txt = "\x48\x65\x6c\x6f "
print(txt)  # uma barra intertida seguida por x é um numero exdecimal nno caso formaando uma palavra

print("--------------------------------------------------------------")

txt = "\110\145\154\157"
print(txt)  # uma barra intertida seguida por 3  numeros inteiros resulta em um octal
