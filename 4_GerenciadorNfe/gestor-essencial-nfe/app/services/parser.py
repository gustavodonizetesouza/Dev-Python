"""Extrai dados estruturados do XML de NF-e (funciona com nfelib ou lxml puro)."""
from pathlib import Path

from lxml import etree

NS_NFE = "http://www.portalfiscal.inf.br/nfe"


def _tag(nome: str) -> str:
    return f"{{{NS_NFE}}}{nome}"


def _texto(el, nome):
    if el is None:
        return None
    node = el.find(_tag(nome))
    if node is not None and node.text:
        return node.text.strip()
    return None


def extrair_dados_nfe(fonte: str | Path | bytes) -> dict:
    """fonte pode ser caminho do arquivo ou os bytes do XML."""
    if isinstance(fonte, (str, Path)):
        raiz = etree.parse(str(fonte)).getroot()
    else:
        raiz = etree.fromstring(fonte)

    ide = raiz.find(f".//{_tag('ide')}")
    emit = raiz.find(f".//{_tag('emit')}")
    dest = raiz.find(f".//{_tag('dest')}")
    tot = raiz.find(f".//{_tag('total')}/{_tag('ICMSTot')}")

    dados = {
        "chave": raiz.attrib.get("Id", "").replace("NFe", ""),
        "numero": _texto(ide, "nNF"),
        "serie": _texto(ide, "serie"),
        "tipo_operacao": _texto(ide, "tpNF"),
        "data_emissao": _texto(ide, "dhEmi") or _texto(ide, "dEmi"),
        "modelo": _texto(ide, "mod"),
        "emissor_cnpj": _texto(emit, "CNPJ"),
        "emissor_nome": _texto(emit, "xNome"),
        "destinatario_cnpj": _texto(dest, "CNPJ"),
        "destinatario_nome": _texto(dest, "xNome"),
        "valor_total": _texto(tot, "vNF"),
        "itens": [],
    }

    for det in raiz.iter(_tag("det")):
        prod = det.find(_tag("prod"))
        dados["itens"].append({
            "n_item": det.attrib.get("nItem"),
            "codigo": _texto(prod, "cProd"),
            "descricao": _texto(prod, "xProd"),
            "ncm": _texto(prod, "NCM"),
            "cfop": _texto(prod, "CFOP"),
            "unidade": _texto(prod, "uCom"),
            "quantidade": _texto(prod, "qCom"),
            "valor_unitario": _texto(prod, "vUnCom"),
            "valor_total": _texto(prod, "vProd"),
        })

    return dados
