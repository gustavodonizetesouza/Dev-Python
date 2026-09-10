"""Orquestra: consulta → grava XML (com hash) → atualiza NSU."""
import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.certificado import CertificadoDigital
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import ItemNota, NSUControle, NotaFiscal
from app.services.distribuicao import consultar_distribuicao
from app.services.parser import extrair_dados_nfe


def _gravar_nota(db: Session, xml_bytes: bytes, pasta_xml: str) -> NotaFiscal | None:
    dados = extrair_dados_nfe(xml_bytes)
    chave = dados["chave"]
    if not chave or db.query(NotaFiscal).filter_by(chave=chave).first():
        return None  # já existe (dedupe por chave)

    nome_arquivo = f"{chave}-nfe.xml"
    caminho = Path(pasta_xml) / nome_arquivo
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(xml_bytes)

    nota = NotaFiscal(
        chave=chave,
        numero=int(dados["numero"] or 0),
        serie=int(dados["serie"] or 1),
        tipo_operacao=dados["tipo_operacao"] or "",
        data_emissao=(dados["data_emissao"] or "")[:10],
        modelo=dados["modelo"],
        valor_total=float(dados["valor_total"] or 0),
        emissor_cnpj=dados["emissor_cnpj"],
        emissor_nome=dados["emissor_nome"],
        destinatario_cnpj=dados["destinatario_cnpj"],
        destinatario_nome=dados["destinatario_nome"],
        caminho_xml=str(caminho),
        hash_xml=hashlib.sha256(xml_bytes).hexdigest(),
    )
    for item in dados["itens"]:
        nota.itens.append(ItemNota(
            n_item=int(item["n_item"] or 0),
            codigo=item["codigo"], descricao=item["descricao"],
            ncm=item["ncm"], cfop=item["cfop"], unidade=item["unidade"],
            quantidade=float(item["quantidade"] or 0),
            valor_unitario=float(item["valor_unitario"] or 0),
            valor_total=float(item["valor_total"] or 0),
        ))
    db.add(nota)
    return nota


def sincronizar() -> dict:
    settings = get_settings()
    cert = CertificadoDigital.carregar_pfx(
        settings.certificado_arquivo, settings.certificado_senha
    )

    with SessionLocal() as db:
        controle = (
            db.query(NSUControle)
            .filter_by(cnpj_interessado=settings.cnpj_interessado)
            .first()
        )
        if controle is None:
            controle = NSUControle(
                cnpj_interessado=settings.cnpj_interessado,
                ambiente=settings.nfe_ambiente,
                ultimo_nsu=0,
            )
            db.add(controle)
            db.flush()

        novo_nsu, documentos = consultar_distribuicao(
            settings, cert, controle.ultimo_nsu
        )

        novas = 0
        for doc in documentos:
            nota = _gravar_nota(db, doc["xml"], settings.pasta_xml)
            novas += 1 if nota is not None else 0

        controle.ultimo_nsu = novo_nsu
        db.commit()

        return {"notas_novas": novas, "ultimo_nsu": novo_nsu, "total_processado": len(documentos)}
