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
from app.core.mfa import (
    conferir_codigo,
    consumir_codigo_recuperacao,
    gerar_codigos_recuperacao,
    novo_segredo,
    uri_de_provisionamento,
)
from app.core.security import conferir_senha, criar_token, hash_senha
from app.core import senhas
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
    # Sinaliza para a tela que a senha está certa mas falta o segundo fator.
    # Sem isto o front não tem como distinguir "senha errada" de "faltou código".
    mfa_exigido: bool = False


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

    # Segundo fator. O código vem no campo `client_secret` do formulário OAuth2
    # — é o campo padrão disponível sem inventar um protocolo próprio.
    segundo_fator_pendente = False
    if autorizado and usuario.mfa_habilitado:
        codigo = (form.client_secret or "").strip()
        if not codigo:
            segundo_fator_pendente = True
            autorizado = False
        elif conferir_codigo(usuario.mfa_segredo, codigo):
            pass
        else:
            restantes = consumir_codigo_recuperacao(codigo, usuario.mfa_codigos_recuperacao or [])
            if restantes is None:
                autorizado = False
            else:
                usuario.mfa_codigos_recuperacao = restantes
                db.add(usuario)

    db.add(LogAcesso(
        usuario_id=usuario.id if usuario else None,
        acao="LOGIN",
        ip=ip,
        user_agent=request.headers.get("user-agent"),
        resultado="OK" if autorizado else ("MFA_PENDENTE" if segundo_fator_pendente else "NEGADO"),
    ))
    db.commit()

    if segundo_fator_pendente:
        # 401 com sinalização própria: a senha estava certa, falta o código.
        # E esta tentativa não conta como falha — senão quem digita a senha
        # certa todo dia se autobloquearia.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Informe o código do seu aplicativo autenticador.",
            headers={"X-MFA-Exigido": "1"},
        )

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


# ------------------------------------------------------------------- Senha


class TrocaSenhaIn(BaseModel):
    senha_atual: str
    senha_nova: str


@router.post("/senha")
def trocar_senha(
    dados: TrocaSenhaIn,
    request: Request,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """Troca a própria senha.

    Pede a senha atual mesmo já havendo sessão aberta: sessão sequestrada
    (máquina destravada, token roubado) não pode virar tomada de conta.
    """
    usuario = sessao.usuario
    if not conferir_senha(dados.senha_atual, usuario.senha_hash):
        db.add(LogAcesso(usuario_id=usuario.id, acao="TROCA_SENHA",
                         ip=request.client.host if request.client else None,
                         resultado="NEGADO"))
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha atual incorreta.")

    try:
        senhas.validar(dados.senha_nova, email=usuario.email, nome=usuario.nome)
    except ValueError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(erro)) from erro

    if conferir_senha(dados.senha_nova, usuario.senha_hash):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "A senha nova precisa ser diferente da atual.")

    usuario.senha_hash = hash_senha(dados.senha_nova)
    usuario.senha_alterada_em = agora()
    db.add(usuario)
    db.add(LogAcesso(usuario_id=usuario.id, acao="TROCA_SENHA",
                     ip=request.client.host if request.client else None, resultado="OK"))
    db.commit()
    return {"ok": True, "alterada_em": usuario.senha_alterada_em.isoformat()}


@router.post("/senha/conferir")
def conferir_forca(dados: dict):
    """Avalia uma senha sem gravar nada — para a tela avisar enquanto se digita.

    Não exige sessão de propósito: também serve à tela de primeiro acesso.
    Não devolve nada sobre o usuário, só sobre o texto enviado.
    """
    achados = senhas.problemas(
        str(dados.get("senha", "")), dados.get("email"), dados.get("nome")
    )
    return {"aceita": not achados, "problemas": achados,
            "comprimento_minimo": senhas.COMPRIMENTO_MINIMO}


# --------------------------------------------------------------------- MFA


class ConfirmacaoMFAIn(BaseModel):
    codigo: str


@router.get("/mfa")
def situacao_mfa(sessao: Sessao = Depends(sessao_atual)):
    u = sessao.usuario
    return {
        "habilitado": u.mfa_habilitado,
        "confirmado_em": u.mfa_confirmado_em.isoformat() if u.mfa_confirmado_em else None,
        "codigos_recuperacao_restantes": len(u.mfa_codigos_recuperacao or []),
    }


@router.post("/mfa/iniciar")
def iniciar_mfa(sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    """Gera o segredo e devolve a URI do QR Code.

    O segundo fator ainda **não** passa a valer aqui: só depois de a pessoa
    devolver um código correto. Habilitar antes disso tranca quem errou a
    leitura do QR para fora da própria conta.
    """
    usuario = sessao.usuario
    if usuario.mfa_habilitado:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "O segundo fator já está ativo. Desative antes de gerar outro.")
    usuario.mfa_segredo = novo_segredo()
    db.add(usuario)
    db.commit()
    return {
        "segredo": usuario.mfa_segredo,
        "uri": uri_de_provisionamento(usuario.mfa_segredo, usuario.email),
        "instrucao": "Leia o QR Code no seu aplicativo autenticador e confirme "
                     "com o código de seis dígitos que ele mostrar.",
    }


@router.post("/mfa/confirmar")
def confirmar_mfa(
    dados: ConfirmacaoMFAIn,
    request: Request,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    usuario = sessao.usuario
    if not usuario.mfa_segredo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Gere o segredo antes de confirmar.")
    if not conferir_codigo(usuario.mfa_segredo, dados.codigo):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Código inválido. Confira se a hora do celular está certa.")

    claros, hashes = gerar_codigos_recuperacao()
    usuario.mfa_habilitado = True
    usuario.mfa_confirmado_em = agora()
    usuario.mfa_codigos_recuperacao = hashes
    db.add(usuario)
    db.add(LogAcesso(usuario_id=usuario.id, acao="MFA_ATIVADO",
                     ip=request.client.host if request.client else None, resultado="OK"))
    db.commit()
    return {
        "habilitado": True,
        # Mostrados uma única vez: guardamos só o hash.
        "codigos_recuperacao": claros,
        "aviso": "Guarde estes códigos fora do celular. Cada um vale uma vez e "
                 "eles não serão mostrados de novo.",
    }


@router.post("/mfa/desativar")
def desativar_mfa(
    dados: TrocaSenhaIn,
    request: Request,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """Desativa o segundo fator. Exige a senha atual — `senha_nova` é ignorada.

    Desligar proteção é ato sensível: quem chegou numa sessão aberta não pode
    remover o fator que impediria o próximo acesso.
    """
    usuario = sessao.usuario
    if not conferir_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha incorreta.")
    usuario.mfa_habilitado = False
    usuario.mfa_segredo = None
    usuario.mfa_confirmado_em = None
    usuario.mfa_codigos_recuperacao = []
    db.add(usuario)
    db.add(LogAcesso(usuario_id=usuario.id, acao="MFA_DESATIVADO",
                     ip=request.client.host if request.client else None, resultado="OK"))
    db.commit()
    return {"habilitado": False}
