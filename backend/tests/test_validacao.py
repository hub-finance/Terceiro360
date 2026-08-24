"""Os cenários do §24 do prompt mestre, verificados de ponta a ponta."""
import datetime as dt

from app.core.enums import Semaforo
from app.engines.conformidade.resolucao import ParametroEstatutario
from app.engines.validacao.contexto import MandatoInfo, MembroInfo
from app.engines.validacao.motor import validar


def _codigos(resultado):
    return {a.codigo.split("::")[0] for a in resultado.achados}


def test_mandato_expirado_bloqueia_o_ato(montar_contexto):
    """§24 — mandato termina em 30/06/2026; eleição informada para 15/08/2026."""
    mandato = MandatoInfo(
        id="m1", orgao="DIRETORIA", designacao="GESTÃO 2024–2026",
        data_inicio=dt.date(2024, 7, 1), data_fim=dt.date(2026, 6, 30),
        membros=[MembroInfo("p1", "Maria Aparecida Souza", "Presidente", "PRESIDENTE")],
    )
    ctx = montar_contexto(
        "ELEICAO_DIRETORIA",
        data_ato=dt.date(2026, 8, 15),
        mandatos=[mandato],
        dados={"data_edital": "2026-07-25", "eleitos": [{"nome": "X", "cargo": "Presidente"}]},
    )
    r = validar(ctx)
    assert r.semaforo is Semaforo.BLOQUEADO
    assert not r.pode_gerar_documentos
    achado = next(a for a in r.achados if a.codigo == "MANDATO_EXPIRADO")
    assert "30/06/2026" in achado.mensagem and "15/08/2026" in achado.mensagem


def test_prazo_de_convocacao_inferior_ao_estatuto(montar_contexto):
    """§24 — estatuto exige 15 dias; edital publicado 5 dias antes."""
    ctx = montar_contexto(
        "ASSEMBLEIA_EXTRAORDINARIA",
        data_ato=dt.date(2026, 5, 20),
        dados={"data_edital": "2026-05-15", "convocado_por": "Presidente"},
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "CONVOCACAO_PRAZO_INSUFICIENTE")
    assert achado.severidade is Semaforo.BLOQUEADO
    assert achado.dados == {"exigido": 15, "realizado": 5}
    # A conclusão precisa vir fundamentada: estatuto + art. 60 do Código Civil.
    referencias = " ".join(str(f) for f in achado.fundamentos)
    assert "Estatuto Social" in referencias and "art. 60" in referencias


def test_divergencia_de_presidente_e_pendencia_nao_bloqueio(montar_contexto):
    """§24 — ata informa presidente diferente do cadastro."""
    ctx = montar_contexto(
        "ASSEMBLEIA_ORDINARIA",
        data_ato=dt.date(2026, 4, 10),
        dados={
            "data_edital": "2026-03-20",
            "convocado_por": "Presidente",
            "presidente_mesa": "Carlos Eduardo Nunes",
            "total_presentes": 25,
            "convocacao": "PRIMEIRA",
        },
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "DIVERGENCIA_CADASTRAL_PRESIDENTE")
    assert achado.severidade is Semaforo.PENDENCIA
    assert achado.dados["cadastrado"] == "Maria Aparecida Souza"


def test_quorum_informado_compativel_com_o_estatuto(montar_contexto):
    """§13 — 🟢 quórum informado compatível com o estatuto cadastrado."""
    ctx = montar_contexto(
        "ASSEMBLEIA_ORDINARIA",
        data_ato=dt.date(2026, 4, 10),
        dados={
            "data_edital": "2026-03-20",
            "convocado_por": "Presidente",
            "total_presentes": 16,   # metade mais um de 30 aptos
            "convocacao": "PRIMEIRA",
        },
        associados_aptos=30,
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "QUORUM_INSTALACAO_OK")
    assert achado.severidade is Semaforo.APTO
    assert "16 presentes" in achado.mensagem


