from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import usuario_atual
from ..models import ItemCompra, Lar, ListaCompra, Usuario, membro_lar
from ..schemas import ItemCompraCreate, ItemCompraOut, ItemPatch, ListaCompraCreate, ListaCompraOut

router = APIRouter(prefix="/compras", tags=["compras"])


def _lar_ativo(usuario: Usuario, db: Session) -> Lar:
    """Retorna o primeiro lar do usuário (esqueleto: um lar por usuário)."""
    lar = (
        db.query(Lar)
        .join(membro_lar, membro_lar.c.lar_id == Lar.id)
        .filter(membro_lar.c.usuario_id == usuario.id)
        .first()
    )
    if not lar:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Nenhum lar encontrado para o usuário")
    return lar


@router.get("/listas", response_model=list[ListaCompraOut])
def listar_listas(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    lar = _lar_ativo(usuario, db)
    return db.query(ListaCompra).filter(ListaCompra.lar_id == lar.id).order_by(ListaCompra.id.desc()).all()


@router.post("/listas", response_model=ListaCompraOut, status_code=status.HTTP_201_CREATED)
def criar_lista(dados: ListaCompraCreate, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    lar = _lar_ativo(usuario, db)
    lista = ListaCompra(lar_id=lar.id, nome=dados.nome)
    db.add(lista)
    db.commit()
    db.refresh(lista)
    return lista


@router.post("/listas/{lista_id}/itens", response_model=ItemCompraOut, status_code=status.HTTP_201_CREATED)
def adicionar_item(
    lista_id: int,
    dados: ItemCompraCreate,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    lista = db.get(ListaCompra, lista_id)
    if not lista:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lista não encontrada")
    item = ItemCompra(lista_id=lista_id, **dados.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/itens/{item_id}", response_model=ItemCompraOut)
def marcar_item(
    item_id: int,
    dados: ItemPatch,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    item = db.get(ItemCompra, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
    item.marcado = dados.marcado
    db.commit()
    db.refresh(item)
    return item
