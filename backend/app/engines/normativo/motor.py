"""MOTOR DE ATUALIZAÇÃO NORMATIVA.

Ciclo completo de uma mudança na base legal:

    VIGIAR → DETECTAR → TRIAR → CURAR (humano) → PUBLICAR → IMPACTAR → REVALIDAR

Princípios inegociáveis:

* nenhuma versão de norma entra em vigor no motor sem curadoria de um
  responsável habilitado (§37, §46, §47);
* toda detecção guarda evidência: URL, hash anterior, hash novo e diff;
* publicar uma norma nova não reescreve o passado — a redação antiga continua
  citável para os atos praticados na sua vigência (§20, §38);
* o que a mudança atinge é calculado a partir de vínculos declarados, não
  adivinhado.
"""
from __future__ import annotations

import datetime as dt
import difflib
from dataclasses import dataclass, field

from app.core.enums import (
    AlvoImpacto,
    OrigemDeteccao,
    SeveridadeImpacto,
    SituacaoAtualizacao,
    SituacaoVersaoNorma,
)
from app.engines.normativo.coletor import Coleta, Coletor, ColetorManual, impressao_digital


# --------------------------------------------------------------- Estruturas


@dataclass
class VersaoNorma:
    numero: int
    situacao: SituacaoVersaoNorma
    vigente_desde: dt.date | None = None
    vigente_ate: dt.date | None = None
    texto: str | None = None
    hash_conteudo: str | None = None
    curado_por: str | None = None
    curado_em: dt.datetime | None = None

    @property
    def curada(self) -> bool:
        return bool(self.curado_por and self.curado_em)


@dataclass
class Vinculo:
    """Um artefato do sistema declaradamente apoiado numa norma."""

    alvo_tipo: AlvoImpacto
    alvo_ref: str
    fonte_chave: str
    dispositivo: str | None = None
    severidade_padrao: SeveridadeImpacto = SeveridadeImpacto.REVISAO_RECOMENDADA


@dataclass
class Deteccao:
    """Resultado de uma verificação de monitoramento."""

    houve_mudanca: bool
    motivo: str
    hash_anterior: str | None = None
    hash_novo: str | None = None
    diff: str | None = None
    erro: str | None = None
    exige_conferencia_manual: bool = False


@dataclass
class Impacto:
    alvo_tipo: AlvoImpacto
    alvo_ref: str
    severidade: SeveridadeImpacto
    descricao: str


@dataclass
class Publicacao:
    """Efeito de publicar uma atualização já curada."""

    versao_anterior: VersaoNorma | None
    versao_nova: VersaoNorma
    impactos: list[Impacto] = field(default_factory=list)


class CuradoriaObrigatoria(RuntimeError):
    """Publicar sem curadoria humana é erro de programa, não decisão de negócio."""


# ------------------------------------------------------------------ Motor


