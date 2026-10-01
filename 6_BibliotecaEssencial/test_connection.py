# ============================================
# test_connection.py
# Diagnóstico de conexão com o SQL Server.
# Testa, em ordem: driver ODBC, resolução do host,
# porta 1433 (TCP) e conexão pyodbc completa.
# Uso: python test_connection.py
# ============================================
import socket
import pyodbc
from config import Config


def testar_driver():
    print("1) Verificando driver ODBC instalado...")
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        print("   ❌ Nenhum driver SQL Server encontrado.")
        print("   Instale o ODBC Driver for SQL Server:")
        print("   https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server")
        return False
    print("   ✅ Drivers encontrados:")
    for d in drivers:
        print(f"      - {d}")
    return True


def testar_host():
    print("2) Resolvendo o host do servidor...")
    servidor = Config.SERVER
    host = servidor.split(",")[0].strip()  # remove a porta, se informada
    try:
        ip = socket.gethostbyname(host)
        print(f"   ✅ Host resolvido: {host} -> {ip}")
        return True
    except socket.gaierror:
        print(f"   ❌ Não foi possível resolver o host: {host}")
        print("   Verifique o valor de DB_SERVER no arquivo .env")
        return False


def testar_porta():
    print("3) Testando acesso à porta 1433 (padrão SQL Server)...")
    servidor = Config.SERVER
    host = servidor.split(",")[0].strip()
    try:
        with socket.create_connection((host, 1433), timeout=5):
            print("   ✅ Porta 1433 acessível. Servidor alcançável na rede.")
        return True
    except Exception as e:
        print(f"   ❌ Falha ao conectar na porta 1433: {e}")
        print("   Causas mais comuns:")
        print("      - Firewall do Azure: o IP público da sua rede não está liberado")
        print("        nas regras de firewall do SQL Server (portal Azure)")
        print("      - SQL Server com 'Allow Azure services' desabilitado")
        print("      - Porta diferente da 1433 (use SERVIDOR,porta no DB_SERVER do .env)")
        print("      - Firewall/VPN local bloqueando a saída")
        return False


def testar_conexao():
    print("4) Tentando conexão pyodbc completa...")
    try:
        conn = pyodbc.connect(Config.connection_string(), timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        versao = cursor.fetchone()[0]
        print("   ✅ Conexão OK!")
        print(f"      Versão do SQL Server: {versao.splitlines()[0]}")
        cursor.close()
        conn.close()
        return True
    except pyodbc.Error as e:
        print(f"   ❌ Erro pyodbc: {e}")
        args = e.args[0] if e.args and isinstance(e.args[0], dict) else {}
        codigo = args.get("code", "n/d")
        print(f"      Código nativo: {codigo}")
        print("      Dica: se o erro citar certificado/criptografia,")
        print("      ajuste DB_TRUST_CERT=yes no arquivo .env")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("  DIAGNÓSTICO DE CONEXÃO - Biblioteca Essencial")
    print("=" * 60)
    r1 = testar_driver()
    print()
    r2 = testar_host()
    print()
    r3 = testar_porta()
    print()
    r4 = testar_conexao()
    print()
    print("=" * 60)
    print("RESULTADO FINAL")
    print(f"  Driver ODBC:  {'✅ OK' if r1 else '❌ FALHOU'}")
    print(f"  Host:         {'✅ OK' if r2 else '❌ FALHOU'}")
    print(f"  Porta 1433:   {'✅ OK' if r3 else '❌ FALHOU'}")
    print(f"  Conexão:      {'✅ OK' if r4 else '❌ FALHOU'}")
    print("=" * 60)