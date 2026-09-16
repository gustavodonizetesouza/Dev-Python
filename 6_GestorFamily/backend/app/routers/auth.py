from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_atual
from ..models import Lar, Usuario, membro_lar
from ..schemas import LoginRequest, Token, UsuarioCreate, UsuarioOut
from ..security import criar_token, hash_senha, verificar_senha

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar(dados: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")

    usuario = Usuario(nome=dados.nome, email=dados.email,
                      senha_hash=hash_senha(dados.senha))
    db.add(usuario)
    db.flush()

    # Todo usuário já nasce com um "lar individual" (modo solteiro).
    # Depois entra o compartilhamento: convites para criar um lar familiar.
    lar = Lar(nome=f"Lar de {dados.nome}")
    db.add(lar)
    db.flush()
    db.execute(insert(membro_lar).values(
        usuario_id=usuario.id, lar_id=lar.id, papel="dono"))

    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=Token)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "E-mail ou senha inválidos")
    return Token(access_token=criar_token(usuario.id))


@router.get("/me", response_model=UsuarioOut)
def eu(usuario: Usuario = Depends(usuario_atual)):
    return usuario
