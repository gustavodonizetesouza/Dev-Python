x = ["apple", "banana"]
y = ["apple", "banana"]

z = x 

print( x is z) # x é z pois tem mesma referencia de objeto
print("--------------------------------------------------------------------")

print(x is y) # x é y -> não é pois tem o mesmos valores mais não é o mesmo objeto
print("--------------------------------------------------------------------")

print(x == y) # x é igual a y -> sim, pois tem o mesmo conteudo
print("--------------------------------------------------------------------")

print( x is not z) # x não é z -> erro, x é y 
print("--------------------------------------------------------------------")

print(x is not y) # x é y -> exato x não é y nesta situação
print("--------------------------------------------------------------------")

print(x != y) # x é y ->errado, são iguais
print("--------------------------------------------------------------------")