def test_quorum_insuficiente_bloqueia(montar_contexto):
    ctx = montar_contexto(
        "ASSEMBLEIA_ORDINARIA",
        data_ato=dt.date(2026, 4, 10),
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "total_presentes": 12, "convocacao": "PRIMEIRA"},
        associados_aptos=30,
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "QUORUM_INSTALACAO_INSUFICIENTE")
    assert achado.severidade is Semaforo.BLOQUEADO
    assert achado.dados["minimo"] == 16


def test_segunda_convocacao_dispensa_quorum_quando_o_estatuto_permite(montar_contexto):
    ctx = montar_contexto(
        "ASSEMBLEIA_ORDINARIA",
        data_ato=dt.date(2026, 4, 10),
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "total_presentes": 5, "convocacao": "SEGUNDA"},
        associados_aptos=30,
    )
    r = validar(ctx)
    assert "QUORUM_INSTALACAO_INSUFICIENTE" not in _codigos(r)


def test_estatuto_ausente_bloqueia_ato_assembleal(montar_contexto):
    ctx = montar_contexto(
        "REFORMA_ESTATUTARIA", data_ato=dt.date(2026, 4, 10), estatuto=None, parametros=[]
    )
    r = validar(ctx)
    assert r.semaforo is Semaforo.BLOQUEADO
    assert "ESTATUTO_NAO_CADASTRADO" in _codigos(r)


def test_parametro_nao_confirmado_gera_validacao_necessaria(montar_contexto):
    ctx = montar_contexto(
        "REFORMA_ESTATUTARIA",
        data_ato=dt.date(2026, 4, 10),
        parametros=[
            ParametroEstatutario("CONVOCACAO_PRAZO_DIAS", 15, confirmado=True),
            ParametroEstatutario("QUORUM_REFORMA_ESTATUTARIA", "2/3", confirmado=False,
                                 dispositivo="art. 30"),
        ],
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "ordem_do_dia": ["Reforma do estatuto social"]},
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo.startswith("PARAMETRO_NAO_CONFIRMADO"))
    assert achado.severidade is Semaforo.PENDENCIA
    assert "VALIDAÇÃO NECESSÁRIA" in achado.titulo


def test_materia_fora_da_ordem_do_dia_bloqueia_destituicao(montar_contexto):
    ctx = montar_contexto(
        "DESTITUICAO",
        data_ato=dt.date(2026, 4, 10),
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "ordem_do_dia": ["Assuntos gerais"], "total_presentes": 25},
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "MATERIA_FORA_DA_ORDEM_DO_DIA")
    assert achado.severidade is Semaforo.BLOQUEADO
    assert any("art. 59" in str(f) for f in achado.fundamentos)


def test_reforma_estatutaria_com_votos_insuficientes(montar_contexto):
    ctx = montar_contexto(
        "REFORMA_ESTATUTARIA",
        data_ato=dt.date(2026, 4, 10),
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "ordem_do_dia": ["Reforma estatutária"], "total_presentes": 30,
               "votos_favor": 15},
    )
    r = validar(ctx)
    achado = next(a for a in r.achados if a.codigo == "QUORUM_DELIBERACAO_INSUFICIENTE")
    assert achado.dados["minimo"] == 20  # 2/3 de 30 presentes


def test_semaforo_e_o_pior_achado(montar_contexto):
    ctx = montar_contexto(
        "ELEICAO_DIRETORIA",
        data_ato=dt.date(2026, 4, 10),
        dados={"data_edital": "2026-03-20", "convocado_por": "Presidente",
               "total_presentes": 20, "eleitos": [{"nome": "X", "cargo": "Presidente"}]},
        associados_aptos=30,
    )
    r = validar(ctx)
    assert r.semaforo is Semaforo.PENDENCIA  # documentos ainda não reunidos
    assert r.pode_gerar_documentos is True
