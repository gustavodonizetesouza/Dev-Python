"""Gestão de senhas das conexões usando Keyring (cofre do sistema)."""
import base64

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

SERVICE = "GerenciadorTestesEssencial"


def salvar_senha(conexao_id, senha):
    """Guarda a senha no cofre (Keyring). Nunca trava: em qualquer falha,
    cai para o fallback em base64 na própria linha de conexão."""
    if not senha:
        return
    if HAS_KEYRING:
        try:
            keyring.set_password(SERVICE, str(conexao_id), senha)
            return
        except Exception:
            # Se o Keyring falhar (backend ausente/prompt travando),
            # usa o fallback silencioso — o app nunca congela por causa de senha.
            pass
    _salvar_fallback(conexao_id, senha)


def obter_senha(conexao_id, senha_armazenada=None):
    """Recupera a senha. Retorna None se não houver."""
    if HAS_KEYRING:
        try:
            valor = keyring.get_password(SERVICE, str(conexao_id))
            if valor:
                return valor
        except Exception:
            pass
    if senha_armazenada:
        try:
            return base64.b64decode(senha_armazenada).decode()
        except Exception:
            return None
    return None


def _salvar_fallback(conexao_id, senha):
    """Guarda em base64 na própria linha (somente se Keyring ausente/falhou)."""
    import sqlite3
    from pathlib import Path
    from database.connection import CONFIG_DB_PATH
    conn = sqlite3.connect(CONFIG_DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE conexoes SET senha=? WHERE id=?",
                (base64.b64encode(senha.encode()).decode(), conexao_id))
    conn.commit()
    conn.close()
