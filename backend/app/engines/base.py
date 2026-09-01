"""Tipos compartilhados pelos motores do TERCEIRO360.

Todo motor devolve *achados* com fundamentação explícita. Nenhum motor
conclui sem dizer de onde veio a regra que aplicou (§38).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from app.core.tempo import agora
from app.core.enums import OrigemDado, Semaforo, StatusParametro


@dataclass(frozen=True)
class Fundamento:
    """A base normativa/estatutária de uma conclusão (§38)."""

    origem: OrigemDado
    referencia: str                      # "Lei nº 10.406/2002" | "Estatuto Social"
    dispositivo: str | None = None       # "art. 59, parágrafo único"
    trecho: str | None = None
    versao_norma: str | None = None      # "redação vigente desde 01/01/2003"
    curado: bool | None = None           # None = não aplicável (estatuto/cadastro)
    url: str | None = None

    def __str__(self) -> str:
        partes = [self.referencia]
        if self.dispositivo:
            partes.append(self.dispositivo)
        if self.versao_norma:
            partes.append(f"({self.versao_norma})")
        return ", ".join(partes)


@dataclass
class ParametroResolvido:
    """Um parâmetro aplicável ao caso concreto, com procedência declarada.

    O sistema jamais devolve um valor "porque é o usual": ou o parâmetro está
    cadastrado e confirmado, ou volta como DADO_NAO_INFORMADO /
    VALIDACAO_NECESSARIA (§46).
    """

    chave: str
    valor: Any = None
    status: StatusParametro = StatusParametro.NAO_INFORMADO
    origem: OrigemDado | None = None
    fundamento: Fundamento | None = None
    observacao: str | None = None
    conflito_com: list[Fundamento] = field(default_factory=list)

    @property
    def utilizavel(self) -> bool:
        return self.status is StatusParametro.CONFIRMADO and self.valor is not None

    def __bool__(self) -> bool:  # evita uso acidental de parâmetro não confirmado
        return self.utilizavel


@dataclass
class Achado:
    """Resultado individual de um check (§12/§13)."""

    codigo: str
    severidade: Semaforo
    titulo: str
    mensagem: str
    fundamentos: list[Fundamento] = field(default_factory=list)
    campo: str | None = None
    sugestao: str | None = None
    dados: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "severidade": self.severidade.value,
            "icone": self.severidade.icone,
            "titulo": self.titulo,
            "mensagem": self.mensagem,
            "campo": self.campo,
            "sugestao": self.sugestao,
            "fundamentos": [
                {
                    "origem": f.origem.value,
                    "referencia": f.referencia,
                    "dispositivo": f.dispositivo,
                    "trecho": f.trecho,
                    "versao_norma": f.versao_norma,
                    "curado": f.curado,
                    "url": f.url,
                }
                for f in self.fundamentos
            ],
            "dados": self.dados,
        }


@dataclass
class ResultadoValidacao:
    """§13 — o semáforo é o pior achado encontrado."""

    achados: list[Achado] = field(default_factory=list)
    parametros: dict[str, ParametroResolvido] = field(default_factory=dict)
    avaliado_em: dt.datetime = field(default_factory=agora)

    @property
    def semaforo(self) -> Semaforo:
        if not self.achados:
            return Semaforo.APTO
        return max((a.severidade for a in self.achados), key=lambda s: s.peso)

    @property
    def bloqueios(self) -> list[Achado]:
        return [a for a in self.achados if a.severidade is Semaforo.BLOQUEADO]

    @property
    def pendencias(self) -> list[Achado]:
        return [a for a in self.achados if a.severidade is Semaforo.PENDENCIA]

    @property
    def pode_gerar_documentos(self) -> bool:
        """§13 — 🔴 impede a geração; 🟡 gera com ressalva registrada."""
        return not self.bloqueios

    def to_dict(self) -> dict:
        return {
            "semaforo": self.semaforo.value,
            "icone": self.semaforo.icone,
            "pode_gerar_documentos": self.pode_gerar_documentos,
            "total_achados": len(self.achados),
            "bloqueios": len(self.bloqueios),
            "pendencias": len(self.pendencias),
            "avaliado_em": self.avaliado_em.isoformat(),
            "achados": [a.to_dict() for a in self.achados],
            "parametros": {
                chave: {
                    "valor": p.valor,
                    "status": p.status.value,
                    "origem": p.origem.value if p.origem else None,
                    "fundamento": str(p.fundamento) if p.fundamento else None,
                    "observacao": p.observacao,
                }
                for chave, p in self.parametros.items()
            },
        }
