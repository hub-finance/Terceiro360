"""Autenticação."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tempo import agora
from app.core.db import get_db
from app.core.deps import Sessao, sessao_atual
from app.core.security import conferir_senha, criar_token
from app.modules.compliance.models import LogAcesso
from app.modules.identity.models import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em_minutos: int


class UsuarioOut(BaseModel):
    id: str
    nome: str
    email: str
    cliente_id: str
    registro_profissional: str | None = None
    permissoes: list[str] = []


@router.post("/login", response_model=TokenOut)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    usuario = db.scalar(select(Usuario).where(Usuario.email == form.username.lower().strip()))
    autorizado = bool(usuario and usuario.ativo and conferir_senha(form.password, usuario.senha_hash))

    db.add(LogAcesso(
        usuario_id=usuario.id if usuario else None,
        acao="LOGIN",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        resultado="OK" if autorizado else "NEGADO",
    ))
    db.commit()

    if not autorizado:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")

    usuario.ultimo_acesso = agora()
    db.add(usuario)
    db.commit()

    return TokenOut(
        access_token=criar_token(usuario.id, usuario.cliente_id),
        expira_em_minutos=settings.access_token_expire_minutes,
    )


@router.get("/eu", response_model=UsuarioOut)
def eu(sessao: Sessao = Depends(sessao_atual)):
    u = sessao.usuario
    return UsuarioOut(
        id=str(u.id), nome=u.nome, email=u.email, cliente_id=str(u.cliente_id),
        registro_profissional=u.registro_profissional, permissoes=sessao.permissoes,
    )