class MotorAtualizacaoNormativa:
    def __init__(self, coletor: Coletor | None = None) -> None:
        self._coletor = coletor or ColetorManual()

    # ------------------------------------------------------------ detecção

    def verificar(
        self,
        url: str | None,
        hash_anterior: str | None,
        texto_anterior: str | None = None,
        coleta: Coleta | None = None,
    ) -> Deteccao:
        """Compara o conteúdo publicado com a última impressão digital conhecida."""
        resultado = coleta or self._coletor.coletar(url)

        if not resultado.sucesso:
            return Deteccao(
                houve_mudanca=False,
                motivo=resultado.erro or "Coleta não realizada.",
                hash_anterior=hash_anterior,
                erro=resultado.erro,
                exige_conferencia_manual=True,
            )

        novo_hash = resultado.hash_conteudo or impressao_digital(resultado.conteudo or "")

        if hash_anterior is None:
            return Deteccao(
                houve_mudanca=False,
                motivo="Primeira coleta: impressão digital registrada como linha de base.",
                hash_novo=novo_hash,
            )

        if novo_hash == hash_anterior:
            return Deteccao(
                houve_mudanca=False,
                motivo="Conteúdo idêntico à última verificação.",
                hash_anterior=hash_anterior,
                hash_novo=novo_hash,
            )

        return Deteccao(
            houve_mudanca=True,
            motivo="O texto publicado na fonte oficial mudou desde a última verificação.",
            hash_anterior=hash_anterior,
            hash_novo=novo_hash,
            diff=self.diff(texto_anterior or "", resultado.conteudo or ""),
        )

    @staticmethod
    def diff(anterior: str, novo: str, contexto: int = 2, max_linhas: int = 400) -> str:
        """Diff legível entre duas redações, por sentença."""
        def sentencas(texto: str) -> list[str]:
            partes = [s.strip() for s in texto.replace(";", ".\n").split(".") if s.strip()]
            return [p + "." for p in partes]

        linhas = list(
            difflib.unified_diff(
                sentencas(anterior), sentencas(novo),
                fromfile="redação anterior", tofile="redação nova",
                n=contexto, lineterm="",
            )
        )
        if len(linhas) > max_linhas:
            linhas = linhas[:max_linhas] + [f"... (+{len(linhas) - max_linhas} linhas)"]
        return "\n".join(linhas)

    # -------------------------------------------------------------- impacto

    def calcular_impactos(
        self,
        fonte_chave: str,
        dispositivos_alterados: list[str] | None,
        vinculos: list[Vinculo],
    ) -> list[Impacto]:
        """O que essa mudança atinge — a partir dos vínculos declarados.

        Sem `dispositivos_alterados`, o alcance é toda a norma: melhor revisar
        demais do que deixar passar uma regra que virou letra morta.
        """
        alterados = set(dispositivos_alterados or [])
        impactos: list[Impacto] = []
        for v in vinculos:
            if v.fonte_chave != fonte_chave:
                continue
            if alterados and v.dispositivo and v.dispositivo not in alterados:
                continue
            escopo = (
                f"o dispositivo {v.dispositivo}" if v.dispositivo and alterados else "a norma"
            )
            impactos.append(
                Impacto(
                    alvo_tipo=v.alvo_tipo,
                    alvo_ref=v.alvo_ref,
                    severidade=v.severidade_padrao,
                    descricao=(
                        f"“{v.alvo_ref}” se apoia em {escopo} {fonte_chave}, que foi alterada. "
                        f"Revise antes de usar em novos atos."
                    ),
                )
            )
        return impactos

    # ------------------------------------------------------------ publicação

    def publicar(
        self,
        versao_atual: VersaoNorma | None,
        texto_novo: str,
        vigente_desde: dt.date,
        curado_por: str | None,
        curado_em: dt.datetime | None = None,
        resumo: str | None = None,
        dispositivos_alterados: list[str] | None = None,
        fonte_chave: str = "",
        vinculos: list[Vinculo] | None = None,
    ) -> Publicacao:
        if not curado_por:
            raise CuradoriaObrigatoria(
                "Uma versão de norma só entra em vigor depois de conferida por um responsável "
                "habilitado. Registre o curador antes de publicar."
            )
        if versao_atual and versao_atual.vigente_desde and vigente_desde < versao_atual.vigente_desde:
            raise ValueError(
                "A nova redação não pode começar a valer antes da redação que ela substitui."
            )

        nova = VersaoNorma(
            numero=(versao_atual.numero + 1) if versao_atual else 1,
            situacao=SituacaoVersaoNorma.VIGENTE,
            vigente_desde=vigente_desde,
            texto=texto_novo,
            hash_conteudo=impressao_digital(texto_novo),
            curado_por=curado_por,
            curado_em=curado_em or dt.datetime.utcnow(),
        )

        anterior = None
        if versao_atual is not None:
            anterior = VersaoNorma(
                numero=versao_atual.numero,
                situacao=SituacaoVersaoNorma.SUPERADA,
                vigente_desde=versao_atual.vigente_desde,
                # A redação antiga continua citável para os atos da sua época.
                vigente_ate=vigente_desde - dt.timedelta(days=1),
                texto=versao_atual.texto,
                hash_conteudo=versao_atual.hash_conteudo,
                curado_por=versao_atual.curado_por,
                curado_em=versao_atual.curado_em,
            )

        impactos = self.calcular_impactos(fonte_chave, dispositivos_alterados, vinculos or [])
        return Publicacao(versao_anterior=anterior, versao_nova=nova, impactos=impactos)

    # ------------------------------------------------------------- vigilância

    @staticmethod
    def proxima_verificacao(ultima: dt.datetime | None, periodicidade_dias: int) -> dt.date:
        base = (ultima or dt.datetime.utcnow()).date()
        return base + dt.timedelta(days=periodicidade_dias)

    @staticmethod
    def situacao_da_vigilancia(
        ultima: dt.datetime | None, periodicidade_dias: int, agora: dt.datetime | None = None
    ) -> str:
        agora = agora or dt.datetime.utcnow()
        if ultima is None:
            return "NUNCA_VERIFICADA"
        atraso = (agora - ultima).days - periodicidade_dias
        if atraso > periodicidade_dias:
            return "ATRASADA"
        if atraso >= 0:
            return "VENCIDA"
        return "EM_DIA"


SITUACAO_ATUALIZACAO_INICIAL = SituacaoAtualizacao.DETECTADA
ORIGEM_PADRAO = OrigemDeteccao.MANUAL
