from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token(usuario_id: int) -> str:
    expiracao = datetime.now(timezone.utc) + \
        timedelta(minutes=settings.token_expire_minutes)
    return jwt.encode({"sub": str(usuario_id), "exp": expiracao}, settings.secret_key, algorithm=ALGORITHM)


def decodificar_token(token: str) -> int:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    return int(payload["sub"])
