"""Dependências da API: sessão, usuário autenticado e escopo de permissão."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import ler_token, tem_permissao
from app.modules.entidades.models import Entidade
from app.modules.identity.models import Perfil, Usuario, UsuarioPerfil

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass
class Sessao:
    usuario: Usuario
    permissoes: list[str]
    entidades_permitidas: set[uuid.UUID] | None  # None = todas do cliente

    @property
    def cliente_id(self) -> uuid.UUID:
        return self.usuario.cliente_id


def sessao_atual(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> Sessao:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária.")
    payload = ler_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada ou inválida.")

    usuario = db.get(Usuario, uuid.UUID(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo.")

    vinculos = db.scalars(
        select(UsuarioPerfil).where(UsuarioPerfil.usuario_id == usuario.id)
    ).all()
    permissoes: list[str] = []
    escopo: set[uuid.UUID] = set()
    irrestrito = not vinculos
    for v in vinculos:
        perfil = db.get(Perfil, v.perfil_id)
        if perfil:
            permissoes.extend(perfil.permissoes or [])
        if v.entidade_id is None:
            irrestrito = True
        else:
            escopo.add(v.entidade_id)

    return Sessao(usuario=usuario, permissoes=permissoes,
                  entidades_permitidas=None if irrestrito else escopo)


def exigir(permissao: str):
    """Uso: `Depends(exigir("juridico:evento:gerar"))`."""

    def _verificar(sessao: Sessao = Depends(sessao_atual)) -> Sessao:
        if not tem_permissao(sessao.permissoes, permissao):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Seu perfil não tem a permissão “{permissao}”.",
            )
        return sessao

    return _verificar


def entidade_do_escopo(
    entidade_id: uuid.UUID, sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)
) -> Entidade:
    """Isolamento lógico entre entidades e entre clientes (§31)."""
    entidade = db.get(Entidade, entidade_id)
    if entidade is None or entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entidade não encontrada.")
    if sessao.entidades_permitidas is not None and entidade.id not in sessao.entidades_permitidas:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a esta entidade.")
    return entidade
