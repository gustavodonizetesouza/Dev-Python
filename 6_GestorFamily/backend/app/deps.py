from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario
from .security import decodificar_token

esquema_bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    try:
        usuario_id = decodificar_token(credenciais.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Token inválido ou expirado")

    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Usuário não encontrado")
    return usuario
