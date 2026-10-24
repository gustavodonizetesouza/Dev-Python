"""Hash e verificação de senhas — PBKDF2-HMAC-SHA256 (biblioteca padrão).

Formato armazenado: pbkdf2_sha256$<iterações>$<salt_hex>$<hash_hex>
Mesmo algoritmo usado pelo ASP.NET Identity (PBKDF2) — o hash é portável
conceitualmente para a versão web. Sem dependências externas.
"""
import hashlib
import hmac
import os

_ITERACOES = 100_000


def hash_senha(senha):
    """Gera o hash PBKDF2 da senha com salt aleatório de 16 bytes."""
    senha_bytes = (senha or "").encode("utf-8")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha_bytes, salt, _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${salt.hex()}${dk.hex()}"


def verificar_senha(senha, armazenada):
    """Verifica a senha contra o hash armazenado (comparação em tempo constante)."""
    try:
        algo, iters, salt_hex, hash_hex = (armazenada or "").split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", (senha or "").encode("utf-8"),
            bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False
