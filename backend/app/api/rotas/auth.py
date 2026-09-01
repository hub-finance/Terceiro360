"""Autenticação."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tempo import agora
from app.core.db import get_db
from app.core.deps import Sessao, sessao_atual
from app.core.security import conferir_senha, criar_token
from app.modules.compliance.models import LogAcesso
from app.modules.identity.models import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# §31 — freio de força bruta. Sem isto, uma senha de oito caracteres cai numa
# tarde: nada limita quantas tentativas o atacante faz por segundo.
TENTATIVAS_ATE_BLOQUEIO = 5
JANELA_BLOQUEIO_MINUTOS = 15


def _tentativas_recentes(db: Session, email: str, ip: str | None) -> int:
    """Conta falhas recentes do mesmo e-mail ou do mesmo IP.

    Pelos dois: contar só por e-mail deixa passar a varredura de muitos
    usuários com senhas comuns; contar só por IP deixa passar o ataque
    distribuído contra uma conta específica.
    """
    desde = agora() - dt.timedelta(minutes=JANELA_BLOQUEIO_MINUTOS)
    usuario = db.scalar(select(Usuario.id).where(Usuario.email == email))
    condicoes = []
    if usuario is not None:
        condicoes.append(LogAcesso.usuario_id == usuario)
    if ip:
        condicoes.append(LogAcesso.ip == ip)
    if not condicoes:
        return 0
    return db.scalar(
        select(func.count(LogAcesso.id)).where(
            LogAcesso.acao == "LOGIN",
            LogAcesso.resultado == "NEGADO",
            LogAcesso.criado_em >= desde,
            or_(*condicoes),
        )
    ) or 0


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
    email = form.username.lower().strip()
    ip = request.client.host if request.client else None

    if _tentativas_recentes(db, email, ip) >= TENTATIVAS_ATE_BLOQUEIO:
        db.add(LogAcesso(acao="LOGIN", ip=ip, resultado="BLOQUEADO",
                         user_agent=request.headers.get("user-agent")))
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Muitas tentativas. Aguarde {JANELA_BLOQUEIO_MINUTOS} minutos e tente de novo.",
        )

    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    autorizado = bool(usuario and usuario.ativo and conferir_senha(form.password, usuario.senha_hash))

    db.add(LogAcesso(
        usuario_id=usuario.id if usuario else None,
        acao="LOGIN",
        ip=ip,
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
