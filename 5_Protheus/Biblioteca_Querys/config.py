# ============================================================
# config.py - Configuração de conexão com o banco
#   - Lê e grava em config.json (editável pela tela Configurações)
#   - Monta a connection string usada pelo pyodbc
#   - Normaliza o nome do servidor (evita erro de barra dupla)
# ============================================================
import json
import os

ARQUIVO_CONFIG = "config.json"

CONFIG_PADRAO = {
    "server": "",
    "database": "",
    "username": "",
    "password": "",
    "driver": "ODBC Driver 18 for SQL Server",
    "trust_certificate": True,
    "timeout": 30,
}


def normalizar_servidor(valor: str) -> str:
    """
    Colapsa barras duplicadas no nome do servidor e remove espaços.
    '10.84.37.42\\\\DB01' -> '10.84.37.42\\DB01'
    """
    if not valor:
        return ""
    valor = valor.strip()
    while "\\\\" in valor:
        valor = valor.replace("\\\\", "\\")
    return valor


def carregar_config() -> dict:
    """Carrega as configurações do config.json (ou padrões na 1ª vez)."""
    cfg = dict(CONFIG_PADRAO)
    if os.path.exists(ARQUIVO_CONFIG):
        try:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                dados = json.load(f)
            cfg.update({k: v for k, v in dados.items() if k in cfg})
        except Exception:
            pass
    return cfg


def salvar_config(cfg: dict):
    """Grava as configurações no config.json (normalizando o servidor)."""
    dados = {k: cfg.get(k, v) for k, v in CONFIG_PADRAO.items()}
    dados["server"] = normalizar_servidor(dados.get("server", ""))
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def montar_connection_string(cfg: dict = None) -> str:
    """Monta a connection string para o pyodbc a partir da configuração."""
    cfg = cfg or carregar_config()
    server = normalizar_servidor(cfg.get("server", ""))
    trust = "yes" if cfg.get("trust_certificate", True) else "no"
    return (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={server};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"TrustServerCertificate={trust};"
        f"Connection Timeout={cfg.get('timeout', 30)};"
    )
