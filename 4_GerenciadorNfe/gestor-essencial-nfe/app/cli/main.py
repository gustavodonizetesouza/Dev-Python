"""CLI para uso independente do Gestor Essencial."""
import typer
from rich.pretty import pprint

from app.infrastructure.database import SessionLocal
from app.infrastructure.models import NotaFiscal

app = typer.Typer(help="Serviço Fiscal NF-e — Gestor Essencial")


@app.command()
def sincronizar():
    """Baixa novas notas desde o último NSU registrado."""
    from app.services.sincronizacao import sincronizar
    resultado = sincronizar()
    typer.echo(
        f"Notas novas: {resultado['notas_novas']} | NSU: {resultado['ultimo_nsu']}")


@app.command()
def listar(cnpj: str | None = None):
    """Lista notas baixadas."""
    with SessionLocal() as db:
        q = db.query(NotaFiscal)
        if cnpj:
            q = q.filter((NotaFiscal.emissor_cnpj == cnpj)
                         | (NotaFiscal.destinatario_cnpj == cnpj))
        for n in q.order_by(NotaFiscal.data_emissao.desc()).limit(50):
            typer.echo(
                f"{n.data_emissao} | Nº {n.numero:06d} | "
                f"{n.emissor_nome or n.destinatario_nome} | R$ {n.valor_total or 0}"
            )


@app.command()
def pdf(chave: str):
    """Gera o DANFE em PDF de uma nota pela chave de acesso."""
    from app.services.danfe import gerar_danfe
    with SessionLocal() as db:
        nota = db.query(NotaFiscal).filter_by(chave=chave).first()
        if not nota or not nota.caminho_xml:
            typer.echo("Nota não encontrada.", err=True)
            raise typer.Exit(1)
        destino = gerar_danfe(
            nota.caminho_xml, filename_saida=f"{chave}-danfe.pdf")
        typer.echo(f"PDF gerado: {destino}")


if __name__ == "__main__":
    app()
