"""Consulta de CNPJ: o que precisa valer mesmo com a rede fora do ar.

Nenhum teste aqui chama a internet. O que se testa é o que quebra de verdade:
CNPJ com dígito errado saindo da máquina à toa, uma fonte fora derrubando a
consulta inteira, e natureza jurídica sendo chutada quando não deveria.
"""
from __future__ import annotations

import datetime as dt

import httpx
import pytest

from app.core.enums import TipoEntidade
from app.modules.entidades import receita

# Resposta real da BrasilAPI, reduzida aos campos que o sistema lê.
BRASILAPI = {
    "cnpj": "33683111000280",
    "razao_social": "ASSOCIACAO BENEFICENTE EXEMPLO",
    "nome_fantasia": "ABE",
    "natureza_juridica": "399-9 - Associação Privada",
    "data_inicio_atividade": "1998-03-16",
    "descricao_situacao_cadastral": "ATIVA",
    "logradouro": "RUA DAS FLORES",
    "numero": "120",
    "complemento": "SALA 3",
    "bairro": "CENTRO",
    "municipio": "BELO HORIZONTE",
    "uf": "MG",
    "cep": "30130000",
    "email": "contato@exemplo.org",
    "ddd_telefone_1": "3132000000",
}

RECEITAWS = {
    "cnpj": "33.683.111/0002-80",
    "nome": "FUNDACAO EXEMPLO",
    "fantasia": "",
    "natureza_juridica": "306-9 - Fundação Privada",
    "abertura": "16/03/1998",
    "situacao": "BAIXADA",
    "municipio": "SAO PAULO",
    "uf": "SP",
    "cep": "01310-100",
}


def transporte(*respostas: httpx.Response) -> httpx.Client:
    """Cliente que devolve as respostas na ordem, uma por chamada."""
    fila = list(respostas)

    def responder(requisicao: httpx.Request) -> httpx.Response:
        if not fila:
            raise httpx.ConnectError("sem resposta preparada", request=requisicao)
        return fila.pop(0)

    return httpx.Client(transport=httpx.MockTransport(responder))


class TestCnpj:
    def test_digito_verificador_confere(self):
        assert receita.validar("00.000.000/0001-91") == "00000000000191"

    def test_digito_errado_nao_vira_chamada_de_rede(self):
        # Sem cliente nenhum: se tentasse a rede, o teste falharia por outra razão.
        with pytest.raises(receita.CnpjInvalido):
            receita.consultar("00.000.000/0001-92")

    def test_sequencia_repetida_e_rejeitada(self):
        # Passa no cálculo do módulo 11, e mesmo assim não existe.
        with pytest.raises(receita.CnpjInvalido):
            receita.validar("11111111111111")

    def test_tamanho_errado(self):
        with pytest.raises(receita.CnpjInvalido):
            receita.validar("123")


class TestNatureza:
    @pytest.mark.parametrize(
        "natureza,esperado",
        [
            ("399-9 - Associação Privada", TipoEntidade.ASSOCIACAO),
            ("322-0 - Organização Religiosa", TipoEntidade.ORGANIZACAO_RELIGIOSA),
            ("306-9 - Fundação Privada", TipoEntidade.FUNDACAO),
        ],
    )
    def test_reconhece(self, natureza, esperado):
        assert receita.tipo_pela_natureza(natureza) is esperado

    @pytest.mark.parametrize(
        "natureza",
        ["313-1 - Entidade Sindical", "308-5 - Condomínio Edilício", "", None],
    )
    def test_nao_chuta_o_que_nao_reconhece(self, natureza):
        # Devolver None faz a tela manter a escolha do usuário. Chutar um tipo
        # aqui contaminaria toda a validação do ato depois.
        assert receita.tipo_pela_natureza(natureza) is None


class TestConsulta:
    def test_preenche_a_partir_da_primeira_fonte(self):
        cliente = transporte(httpx.Response(200, json=BRASILAPI))
        dados = receita.consultar("33.683.111/0002-80", cliente=cliente)

        assert dados.razao_social == "ASSOCIACAO BENEFICENTE EXEMPLO"
        assert dados.tipo_entidade == TipoEntidade.ASSOCIACAO.value
        assert dados.data_constituicao == dt.date(1998, 3, 16)
        assert dados.cep == "30130-000"
        assert dados.uf == "MG"
        assert dados.situacao_exige_atencao is False
        assert "BrasilAPI" in dados.fonte

    def test_cai_para_a_segunda_fonte_quando_a_primeira_falha(self):
        cliente = transporte(
            httpx.Response(429, text="limite excedido"),
            httpx.Response(200, json=RECEITAWS),
        )
        dados = receita.consultar("33.683.111/0002-80", cliente=cliente)

        assert dados.razao_social == "FUNDACAO EXEMPLO"
        assert dados.tipo_entidade == TipoEntidade.FUNDACAO.value
        assert dados.data_constituicao == dt.date(1998, 3, 16)
        assert "ReceitaWS" in dados.fonte

    def test_situacao_baixada_e_sinalizada(self):
        cliente = transporte(httpx.Response(500), httpx.Response(200, json=RECEITAWS))
        dados = receita.consultar("33.683.111/0002-80", cliente=cliente)
        assert dados.situacao_cadastral == "BAIXADA"
        assert dados.situacao_exige_atencao is True

    def test_nao_encontrado_nao_tenta_a_proxima_fonte(self):
        # 404 é resposta sobre o CNPJ, não sobre o serviço: insistir noutra
        # fonte só gastaria tempo para chegar à mesma conclusão.
        cliente = transporte(httpx.Response(404), httpx.Response(200, json=BRASILAPI))
        with pytest.raises(receita.NaoEncontrado):
            receita.consultar("33.683.111/0002-80", cliente=cliente)

    def test_todas_as_fontes_fora_vira_servico_indisponivel(self):
        cliente = transporte(httpx.Response(503), httpx.Response(503))
        with pytest.raises(receita.ServicoIndisponivel):
            receita.consultar("33.683.111/0002-80", cliente=cliente)

    def test_json_quebrado_nao_derruba_a_consulta(self):
        cliente = transporte(
            httpx.Response(200, text="<html>manutenção</html>"),
            httpx.Response(200, json=RECEITAWS),
        )
        dados = receita.consultar("33.683.111/0002-80", cliente=cliente)
        assert dados.razao_social == "FUNDACAO EXEMPLO"
