# ============================================================
# CONFIGURAÇÃO DE CONEXÃO - SQL SERVER (Protheus)
# Edite apenas este arquivo com os dados do seu ambiente
# ============================================================

SERVER = "10.84.37.42\\DB01"          # ex: "10.0.0.15" ou "srv-protheus"
DATABASE = "DADOSADV11"            # nome do banco de dados
USERNAME = "CONSULTA"             # usuário com permissão de leitura
PASSWORD = "polycons2008"               # senha
DRIVER = "ODBC Driver 18 for SQL Server"   # ou "ODBC Driver 17 for SQL Server"

# String de conexão montada automaticamente
CONNECTION_STRING = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
    f"TrustServerCertificate=yes;"
    f"Connection Timeout=30;"
)
