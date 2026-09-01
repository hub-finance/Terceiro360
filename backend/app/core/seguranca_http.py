"""Defesas de borda: cabeçalhos de resposta e freio de requisições (§31).

São as proteções que valem para toda a API, independentemente da rota. Ficam
aqui, e não espalhadas por cada endpoint, porque defesa que depende de o
programador lembrar de aplicar é defesa que uma hora falta.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Um navegador só respeita o que o servidor manda. Cada cabeçalho abaixo fecha
# uma porta concreta:
CABECALHOS = {
    # Impede o navegador de "adivinhar" que um .txt é na verdade um script.
    "X-Content-Type-Options": "nosniff",
    # Impede que o painel seja embutido em iframe de outro site (clickjacking:
    # o atacante põe a tela real por baixo de botões falsos).
    "X-Frame-Options": "DENY",
    # Não vaza a URL interna que o usuário estava vendo ao clicar num link
    # externo — a URL carrega identificador de entidade e de documento.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # A API não usa câmera, microfone nem geolocalização. Dizer isso barra o
    # uso por qualquer coisa injetada na página.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
}

# A API responde JSON, nunca HTML. Uma política restritiva aqui é de graça, e
# transforma um eventual retorno de HTML inesperado em página inerte.
CSP_API = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)

# A documentação interativa monta a página com script e estilo de CDN, então
# precisa de política própria — só para ela, e só fora de produção.
CSP_DOCS = (
    "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
    "script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' "
    "https://cdn.jsdelivr.net; frame-ancestors 'none'"
)


class CabecalhosSeguranca(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resposta = await call_next(request)
        for chave, valor in CABECALHOS.items():
            resposta.headers.setdefault(chave, valor)

        caminho = request.url.path
        ehdocs = caminho in ("/docs", "/redoc") or caminho.startswith("/docs")
        resposta.headers.setdefault(
            "Content-Security-Policy", CSP_DOCS if ehdocs else CSP_API
        )

        if settings.em_producao:
            # Só em produção: em desenvolvimento o HSTS gravaria "sempre HTTPS"
            # para localhost no navegador do programador, e localhost não tem
            # certificado — a partir daí nada mais abre.
            resposta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resposta


class FreioDeRequisicoes(BaseHTTPMiddleware):
    """Janela deslizante por IP.

    Limitação honesta: a contagem vive na memória do processo. Com várias
    réplicas, cada uma conta a sua parte, e o limite real vira N vezes o
    configurado. Serve contra varredura e script solto — que é o que aparece
    todo dia. Para um ataque sério e distribuído, o freio precisa estar antes
    da aplicação, na CDN ou no proxy reverso, e é lá que ele deve ficar mesmo:
    filtrar tráfego hostil dentro do processo já é gastar o processo.

    O login tem freio próprio, mais estreito e persistido em banco
    (`app/api/rotas/auth.py`), porque ali a tentativa precisa deixar rastro.
    """

    def __init__(self, app, limite: int = 300, janela_segundos: int = 60):
        super().__init__(app)
        self.limite = limite
        self.janela = janela_segundos
        self._batidas: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in ("/saude", "/"):
            return await call_next(request)

        chave = request.client.host if request.client else "desconhecido"
        agora = time.monotonic()
        batidas = self._batidas[chave]
        while batidas and agora - batidas[0] > self.janela:
            batidas.popleft()

        if len(batidas) >= self.limite:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Muitas requisições. Aguarde um instante."},
                headers={"Retry-After": str(self.janela)},
            )

        batidas.append(agora)
        # Sem esta poda, um atacante trocando de IP a cada requisição encheria
        # a memória do processo — a própria defesa viraria o ataque.
        if len(self._batidas) > 10_000:
            for ip in [i for i, b in self._batidas.items() if not b or agora - b[-1] > self.janela]:
                del self._batidas[ip]

        return await call_next(request)
