"""Coleta de conteúdo normativo para o monitoramento (§35).

Não há integração oficial com o Diário Oficial nem com os cartórios de RCPJ.
Portanto: onde existe endereço público estável, o coletor busca o conteúdo e
compara a impressão digital; onde não existe, o monitoramento vira **tarefa de
reconferência manual** com responsável e prazo. O sistema nunca simula uma
consulta que não fez.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Coleta:
    sucesso: bool
    conteudo: str | None = None
    hash_conteudo: str | None = None
    erro: str | None = None
    manual: bool = False


def impressao_digital(conteudo: str) -> str:
    """Hash do texto normalizado — ignora variações de espaço e capitalização."""
    normalizado = re.sub(r"\s+", " ", conteudo or "").strip().lower()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def texto_de_html(html: str) -> str:
    sem_script = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    sem_tags = re.sub(r"(?s)<[^>]+>", " ", sem_script)
    return re.sub(r"\s+", " ", sem_tags).strip()


class Coletor(Protocol):
    def coletar(self, url: str | None) -> Coleta: ...


class ColetorManual:
    """Padrão do sistema: exige conferência humana e registro da evidência."""

    def coletar(self, url: str | None) -> Coleta:
        return Coleta(
            sucesso=False,
            manual=True,
            erro="Fonte sem coleta automatizada. Reconferência manual necessária.",
        )


class ColetorHTTP:
    """Busca o conteúdo publicado no endereço oficial cadastrado.

    Usado apenas para fontes com URL estável (ex.: texto compilado no Planalto).
    Falha de rede não vira "sem alteração": vira erro registrado no monitoramento.
    """

    def __init__(self, timeout: int = 20, user_agent: str = "TERCEIRO360/1.0") -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    def coletar(self, url: str | None) -> Coleta:
        if not url:
            return ColetorManual().coletar(url)
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                bruto = resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Coleta(sucesso=False, erro=f"Falha ao consultar {url}: {exc}")

        texto = texto_de_html(bruto)
        return Coleta(sucesso=True, conteudo=texto, hash_conteudo=impressao_digital(texto))
