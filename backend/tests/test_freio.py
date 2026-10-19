"""Freio de pedidos por minuto: a cota é de quem pede, não do sistema inteiro.

Em produção o freio contava por endereço, e no Render todo pedido chega com o
endereço do intermediário. O sistema inteiro dividia uma cota de 300 pedidos
por minuto: um robô varrendo o endereço público da API esgotou a cota, e o
login passou a responder "muitas tentativas" — sem que tentativa alguma
chegasse ao banco.
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import criar_token
from app.core.seguranca_http import FreioDeRequisicoes


def _app(limite: int = 3) -> TestClient:
    app = FastAPI()
    app.add_middleware(FreioDeRequisicoes, limite=limite, janela_segundos=60)

    @app.get("/coisa")
    def coisa():
        return {"ok": True}

    return TestClient(app)


def _token() -> dict:
    return {"Authorization": f"Bearer {criar_token(uuid.uuid4(), uuid.uuid4())}"}


def test_sem_token_conta_por_endereco():
    cliente = _app()
    assert [cliente.get("/coisa").status_code for _ in range(4)] == [200, 200, 200, 429]


def test_robo_sem_token_nao_esgota_a_cota_de_quem_esta_logado():
    """O caso de produção: a enxurrada anônima não pode trancar os usuários."""
    cliente = _app()
    for _ in range(10):
        cliente.get("/coisa")
    assert cliente.get("/coisa").status_code == 429
    assert cliente.get("/coisa", headers=_token()).status_code == 200


def test_um_usuario_nao_esgota_a_cota_de_outro():
    cliente = _app()
    ana, bia = _token(), _token()
    assert [cliente.get("/coisa", headers=ana).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert cliente.get("/coisa", headers=bia).status_code == 200


def test_token_forjado_nao_ganha_cota_propria():
    """Sem conferir a assinatura, cada token inventado seria uma cota nova."""
    cliente = _app()
    forjados = [{"Authorization": f"Bearer forjado.{i}.token"} for i in range(4)]
    assert [cliente.get("/coisa", headers=h).status_code for h in forjados] == [200, 200, 200, 429]


def test_mensagem_diz_a_espera_verdadeira():
    cliente = _app(limite=1)
    cliente.get("/coisa")
    r = cliente.get("/coisa")
    assert r.status_code == 429
    assert "um minuto" in r.json()["detail"]
    assert r.headers["retry-after"] == "60"
