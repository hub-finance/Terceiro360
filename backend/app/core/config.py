"""Configuração central do TERCEIRO360."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Vale só para rodar na máquina do desenvolvedor. Está publicada no
# repositório, então qualquer pessoa poderia assinar um token válido com ela.
CHAVE_DE_DESENVOLVIMENTO = "troque-esta-chave-em-producao"


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
    secret_key: str = CHAVE_DE_DESENVOLVIMENTO
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    # Origens autorizadas a chamar a API pelo navegador. Em produção é o
    # domínio do painel; deixar localhost aqui não protege nada, mas deixar
    # "*" com credenciais permitiria a qualquer site agir como o usuário.
    cors_origens: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def em_producao(self) -> bool:
        return self.environment.lower() in ("production", "producao", "prod")

    # LGPD / retenção
    mascarar_dados_pessoais: bool = True
    retencao_logs_dias: int = 1825

    # Armazenamento de documentos gerados
    storage_dir: str = "./storage"


@lru_cache
def get_settings() -> Settings:
    config = Settings()
    if config.em_producao:
        # Falhar ao subir é muito melhor do que subir inseguro: com a chave
        # padrão, qualquer um forja um token de qualquer usuário de qualquer
        # cliente, e nada no sistema acusa — o token é válido.
        if config.secret_key == CHAVE_DE_DESENVOLVIMENTO:
            raise RuntimeError(
                "T360_SECRET_KEY não foi definida. Em produção o sistema não sobe "
                "com a chave de desenvolvimento: ela está publicada no repositório "
                "e permitiria forjar a sessão de qualquer usuário. "
                "Gere uma com: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if len(config.secret_key) < 32:
            raise RuntimeError(
                "T360_SECRET_KEY curta demais (mínimo 32 caracteres) para assinar "
                "sessões em produção."
            )
        if config.debug:
            raise RuntimeError(
                "T360_DEBUG não pode ficar ligado em produção: expõe detalhe "
                "interno nas mensagens de erro."
            )
    return config


settings = get_settings()
