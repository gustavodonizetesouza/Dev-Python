# ============================================
# config.py
# Centraliza as configurações do sistema.
# Lê as credenciais do banco a partir do arquivo .env
# (nunca deixe senha escrita no código).
# ============================================
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()


class Config:
    # Dados de conexão com o SQL Server (vindos do .env)
    SERVER = os.getenv("DB_SERVER", "24.152.39.128,1433\\MSSQLSERVER2022")
    DATABASE = os.getenv("DB_DATABASE", "WapBibliotecaEssencialApp")
    USERNAME = os.getenv("DB_USER", "BibliotecaEssencialAp")
    PASSWORD = os.getenv("DB_PASSWORD", "$1305Wap2023*")
    DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    ENCRYPT = os.getenv("DB_ENCRYPT", "yes")
    TRUST_CERT = os.getenv("DB_TRUST_CERT", "no")

    @staticmethod
    def connection_string() -> str:
        return (
            f"DRIVER={{{Config.DRIVER}}};"
            f"SERVER={Config.SERVER};"
            f"DATABASE={Config.DATABASE};"
            f"UID={Config.USERNAME};"
            f"PWD={Config.PASSWORD};"
            f"Encrypt={Config.ENCRYPT};"
            f"TrustServerCertificate={Config.TRUST_CERT};"
        )
