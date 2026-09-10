"""Configuração central do serviço (lê do .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Ambiente SEFAZ
    nfe_ambiente: str = "homologacao"   # "homologacao" | "producao"
    uf: str = "SP"
    cnpj_interessado: str = ""

    # Certificado A1
    certificado_arquivo: str = ""
    certificado_senha: str = ""

    # SQL Server
    sqlserver_host: str = "localhost"
    sqlserver_db: str = "GestorEssencialNFe"
    sqlserver_user: str = "sa"
    sqlserver_password: str = ""
    sqlserver_driver: str = "ODBC Driver 18 for SQL Server"
    sqlserver_trust_cert: bool = True

    # Armazenamento
    pasta_xml: str = "storage/xml"
    pasta_pdf: str = "storage/pdf"

    # API
    api_token: str = ""

    @property
    def url_banco(self) -> str:
        trust = "yes" if self.sqlserver_trust_cert else "no"
        return (
            f"mssql+pyodbc://{self.sqlserver_user}:{self.sqlserver_password}"
            f"@{self.sqlserver_host}/{self.sqlserver_db}"
            f"?driver={self.sqlserver_driver}&TrustServerCertificate={trust}"
        )

    @property
    def endpoint_distribuicao(self) -> str:
        base = (
            "https://www1.nfe.fazenda.gov.br"
            if self.nfe_ambiente == "producao"
            else "https://hom1.nfe.fazenda.gov.br"
        )
        return f"{base}/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"


@lru_cache
def get_settings() -> Settings:
    return Settings()
