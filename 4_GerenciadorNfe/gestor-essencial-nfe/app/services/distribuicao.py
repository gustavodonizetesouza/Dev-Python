"""Cliente do webservice NFeDistribuicaoDFe.

Fluxo: monta <distDFeInt> com o último NSU → assina com o A1 (RSA-SHA256)
→ envia via POST com TLS mútuo → descompacta os XMLs do retorno.
"""
import base64
import gzip
import hashlib
import tempfile
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

from app.config import Settings
from app.infrastructure.certificado import CertificadoDigital

NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

CODIGOS_UF = {
    "AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29, "CE": 23, "DF": 53,
    "ES": 32, "GO": 52, "MA": 21, "MT": 51, "MS": 50, "MG": 31, "PA": 15,
    "PB": 25, "PR": 41, "PE": 26, "PI": 22, "RJ": 33, "RN": 24, "RS": 43,
    "RO": 11, "RR": 14, "SC": 42, "SP": 35, "SE": 28, "TO": 17,
}


def _tag(nome: str) -> str:
    return f"{{{NS_NFE}}}{nome}"


def montar_pedido(ambiente: str, uf: str, cnpj: str, ultimo_nsu: int = 0) -> bytes:
    raiz = etree.Element(_tag("distDFeInt"), versao="1.01")
    etree.SubElement(raiz, _tag("tpAmb")
                     ).text = "1" if ambiente == "producao" else "2"
    etree.SubElement(raiz, _tag("cUFAutor")).text = str(CODIGOS_UF[uf.upper()])
    etree.SubElement(raiz, _tag("CNPJ")).text = cnpj
    etree.SubElement(raiz, _tag("ultNSU")).text = str(ultimo_nsu)
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def assinar_documento(xml_bytes: bytes, cert: CertificadoDigital) -> bytes:
    """Assinatura enveloped (xmldsig) com RSA-SHA256, padrão SEFAZ.

    IMPORTANTE: valide o resultado em homologação comparando com a
    implementação da PyTrustNFe — assinatura é o ponto mais sensível.
    """
    raiz = etree.fromstring(xml_bytes, etree.XMLParser(remove_blank_text=True))

    # 1) Monta a estrutura Signature (valores vazios por enquanto)
    sig = etree.SubElement(raiz, f"{{{NS_DS}}}Signature")
    sinfo = etree.SubElement(sig, f"{{{NS_DS}}}SignedInfo")
    etree.SubElement(
        sinfo, f"{{{NS_DS}}}CanonicalizationMethod",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    etree.SubElement(
        sinfo, f"{{{NS_DS}}}SignatureMethod",
        Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    )
    ref = etree.SubElement(sinfo, f"{{{NS_DS}}}Reference", URI="")
    trans = etree.SubElement(ref, f"{{{NS_DS}}}Transforms")
    etree.SubElement(
        trans, f"{{{NS_DS}}}Transform",
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    etree.SubElement(
        trans, f"{{{NS_DS}}}Transform",
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    etree.SubElement(ref, f"{{{NS_DS}}}DigestMethod",
                     Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
    digest_value = etree.SubElement(ref, f"{{{NS_DS}}}DigestValue")
    etree.SubElement(sig, f"{{{NS_DS}}}SignatureValue")
    kinfo = etree.SubElement(sig, f"{{{NS_DS}}}KeyInfo")
    x509 = etree.SubElement(kinfo, f"{{{NS_DS}}}X509Data")
    etree.SubElement(x509, f"{{{NS_DS}}}X509Certificate").text = (
        cert.certificado_base64_dersha256()
    )

    # 2) Digest = SHA-256 do documento SEM a assinatura (transform enveloped), c14n
    raiz.remove(sig)
    doc_c14n = etree.tostring(raiz, method="c14n", with_comments=False)
    digest_value.text = base64.b64encode(
        hashlib.sha256(doc_c14n).digest()).decode()

    # 3) Reinsere a assinatura e assina o SignedInfo
    raiz.append(sig)
    sinfo_c14n = etree.tostring(sinfo, method="c14n", with_comments=False)
    assinatura = cert.chave.sign(
        sinfo_c14n, padding.PKCS1v15(), hashes.SHA256())
    sig.find(f"{{{NS_DS}}}SignatureValue").text = base64.b64encode(
        assinatura).decode()

    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def consultar_distribuicao(
    settings: Settings,
    cert: CertificadoDigital,
    ultimo_nsu: int = 0,
) -> tuple[int, list[dict]]:
    """Retorna (novo_ultimo_nsu, [{"schema": ..., "xml": bytes}, ...])."""
    pedido = assinar_documento(
        montar_pedido(settings.nfe_ambiente, settings.uf,
                      settings.cnpj_interessado, ultimo_nsu),
        cert,
    )

    with tempfile.TemporaryDirectory() as tmp:
        cert_pem, key_pem = cert.gerar_pem_para_tls(Path(tmp))
        with httpx.Client(cert=(str(cert_pem), str(key_pem)), timeout=60.0) as client:
            resp = client.post(
                settings.endpoint_distribuicao,
                content=pedido,
                headers={"Content-Type": "text/xml; charset=utf-8"},
            )
    resp.raise_for_status()

    raiz = etree.fromstring(resp.content)
    novo_nsu = raiz.find(f".//{_tag('ultNSU')}")
    novo_nsu_val = int(
        novo_nsu.text) if novo_nsu is not None and novo_nsu.text else ultimo_nsu

    documentos = []
    for doc in raiz.iter(_tag("docZip")):
        conteudo = gzip.decompress(base64.b64decode(doc.text))
        documentos.append(
            {"schema": doc.attrib.get("schema", ""), "xml": conteudo})

    return novo_nsu_val, documentos
