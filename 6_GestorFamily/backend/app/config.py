from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Padrão de desenvolvimento: SQLite. Em produção aponte para o SQL Server.
    database_url: str = "sqlite:///./dev.db"
    secret_key: str = "troque-esta-chave-em-producao"
    token_expire_minutes: int = 480  # 8 horas

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
