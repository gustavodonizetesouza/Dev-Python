"""Hash e verificação de senhas — PBKDF2-HMAC-SHA256 (nativo, zero dependências).

Formato armazenado: pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>
Mesmo padrão conceitual do Django; em C# o equivalente é Rfc2898DeriveBytes
(PBKDF2), o que deixa o port para ASP.NET Core alinhado.
"""
import hashlib
import hmac
import secrets

ITERACOES = 120_000
TAM_SALT = 16  # bytes


def hash_senha(senha: str) -> str:
    """Gera o hash com salt aleatório de 16 bytes e 120k iterações."""
    salt = secrets.token_bytes(TAM_SALT)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt, ITERACOES)
    return f"pbkdf2_sha256${ITERACOES}${salt.hex()}${derivado.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    """Verifica a senha contra o hash armazenado (comparação em tempo constante)."""
    try:
        algoritmo, iteracoes, salt_hex, hash_hex = armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        derivado = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), bytes.fromhex(salt_hex), int(iteracoes))
        return hmac.compare_digest(derivado.hex(), hash_hex)
    except (ValueError, AttributeError, TypeError):
        return False


def validar_senha_forte(senha: str):
    """Regra mínima de senha. Retorna mensagem de erro ou None se OK."""
    if len(senha or "") < 6:
        return "A senha deve ter pelo menos 6 caracteres."
    return None
