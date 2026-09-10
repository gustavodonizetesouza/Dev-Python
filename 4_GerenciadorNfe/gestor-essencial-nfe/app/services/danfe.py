"""Geração do DANFE em PDF a partir do XML (biblioteca brazilfiscalreport)."""
from pathlib import Path

from brazilfiscalreport.danfe import Danfe


def gerar_danfe(
    caminho_xml: str | Path,
    pasta_saida: str | Path = "storage/pdf",
    filename_saida: str | None = None,
) -> Path:
    xml_path = Path(caminho_xml)
    destino = Path(pasta_saida) / (
        filename_saida or f"{xml_path.stem}-danfe.pdf"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)

    with open(xml_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    danfe = Danfe(xml=xml_content)
    danfe.output(str(destino))
    return destino
