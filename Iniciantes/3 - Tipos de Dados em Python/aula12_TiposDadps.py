# Tipo de texto:       str
# Tipo numérico:       int, float, omplex
# Tipos de sequencias: list, tuple, range
# Tipos de Mapeamento: dict
# Tpos de conjunto:    bool
# Tipos binários:       bytes, bytearray, memoryview

# Definir o tipo de dados

a = "Hello Word"  # -> str
b = 20           # -> int
c = 20.5         # -> float
d = 1j           # -> complex

e = ["amarelo", "verde", "branco"]      # -> list
f = ("azul", "preto", "roxo")           # -> tuple
g = range(6)                            # -> range
h = {"name": "Gustavo", "age": "37"}  # -> dict

i = {"morango", "banana", "uva"}        # -> set
j = frozenset({"acabate", "abacaxi", "maça"})  # frozenset
k = True  # bool
l = b"Hello"  # bytes
m = bytearray(5)  # bytearray
n = memoryview(bytes(5))  # memoryiew

# Configurando o Tipo de Dados Específico

x = str("Hello World")  # str
x = int(20)  # int
x = float(20.5)  # float
x = complex(1j)  # complex
x = list(("apple", "banana", "cherry"))  # list
x = tuple(("apple", "banana", "cherry"))  # tuple
x = range(6)  # range
x = dict(name="John", age=36)  # dict
x = set(("apple", "banana", "cherry"))  # set
x = frozenset(("apple", "banana", "cherry"))  # frozenset
x = bool(5)  # bool
x = bytes(5)  # bytes
x = bytearray(5)  # bytearray
x = memoryview(bytes(5))  # memoryview

x = "20"
print(x)
print(type(x))

x = int("20")
print(type(x))
