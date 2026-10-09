"""Gestão de senhas das conexões usando Keyring (cofre do sistema)."""
import base64

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

SERVICE = "GerenciadorTestesEssencial"


def salvar_senha(conexao_id, senha):
    """Guarda a senha no cofre do sistema (Keyring)."""
    if not senha:
        return
    if HAS_KEYRING:
        keyring.set_password(SERVICE, str(conexao_id), senha)
    else:
        _salvar_fallback(conexao_id, senha)


def obter_senha(conexao_id, senha_armazenada=None):
    """Recupera a senha. Retorna None se não houver."""
    if HAS_KEYRING:
        return keyring.get_password(SERVICE, str(conexao_id))
    if senha_armazenada:
        try:
            return base64.b64decode(senha_armazenada).decode()
        except Exception:
            return None
    return None


def _salvar_fallback(conexao_id, senha):
    """Guarda em base64 na própria linha (somente se Keyring ausente)."""
    import sqlite3
    from pathlib import Path
    from database.connection import CONFIG_DB_PATH
    conn = sqlite3.connect(CONFIG_DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE conexoes SET senha=? WHERE id=?",
                (base64.b64encode(senha.encode()).decode(), conexao_id))
    conn.commit()
    conn.close()
