"""Modelos ORM — espelham o DDL em sql/ddl_sqlserver.sql."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class NSUControle(Base):
    """Controla a sincronização incremental (NT 2014.002)."""
    __tablename__ = "tb_nfe_nsu"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cnpj_interessado: Mapped[str] = mapped_column(
        String(14), unique=True, index=True)
    ambiente: Mapped[str] = mapped_column(String(10), default="homologacao")
    ultimo_nsu: Mapped[int] = mapped_column(BigInteger, default=0)
    ultima_consulta: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True)


class NotaFiscal(Base):
    __tablename__ = "tb_nfe_nota"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(44), unique=True, index=True)
    numero: Mapped[int] = mapped_column(Integer)
    serie: Mapped[int] = mapped_column(Integer, default=1)
    tipo_operacao: Mapped[str] = mapped_column(
        String(1))        # 0=entrada 1=saída
    data_emissao: Mapped[date] = mapped_column(Date)
    modelo: Mapped[str | None] = mapped_column(
        String(2))        # 55=NF-e 65=NFC-e
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    emissor_cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    emissor_nome: Mapped[str | None] = mapped_column(String(200))
    destinatario_cnpj: Mapped[str | None] = mapped_column(
        String(14), index=True)
    destinatario_nome: Mapped[str | None] = mapped_column(String(200))
    caminho_xml: Mapped[str | None] = mapped_column(String(500))
    hash_xml: Mapped[str | None] = mapped_column(
        String(64))      # SHA-256 do XML
    status_manifestacao: Mapped[str | None] = mapped_column(String(10))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    itens: Mapped[list["ItemNota"]] = relationship(
        back_populates="nota", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_nota_emissor_emissao",
                      "emissor_cnpj", "data_emissao"),)


class ItemNota(Base):
    __tablename__ = "tb_nfe_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nota_id: Mapped[int] = mapped_column(
        ForeignKey("tb_nfe_nota.id", ondelete="CASCADE"), index=True
    )
    n_item: Mapped[int] = mapped_column(Integer)
    codigo: Mapped[str | None] = mapped_column(String(60))
    descricao: Mapped[str | None] = mapped_column(String(250))
    ncm: Mapped[str | None] = mapped_column(String(8))
    cfop: Mapped[str | None] = mapped_column(String(4))
    unidade: Mapped[str | None] = mapped_column(String(6))
    quantidade: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    nota: Mapped[NotaFiscal] = relationship(back_populates="itens")
