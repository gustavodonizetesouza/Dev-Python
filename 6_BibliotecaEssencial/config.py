# ============================================
# config.py
# Centraliza as configurações do sistema.
# Lê as credenciais do banco a partir do arquivo .env.
# Inclui DETECÇÃO AUTOMÁTICA do driver ODBC:
# se o driver configurado não existir na máquina,
# usa o melhor driver SQL Server instalado.
#
# Conexão de referência (mesma do ASP.NET):
#   Server=34.112.39.100,1433; Database=WapGestorEssenc;
#   user=GestorEssenc; TrustServerCertificate=True
# ============================================
import os
import pyodbc
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()


def detectar_driver() -> str:
    """Retorna o melhor driver ODBC SQL Server instalado na máquina.

    Ordem de preferência: 18, 17, 13, Native Client, SQL Server.
    Se nenhum for encontrado, retorna o nome do 18 (o erro
    resultante deixará claro que falta instalar o driver).
    """
    preferidos = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]
    instalados = pyodbc.drivers()
    for nome in preferidos:
        if nome in instalados:
            return nome
    # Fallback: qualquer driver que contenha "SQL Server"
    for nome in instalados:
        if "SQL Server" in nome:
            return nome
    return preferidos[0]


class Config:
    # Dados de conexão com o SQL Server (vindos do .env)
    # Formato do servidor: "IP,porta" (ex.: 34.112.39.100,1433)
    SERVER = os.getenv("DB_SERVER", "24.152.39.128,1433")
    DATABASE = os.getenv("DB_DATABASE", "WapBibliotecaEssencialApp")
    USERNAME = os.getenv("DB_USER", "BibliotecaEssencialApp")
    PASSWORD = os.getenv("DB_PASSWORD", "$1305Wap2023*")

    # Driver ODBC: usa o do .env se informado; senão, detecta automaticamente
    DRIVER = os.getenv("DB_DRIVER") or detectar_driver()

    # Criptografia da conexão
    # ENCRYPT=yes exige certificado; TRUST_CERT=yes aceita sem validar
    ENCRYPT = os.getenv("DB_ENCRYPT", "yes")
    TRUST_CERT = os.getenv("DB_TRUST_CERT", "yes")

    @staticmethod
    def connection_string() -> str:
        """Monta a string de conexão usada pelo pyodbc."""
        return (
            f"DRIVER={{{Config.DRIVER}}};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            f"UID={Config.USERNAME};"
            f"PWD={Config.PASSWORD};"
            f"Encrypt={Config.ENCRYPT};"
            f"TrustServerCertificate={Config.TRUST_CERT};"
        )