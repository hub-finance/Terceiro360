"""Configuração central do TERCEIRO360."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="T360_", extra="ignore")

    app_name: str = "TERCEIRO360"
    app_slogan: str = "Inteligência e automação para o Terceiro Setor."
    api_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

    # Banco. PostgreSQL em produção; SQLite é aceito para desenvolvimento e testes.
    database_url: str = "sqlite+pysqlite:///./terceiro360.db"

    # Segurança
    secret_key: str = "troque-esta-chave-em-producao"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # LGPD / retenção
    mascarar_dados_pessoais: bool = True
    retencao_logs_dias: int = 1825

    # Armazenamento de documentos gerados
    storage_dir: str = "./storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
