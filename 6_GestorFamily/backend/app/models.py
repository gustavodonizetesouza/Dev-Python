from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Associação N:N entre Usuario e Lar (quem pertence a qual família)
membro_lar = Table(
    "membro_lar",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id"), primary_key=True),
    Column("lar_id", ForeignKey("lares.id"), primary_key=True),
    Column("papel", String(20), nullable=False,
           server_default="membro"),  # dono | membro
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    lares: Mapped[list["Lar"]] = relationship(
        secondary=membro_lar, back_populates="membros")


class Lar(Base):
    __tablename__ = "lares"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    membros: Mapped[list["Usuario"]] = relationship(
        secondary=membro_lar, back_populates="lares")
    listas: Mapped[list["ListaCompra"]] = relationship(
        back_populates="lar", cascade="all, delete-orphan")


class ListaCompra(Base):
    __tablename__ = "listas_compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    lar_id: Mapped[int] = mapped_column(ForeignKey("lares.id"))
    nome: Mapped[str] = mapped_column(String(120))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    lar: Mapped["Lar"] = relationship(back_populates="listas")
    itens: Mapped[list["ItemCompra"]] = relationship(
        back_populates="lista", cascade="all, delete-orphan")

    @property
    def total_estimado(self) -> float:
        """Soma da previsão de gasto da lista (preço estimado x quantidade)."""
        return round(sum((i.preco_estimado or 0) * i.quantidade for i in self.itens), 2)


class ItemCompra(Base):
    __tablename__ = "itens_compra"

    id: Mapped[int] = mapped_column(primary_key=True)
    lista_id: Mapped[int] = mapped_column(ForeignKey("listas_compra.id"))
    descricao: Mapped[str] = mapped_column(String(200))
    quantidade: Mapped[float] = mapped_column(Float, default=1)
    preco_estimado: Mapped[float | None] = mapped_column(
        Float, nullable=True)  # preço médio anterior
    marcado: Mapped[bool] = mapped_column(Boolean, default=False)

    lista: Mapped["ListaCompra"] = relationship(back_populates="itens")
