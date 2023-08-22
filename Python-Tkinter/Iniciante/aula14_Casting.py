# int() - constrói um número inteiro a partir de um literal inteiro, um literal flutuante (removendo todos os decimais) ou um literal de string (desde que a string represente um número inteiro)

# float() - constrói um número flutuante a partir de um literal inteiro, um literal flutuante ou um literal de string (desde que a string represente um flutuante ou um inteiro)

# str() - constrói uma string a partir de uma ampla variedade de tipos de dados, incluindo strings, literais inteiros e literais flutuantes

x = int(1)   # Será 1
y = int(2.8) # Será 2
z = int("3") # Será 3
print(x)
print(y)
print(z)

x = float(1)     # Será 1.0
y = float(2.8)   # Será 2.8
z = float("3")   # Será 3.0
w = float("4.2") # Será 4.2
print(x)
print(y)
print(z)
print(w)

x = str("s1") # Será 's1'
y = str(2)    # Será '2'
z = str(3.0)  # Será '3.0'
print(x)
print(y)
print(z)
