"""Autenticação, senhas e permissões (§5, §33)."""
from __future__ import annotations

import datetime as dt
import uuid

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt opera sobre no máximo 72 bytes; senhas maiores são truncadas de forma
# explícita para que o comportamento seja o mesmo na gravação e na conferência.
_LIMITE_BCRYPT = 72


def _preparar(senha: str) -> bytes:
    return senha.encode("utf-8")[:_LIMITE_BCRYPT]


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_preparar(senha), bcrypt.gensalt()).decode("utf-8")


def conferir_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return bcrypt.checkpw(_preparar(senha), hash_armazenado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_token(usuario_id: uuid.UUID, cliente_id: uuid.UUID, extras: dict | None = None) -> str:
    agora = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "cli": str(cliente_id),
        "iat": agora,
        "exp": agora + dt.timedelta(minutes=settings.access_token_expire_minutes),
        **(extras or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def ler_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ------------------------------------------------------------------ Permissões

# Perfis padrão do sistema (§5). "*" = tudo dentro do escopo do cliente.
PERFIS_PADRAO: dict[str, dict] = {
    "ADMINISTRADOR": {
        "nome": "Administrador",
        "permissoes": ["*"],
        "exige_habilitacao": False,
    },
    "ADVOGADO": {
        "nome": "Advogado",
        "permissoes": [
            "entidades:*", "juridico:*", "documentos:*", "registral:*",
            "normativo:*", "governanca:ler", "ia:*",
        ],
        "exige_habilitacao": True,
    },
    "CONSULTOR": {
        "nome": "Consultor",
        "permissoes": ["entidades:ler", "juridico:*", "documentos:*", "governanca:ler"],
        "exige_habilitacao": False,
    },
    "SECRETARIO": {
        "nome": "Secretário",
        "permissoes": ["entidades:ler", "juridico:evento:criar", "juridico:evento:ler",
                       "documentos:ler", "documentos:gerar"],
        "exige_habilitacao": False,
    },
    "PRESIDENTE": {
        "nome": "Presidente",
        "permissoes": ["entidades:ler", "juridico:*", "documentos:*", "governanca:ler",
                       "documentos:aprovar"],
        "exige_habilitacao": False,
    },
    "TESOUREIRO": {
        "nome": "Tesoureiro",
        "permissoes": ["entidades:ler", "documentos:ler", "governanca:ler"],
        "exige_habilitacao": False,
    },
    "CONSELHO_FISCAL": {
        "nome": "Conselho Fiscal",
        "permissoes": ["entidades:ler", "documentos:ler", "governanca:ler", "documentos:parecer"],
        "exige_habilitacao": False,
    },
    "AUDITOR": {
        "nome": "Auditor",
        "permissoes": ["entidades:ler", "juridico:ler", "documentos:ler", "governanca:ler",
                       "compliance:ler"],
        "exige_habilitacao": False,
    },
    "OPERADOR": {
        "nome": "Operador",
        "permissoes": ["entidades:ler", "juridico:evento:criar", "documentos:gerar"],
        "exige_habilitacao": False,
    },
    "CLIENTE": {
        "nome": "Cliente",
        "permissoes": ["entidades:ler", "documentos:ler", "governanca:ler"],
        "exige_habilitacao": False,
    },
    "VISUALIZADOR": {
        "nome": "Visualizador",
        "permissoes": ["entidades:ler", "documentos:ler"],
        "exige_habilitacao": False,
    },
}


def tem_permissao(permissoes: list[str], requerida: str) -> bool:
    """Confere "modulo:recurso:acao" contra a lista do perfil, aceitando curingas."""
    if "*" in permissoes:
        return True
    partes = requerida.split(":")
    for concedida in permissoes:
        if concedida == requerida:
            return True
        if concedida.endswith(":*"):
            prefixo = concedida[:-2].split(":")
            if partes[: len(prefixo)] == prefixo:
                return True
    return False
