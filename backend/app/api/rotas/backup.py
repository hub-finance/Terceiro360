"""Cópia de segurança do escritório (§31, LGPD art. 37)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, exigir
from app.core.tempo import agora
from app.modules.backup.servico import exportar, nome_do_arquivo
from app.modules.compliance.models import LogAcesso
from app.modules.identity.models import Usuario

router = APIRouter(prefix="/backup", tags=["Cópia de segurança"])

ACAO = "BACKUP_EXPORTADO"


def _escritorio_inteiro(sessao: Sessao) -> None:
    """A cópia é do escritório todo. Quem só enxerga algumas entidades não
    pode, por ela, levar as outras."""
    if sessao.entidades_permitidas is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A cópia de segurança abrange o escritório inteiro, e seu acesso é "
            "limitado a algumas entidades.",
        )


@router.get("")
def baixar(
    request: Request,
    sessao: Sessao = Depends(exigir("backup:exportar")),
    db: Session = Depends(get_db),
):
    """Gera e entrega o ZIP da cópia. Nada é gravado no servidor."""
    _escritorio_inteiro(sessao)
    usuario = sessao.usuario
    arquivo, manifesto = exportar(
        db, sessao.cliente_id, {"id": str(usuario.id), "nome": usuario.nome, "email": usuario.email}
    )

    # O arquivo leva dado pessoal decifrado: quem levou, quando e de onde
    # precisa ficar registrado (LGPD, art. 37).
    db.add(LogAcesso(
        usuario_id=usuario.id, acao=ACAO, recurso="backup",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"), resultado="OK",
    ))
    db.commit()

    nome = nome_do_arquivo(manifesto["escritorio"].get("nome") or "", agora())
    return Response(
        content=arquivo,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            # Arquivo com dado pessoal não fica em cache de proxy nem do navegador.
            "Cache-Control": "no-store",
        },
    )


@router.get("/historico")
def historico(
    sessao: Sessao = Depends(exigir("backup:exportar")),
    db: Session = Depends(get_db),
):
    """As últimas exportações do escritório: quem, quando e de onde."""
    _escritorio_inteiro(sessao)
    linhas = db.execute(
        select(LogAcesso.criado_em, LogAcesso.ip, Usuario.nome)
        .join(Usuario, Usuario.id == LogAcesso.usuario_id)
        .where(LogAcesso.acao == ACAO, Usuario.cliente_id == sessao.cliente_id)
        .order_by(LogAcesso.criado_em.desc())
        .limit(10)
    ).all()
    return [
        {"quando": quando.isoformat(), "ip": ip, "por": nome}
        for quando, ip, nome in linhas
    ]
