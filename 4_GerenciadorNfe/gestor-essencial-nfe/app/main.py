"""API REST — consumida pelo Gestor Essencial (HTTP/JSON + Bearer token)."""
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.infrastructure.database import get_db
from app.infrastructure.models import NotaFiscal

app = FastAPI(title="Serviço Fiscal NF-e · Gestor Essencial", version="0.1.0")


def _validar_token(x_api_token: str = Header(default="")):
    if x_api_token != get_settings().api_token:
        raise HTTPException(status_code=401, detail="Token inválido")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/notas", dependencies=[Depends(_validar_token)])
def listar_notas(cnpj: str | None = None, db: Session = Depends(get_db)):
    q = db.query(NotaFiscal)
    if cnpj:
        q = q.filter((NotaFiscal.emissor_cnpj == cnpj)
                     | (NotaFiscal.destinatario_cnpj == cnpj))
    notas = q.order_by(NotaFiscal.data_emissao.desc()).limit(200).all()
    return [{
        "chave": n.chave,
        "numero": n.numero,
        "serie": n.serie,
        "tipo_operacao": n.tipo_operacao,
        "data_emissao": n.data_emissao.isoformat(),
        "emitente": n.emissor_nome,
        "destinatario": n.destinatario_nome,
        "valor_total": float(n.valor_total or 0),
        "status_manifestacao": n.status_manifestacao,
    } for n in notas]


@app.get("/api/v1/notas/{chave}/xml", dependencies=[Depends(_validar_token)])
def baixar_xml(chave: str, db: Session = Depends(get_db)):
    nota = db.query(NotaFiscal).filter_by(chave=chave).first()
    if not nota or not nota.caminho_xml or not Path(nota.caminho_xml).exists():
        raise HTTPException(404, "XML não encontrado")
    return FileResponse(nota.caminho_xml, media_type="application/xml",
                        filename=f"{chave}.xml")


@app.get("/api/v1/notas/{chave}/pdf", dependencies=[Depends(_validar_token)])
def baixar_pdf(chave: str, db: Session = Depends(get_db)):
    from app.services.danfe import gerar_danfe
    nota = db.query(NotaFiscal).filter_by(chave=chave).first()
    if not nota or not nota.caminho_xml:
        raise HTTPException(404, "Nota não encontrada")
    pdf = gerar_danfe(nota.caminho_xml, filename_saida=f"{chave}-danfe.pdf")
    return FileResponse(pdf, media_type="application/pdf",
                        filename=f"{chave}-danfe.pdf")


@app.post("/api/v1/sincronizar", dependencies=[Depends(_validar_token)])
def sincronizar_agora():
    from app.services.sincronizacao import sincronizar
    return sincronizar()
