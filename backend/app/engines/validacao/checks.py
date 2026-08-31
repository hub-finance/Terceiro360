"""CHECK JURÍDICO e CHECK DOCUMENTAL (§12).

Regras de ouro deste arquivo:

* nenhum check conclui a partir de valor presumido — se o parâmetro não está
  confirmado, o resultado é 🟡 pedindo confirmação, nunca 🟢 por conveniência;
* todo achado carrega fundamento;
* 🔴 significa "não gere o documento assim"; 🟡 significa "falta informação ou
  conferência"; 🟢 é o silêncio dos checks.
"""
from __future__ import annotations

import datetime as dt
from typing import Iterable

from app.core.enums import OrigemDado, Semaforo, StatusParametro, TipoEvento
from app.engines.base import Achado, Fundamento
from app.engines.conformidade.catalogo import CATALOGO, obrigatorios_para
from app.engines.conformidade.matriz import MATRIZ, EspecieAssembleia, ExigeReforma, ato
from app.engines.conformidade.quorum import BaseQuorum, interpretar_quorum
from app.engines.validacao.contexto import ContextoValidacao
from app.engines.validacao.registro import check

# As listas abaixo derivam da matriz de atos: acrescentar um ato novo lá o faz
# entrar automaticamente nos checks certos, sem editar este arquivo (§55).
EVENTOS_ASSEMBLEARES = tuple(t for t, a in MATRIZ.items() if a.assemblear)

# Atos de competência privativa da assembleia geral, em reunião especialmente
# convocada para esse fim (Código Civil, art. 59 e parágrafo único).
EVENTOS_COMPETENCIA_PRIVATIVA = tuple(
    t for t, a in MATRIZ.items() if a.exige_convocacao_especifica
)

EVENTOS_QUE_EXIGEM_ESTATUTO = tuple(
    t for t, a in MATRIZ.items()
    if a.assemblear or a.tipo in (
        TipoEvento.POSSE_DIRETORIA.value, TipoEvento.RENUNCIA.value,
        TipoEvento.SUBSTITUICAO.value, TipoEvento.VACANCIA.value,
    )
)

_FUND_ESTATUTO = Fundamento(
    origem=OrigemDado.ESTATUTO, referencia="Estatuto Social da entidade"
)


def _fund_legal(ctx: ContextoValidacao, chave: str, dispositivo: str) -> list[Fundamento]:
    f = ctx.resolvedor._normas.fundamento(chave, dispositivo, ctx.data_efetiva)
    return [f] if f else []


# --------------------------------------------------------------- Cadastro


@check("ENTIDADE_IDENTIFICACAO", "Identificação mínima da entidade", grupo="CADASTRO")
def entidade_identificacao(ctx: ContextoValidacao) -> Iterable[Achado]:
    if not ctx.entidade.cnpj:
        yield Achado(
            codigo="ENTIDADE_SEM_CNPJ",
            severidade=Semaforo.PENDENCIA,
            titulo="CNPJ não cadastrado",
            mensagem="A entidade está sem CNPJ no cadastro. Documentos e requerimentos "
                     "sairão com a marcação DADO NÃO INFORMADO nesse campo.",
            campo="entidade.cnpj",
            sugestao="Cadastre o CNPJ em Entidades → Dados gerais.",
        )
    if not (ctx.entidade.municipio and ctx.entidade.uf):
        yield Achado(
            codigo="ENTIDADE_SEM_ENDERECO",
            severidade=Semaforo.PENDENCIA,
            titulo="Município/UF não cadastrados",
            mensagem="Sem município e UF o sistema não consegue identificar o RCPJ competente.",
            campo="entidade.municipio",
        )


# --------------------------------------------------------------- Estatuto


@check("ESTATUTO_VIGENTE", "Existe estatuto vigente cadastrado",
       eventos=EVENTOS_QUE_EXIGEM_ESTATUTO, fundamentos=("CC_2002",))
def estatuto_vigente(ctx: ContextoValidacao) -> Iterable[Achado]:
    if ctx.estatuto is None:
        yield Achado(
            codigo="ESTATUTO_NAO_CADASTRADO",
            severidade=Semaforo.BLOQUEADO,
            titulo="Estatuto não cadastrado",
            mensagem="Não há estatuto cadastrado para esta entidade. Sem as regras "
                     "estatutárias o sistema não tem como validar quórum, prazo de "
                     "convocação ou competência do órgão.",
            fundamentos=_fund_legal(ctx, "CC_2002", "art. 54"),
            sugestao="Cadastre o estatuto em Estatuto → Nova versão, ou importe o arquivo "
                     "para extração assistida.",
        )
        return
    if not ctx.estatuto.vigente:
        yield Achado(
            codigo="ESTATUTO_SEM_VERSAO_VIGENTE",
            severidade=Semaforo.BLOQUEADO,
            titulo="Nenhuma versão do estatuto está marcada como vigente",
            mensagem="Há versões cadastradas, mas nenhuma marcada como vigente.",
        )
    if not ctx.estatuto.data_registro:
        yield Achado(
            codigo="ESTATUTO_SEM_REGISTRO",
            severidade=Semaforo.PENDENCIA,
            titulo="Estatuto sem dados de registro",
            mensagem="A versão vigente do estatuto não tem número de registro, livro e folha. "
                     "Esses dados costumam ser exigidos no requerimento ao RCPJ.",
            fundamentos=_fund_legal(ctx, "LRP_1973", "art. 121"),
            campo="estatuto.numero_registro",
        )


@check("PARAMETROS_ESTATUTARIOS", "Parâmetros exigidos pelo ato estão confirmados")
def parametros_estatutarios(ctx: ContextoValidacao) -> Iterable[Achado]:
    for definicao in obrigatorios_para(ctx.tipo_evento):
        p = ctx.param(definicao.chave)
        if p.status is StatusParametro.CONFIRMADO:
            continue
        if p.status is StatusParametro.INCONSISTENCIA:
            yield Achado(
                codigo=f"PARAMETRO_CONFLITANTE::{definicao.chave}",
                severidade=Semaforo.BLOQUEADO,
                titulo=f"Conflito normativo: {definicao.rotulo}",
                mensagem=p.observacao or "Conflito entre a regra estatutária e a regra legal.",
                fundamentos=[f for f in ([p.fundamento] + p.conflito_com) if f],
                campo=definicao.chave,
                sugestao="Submeta o ponto à análise jurídica antes de prosseguir.",
            )
        elif p.status is StatusParametro.VALIDACAO_NECESSARIA:
            yield Achado(
                codigo=f"PARAMETRO_NAO_CONFIRMADO::{definicao.chave}",
                severidade=Semaforo.PENDENCIA,
                titulo=f"VALIDAÇÃO NECESSÁRIA: {definicao.rotulo}",
                mensagem=f"{definicao.pergunta_simples} O valor lido do estatuto foi "
                         f"“{p.valor}”, mas ainda não foi confirmado por um responsável.",
                fundamentos=[p.fundamento] if p.fundamento else [],
                campo=definicao.chave,
                sugestao="Confirme o parâmetro em Estatuto → Parâmetros.",
            )
        else:
            yield Achado(
                codigo=f"PARAMETRO_AUSENTE::{definicao.chave}",
                severidade=Semaforo.PENDENCIA,
                titulo=f"DADO NÃO INFORMADO: {definicao.rotulo}",
                mensagem=f"{definicao.pergunta_simples} Este parâmetro é necessário para "
                         f"validar o ato e não está cadastrado."
                         + (f" {definicao.nota}" if definicao.nota else ""),
                fundamentos=[p.fundamento] if p.fundamento else [],
                campo=definicao.chave,
                sugestao="Cadastre o parâmetro em Estatuto → Parâmetros.",
            )


# --------------------------------------------------------------- Mandato


@check("MANDATO_VIGENTE", "Mandato da diretoria vigente na data do ato")
def mandato_vigente(ctx: ContextoValidacao) -> Iterable[Achado]:
    if ctx.tipo_evento == TipoEvento.CONSTITUICAO.value:
        return
    mandato = ctx.mandato_mais_recente("DIRETORIA")
    if mandato is None:
        yield Achado(
            codigo="MANDATO_INEXISTENTE",
            severidade=Semaforo.PENDENCIA,
            titulo="Nenhum mandato de diretoria cadastrado",
            mensagem="Não há mandato registrado para a diretoria. Sem ele o sistema não "
                     "consegue verificar vigência nem preencher os documentos com os "
                     "dirigentes atuais.",
            sugestao="Cadastre a gestão atual em Diretoria → Mandatos.",
        )
        return

    data = ctx.data_efetiva
    if not mandato.vigente_em(data):
        vencido = mandato.data_fim < data
        yield Achado(
            codigo="MANDATO_EXPIRADO",
            severidade=Semaforo.BLOQUEADO,
            titulo="INCONSISTÊNCIA: mandato expirado",
            mensagem=(
                f"O mandato cadastrado ({mandato.designacao}) encerrou-se em "
                f"{mandato.data_fim:%d/%m/%Y}, antes da data informada para o ato "
                f"({data:%d/%m/%Y})."
                if vencido
                else f"O mandato {mandato.designacao} só inicia em "
                     f"{mandato.data_inicio:%d/%m/%Y}, depois da data do ato ({data:%d/%m/%Y})."
            ),
            campo="data_ato",
            dados={"mandato": mandato.designacao, "data_fim": mandato.data_fim.isoformat()},
            sugestao="Verifique a data do ato ou registre o ato de eleição que renovou a gestão. "
                     "Atos praticados por diretoria com mandato vencido costumam gerar exigência "
                     "no registro.",
        )
        return

    dias = (mandato.data_fim - data).days
    if dias <= 90:
        yield Achado(
            codigo="MANDATO_A_VENCER",
            severidade=Semaforo.PENDENCIA,
            titulo="Mandato próximo do fim",
            mensagem=f"O mandato {mandato.designacao} termina em {mandato.data_fim:%d/%m/%Y} "
                     f"({dias} dias). Verifique se a renovação já está encaminhada.",
            dados={"dias_restantes": dias},
        )


@check("REELEICAO_PERMITIDA", "Reeleição admitida pelo estatuto",
       eventos=(TipoEvento.REELEICAO_DIRETORIA.value,))
def reeleicao_permitida(ctx: ContextoValidacao) -> Iterable[Achado]:
    p = ctx.param("MANDATO_PERMITE_REELEICAO")
    if p.status is StatusParametro.CONFIRMADO and p.valor in (False, "false", "NAO", "NÃO", 0):
        yield Achado(
            codigo="REELEICAO_VEDADA",
            severidade=Semaforo.BLOQUEADO,
            titulo="Reeleição vedada pelo estatuto",
            mensagem="O parâmetro estatutário cadastrado indica que não há reeleição.",
            fundamentos=[p.fundamento] if p.fundamento else [],
            campo="MANDATO_PERMITE_REELEICAO",
        )


# --------------------------------------------------------------- Convocação


@check("CONVOCACAO_PRAZO", "Antecedência da convocação", eventos=EVENTOS_ASSEMBLEARES,
       fundamentos=("CC_2002",))
def convocacao_prazo(ctx: ContextoValidacao) -> Iterable[Achado]:
    data_edital = ctx.dado("data_edital") or ctx.dado("data_convocacao")
    if not data_edital:
        yield Achado(
            codigo="CONVOCACAO_SEM_DATA",
            severidade=Semaforo.PENDENCIA,
            titulo="DADO NÃO INFORMADO: data da convocação",
            mensagem="Informe a data de publicação do edital/aviso de convocação para que o "
                     "sistema possa conferir a antecedência exigida pelo estatuto.",
            campo="data_edital",
        )
        return

    if isinstance(data_edital, str):
        data_edital = dt.date.fromisoformat(data_edital)

    p = ctx.param("CONVOCACAO_PRAZO_DIAS")
    if not p.utilizavel:
        return  # já reportado por PARAMETROS_ESTATUTARIOS

    antecedencia = (ctx.data_efetiva - data_edital).days
    exigido = int(p.valor)
    if antecedencia < exigido:
        yield Achado(
            codigo="CONVOCACAO_PRAZO_INSUFICIENTE",
            severidade=Semaforo.BLOQUEADO,
            titulo="POSSÍVEL IRREGULARIDADE: prazo de convocação",
            mensagem=f"O estatuto exige {exigido} dias de antecedência e a convocação foi "
                     f"publicada em {data_edital:%d/%m/%Y}, {antecedencia} dias antes da "
                     f"assembleia marcada para {ctx.data_efetiva:%d/%m/%Y}.",
            fundamentos=([p.fundamento] if p.fundamento else [])
                        + _fund_legal(ctx, "CC_2002", "art. 60"),
            campo="data_edital",
            dados={"exigido": exigido, "realizado": antecedencia},
            sugestao="Remarque a assembleia ou republique a convocação respeitando o prazo. "
                     "Vício de convocação é causa recorrente de exigência e de anulação da "
                     "deliberação.",
        )


@check("CONVOCACAO_LEGITIMIDADE", "Legitimidade de quem convocou",
       eventos=EVENTOS_ASSEMBLEARES, fundamentos=("CC_2002",))
def convocacao_legitimidade(ctx: ContextoValidacao) -> Iterable[Achado]:
    convocante = ctx.dado("convocado_por")
    if not convocante:
        yield Achado(
            codigo="CONVOCANTE_NAO_INFORMADO",
            severidade=Semaforo.PENDENCIA,
            titulo="DADO NÃO INFORMADO: quem convocou",
            mensagem="Informe quem convocou a assembleia. A legitimidade do convocante é "
                     "verificada contra o estatuto e contra a garantia legal de convocação "
                     "por 1/5 dos associados.",
            fundamentos=_fund_legal(ctx, "CC_2002", "art. 60"),
            campo="convocado_por",
        )
        return

    p = ctx.param("CONVOCACAO_LEGITIMADOS")
    if not p.utilizavel:
        return
    legitimados = p.valor if isinstance(p.valor, (list, tuple)) else [p.valor]
    normalizados = [str(x).strip().lower() for x in legitimados]
    if str(convocante).strip().lower() not in normalizados:
        yield Achado(
            codigo="CONVOCANTE_SEM_PREVISAO",
            severidade=Semaforo.PENDENCIA,
            titulo="Convocante fora da lista estatutária",
            mensagem=f"“{convocante}” não consta entre os legitimados cadastrados "
                     f"({', '.join(map(str, legitimados))}). Confirme a previsão estatutária "
                     f"ou se a convocação se deu pela via do art. 60 do Código Civil.",
            fundamentos=([p.fundamento] if p.fundamento else [])
                        + _fund_legal(ctx, "CC_2002", "art. 60"),
            campo="convocado_por",
        )


@check("COMPETENCIA_ORGAO", "Competência e convocação específica",
       eventos=EVENTOS_COMPETENCIA_PRIVATIVA, fundamentos=("CC_2002",))
def competencia_orgao(ctx: ContextoValidacao) -> Iterable[Achado]:
    fundamentos = _fund_legal(ctx, "CC_2002", "art. 59")
    ordem_do_dia = ctx.dado("ordem_do_dia") or []
    if not ordem_do_dia:
        yield Achado(
            codigo="ORDEM_DO_DIA_AUSENTE",
            severidade=Semaforo.PENDENCIA,
            titulo="Ordem do dia não informada",
            mensagem="Destituição de administradores e alteração do estatuto são de competência "
                     "privativa da assembleia geral, em reunião especialmente convocada para "
                     "esse fim. A matéria precisa constar expressamente da ordem do dia do "
                     "edital.",
            fundamentos=fundamentos,
            campo="ordem_do_dia",
        )
        return

    termos = _TERMOS_ORDEM_DO_DIA.get(ctx.tipo_evento, ())
    texto = " ".join(str(i) for i in ordem_do_dia).lower()
    if termos and not any(t in texto for t in termos):
        yield Achado(
            codigo="MATERIA_FORA_DA_ORDEM_DO_DIA",
            severidade=Semaforo.BLOQUEADO,
            titulo="Matéria não consta da ordem do dia",
            mensagem="A ordem do dia informada não menciona a matéria deste ato. Deliberação "
                     "sobre assunto não constante da convocação é vício recorrente de "
                     "anulação e de exigência registral.",
            fundamentos=fundamentos,
            campo="ordem_do_dia",
            dados={"ordem_do_dia": ordem_do_dia},
        )


# --------------------------------------------------------------- Quórum


# Palavras que precisam aparecer na ordem do dia para que a matéria esteja
# efetivamente convocada. Deliberar sobre assunto ausente do edital é vício
# recorrente de anulação.
_TERMOS_ORDEM_DO_DIA: dict[str, tuple[str, ...]] = {
    TipoEvento.REFORMA_ESTATUTARIA.value: ("estatut", "reforma"),
    TipoEvento.ALTERACAO_FINALIDADE.value: ("finalidade", "estatut"),
    TipoEvento.ALTERACAO_DENOMINACAO.value: ("denomina", "nome", "estatut"),
    TipoEvento.ALTERACAO_ORGAOS.value: ("órgão", "orgao", "estatut"),
    TipoEvento.ALTERACAO_MANDATO.value: ("mandato", "estatut"),
    TipoEvento.ALTERACAO_QUORUM.value: ("quórum", "quorum", "estatut"),
    TipoEvento.DESTITUICAO.value: ("destitui",),
    TipoEvento.DISSOLUCAO.value: ("dissolu", "extin"),
}


@check("QUORUM_INSTALACAO", "Quórum de instalação", eventos=EVENTOS_ASSEMBLEARES)
def quorum_instalacao(ctx: ContextoValidacao) -> Iterable[Achado]:
    presentes = ctx.dado("total_presentes")
    if presentes is None:
        return

    convocacao = str(ctx.dado("convocacao") or "PRIMEIRA").upper()
    chave = (
        "QUORUM_INSTALACAO_SEGUNDA" if convocacao.startswith("SEG") else "QUORUM_INSTALACAO_PRIMEIRA"
    )
    p = ctx.param(chave)
    if not p.utilizavel:
        return

    exigencia = interpretar_quorum(p.valor)
    if exigencia is None:
        yield Achado(
            codigo=f"QUORUM_NAO_INTERPRETAVEL::{chave}",
            severidade=Semaforo.PENDENCIA,
            titulo="VALIDAÇÃO NECESSÁRIA: quórum de instalação",
            mensagem=f"O sistema não conseguiu interpretar com segurança a expressão de quórum "
                     f"cadastrada (“{p.valor}”). Confirme o número mínimo de presentes.",
            fundamentos=[p.fundamento] if p.fundamento else [],
            campo=chave,
        )
        return

    base = ctx.associados_aptos if exigencia.base is BaseQuorum.APTOS else int(presentes)
    if exigencia.base is BaseQuorum.APTOS and not ctx.associados_aptos:
        yield Achado(
            codigo="QUORUM_SEM_BASE_DE_CALCULO",
            severidade=Semaforo.PENDENCIA,
            titulo="Base de cálculo do quórum indisponível",
            mensagem="O quórum é calculado sobre o total de associados aptos, e não há "
                     "associados cadastrados com direito a voto.",
            campo="associados",
            sugestao="Cadastre o quadro associativo em Associados.",
        )
        return

    minimo = exigencia.minimo(base)
    if int(presentes) < minimo:
        yield Achado(
            codigo="QUORUM_INSTALACAO_INSUFICIENTE",
            severidade=Semaforo.BLOQUEADO,
            titulo="Quórum de instalação não atingido",
            mensagem=f"Em {convocacao.lower()} convocação o estatuto exige "
                     f"{exigencia.descricao(base)} e foram informados {presentes} presentes "
                     f"(mínimo: {minimo}).",
            fundamentos=[p.fundamento] if p.fundamento else [],
            campo="total_presentes",
            dados={"minimo": minimo, "presentes": int(presentes), "base": base},
        )
    else:
        yield Achado(
            codigo="QUORUM_INSTALACAO_OK",
            severidade=Semaforo.APTO,
            titulo="Quórum de instalação compatível com o estatuto",
            mensagem=f"{presentes} presentes para um mínimo de {minimo} "
                     f"({exigencia.descricao(base)}).",
            fundamentos=[p.fundamento] if p.fundamento else [],
        )


@check("QUORUM_DELIBERACAO", "Quórum de aprovação por matéria", eventos=EVENTOS_ASSEMBLEARES)
def quorum_deliberacao(ctx: ContextoValidacao) -> Iterable[Achado]:
    votos = ctx.dado("votos_favor")
    if votos is None:
        return

    chave = MATRIZ[ctx.tipo_evento].chave_quorum if ctx.tipo_evento in MATRIZ else None
    if chave is None:
        return

    p = ctx.param(chave)
    if not p.utilizavel:
        return
    exigencia = interpretar_quorum(p.valor)
    if exigencia is None:
        return

    presentes = int(ctx.dado("total_presentes") or 0)
    base = ctx.associados_aptos if exigencia.base is BaseQuorum.APTOS else presentes
    if not base:
        return
    minimo = exigencia.minimo(base)
    if int(votos) < minimo:
        yield Achado(
            codigo="QUORUM_DELIBERACAO_INSUFICIENTE",
            severidade=Semaforo.BLOQUEADO,
            titulo="Quórum de aprovação não atingido",
            mensagem=f"A matéria exige {exigencia.descricao(base)} — mínimo de {minimo} votos — "
                     f"e foram informados {votos} votos favoráveis.",
            fundamentos=([p.fundamento] if p.fundamento else [])
                        + (_fund_legal(ctx, "CC_2002", "art. 59")
                           if chave in ("QUORUM_REFORMA_ESTATUTARIA", "QUORUM_DESTITUICAO")
                           else []),
            campo="votos_favor",
            dados={"minimo": minimo, "votos": int(votos), "base": base},
        )


@check("EXIGE_REFORMA_ESTATUTARIA", "A alteração exige reforma do estatuto?",
       eventos=(TipoEvento.ALTERACAO_ENDERECO.value,), fundamentos=("CC_2002",))
def exige_reforma_estatutaria(ctx: ContextoValidacao) -> Iterable[Achado]:
    """§39 — 'essa alteração exige reforma estatutária?'

    Para a maioria dos atos a matriz responde sozinha. O endereço é o caso em
    que depende do texto do estatuto: se ele fixa o endereço completo, mudar de
    rua já é reforma; se fixa apenas o município, a mudança dentro dele se
    resolve por averbação. Quem sabe isso é quem leu o estatuto — por isso a
    pergunta existe, e por isso ela muda o quórum exigido.
    """
    consta = ctx.dado("consta_do_estatuto")
    endereco_novo = ctx.dado("endereco_novo") or ""
    municipio_mudou = bool(
        ctx.entidade.municipio
        and endereco_novo
        and ctx.entidade.municipio.lower() not in str(endereco_novo).lower()
    )

    if consta is None:
        yield Achado(
            codigo="ENDERECO_NO_ESTATUTO_NAO_INFORMADO",
            severidade=Semaforo.PENDENCIA,
            titulo="VALIDAÇÃO NECESSÁRIA: o endereço consta do estatuto?",
            mensagem="Se o estatuto traz o endereço completo da sede, a mudança é "
                     "reforma estatutária, com o quórum e a convocação próprios. Se "
                     "traz apenas o município, resolve-se por averbação.",
            fundamentos=_fund_legal(ctx, "CC_2002", "art. 54"),
            campo="consta_do_estatuto",
        )
        return

    if consta in (True, "true", "SIM", 1):
        p = ctx.param("QUORUM_REFORMA_ESTATUTARIA")
        yield Achado(
            codigo="ALTERACAO_ENDERECO_EXIGE_REFORMA",
            severidade=Semaforo.PENDENCIA,
            titulo="Esta alteração é reforma estatutária",
            mensagem="O endereço consta do estatuto, então a mudança altera o próprio "
                     "estatuto: exige assembleia especialmente convocada para esse fim e "
                     "o quórum de reforma"
                     + (f" ({p.valor})." if p.utilizavel else ", que não está cadastrado."),
            fundamentos=([p.fundamento] if p.fundamento else [])
                        + _fund_legal(ctx, "CC_2002", "art. 59"),
            sugestao="Registre o ato como Reforma Estatutária, e não como simples "
                     "alteração de endereço.",
        )

    if municipio_mudou:
        yield Achado(
            codigo="MUDANCA_DE_MUNICIPIO",
            severidade=Semaforo.PENDENCIA,
            titulo="A sede muda de município",
            mensagem="Mudança de município altera a sede prevista no estatuto e pode "
                     "alterar o RCPJ competente para os próximos atos.",
            fundamentos=_fund_legal(ctx, "LRP_1973", "art. 114"),
            sugestao="Confirme qual cartório passa a ser competente e atualize o "
                     "cadastro da entidade.",
        )


# --------------------------------------------------------- Inconsistências


@check("DIVERGENCIA_DIRIGENTE", "Dirigente informado x cadastro")
def divergencia_dirigente(ctx: ContextoValidacao) -> Iterable[Achado]:
    informado = ctx.dado("presidente_mesa") or ctx.dado("presidente")
    if not informado:
        return
    mandato = ctx.mandato_vigente("DIRETORIA")
    if mandato is None:
        return
    presidente = mandato.ocupante("PRESIDENTE")
    if presidente is None:
        return
    if str(informado).strip().lower() != presidente.nome.strip().lower():
        yield Achado(
            codigo="DIVERGENCIA_CADASTRAL_PRESIDENTE",
            severidade=Semaforo.PENDENCIA,
            titulo="DIVERGÊNCIA CADASTRAL: presidente",
            mensagem=f"O nome informado no ato (“{informado}”) não corresponde ao presidente "
                     f"cadastrado para a gestão vigente (“{presidente.nome}”).",
            campo="presidente_mesa",
            sugestao="Se houve substituição, registre o ato correspondente antes de gerar "
                     "os documentos. Se foi apenas quem presidiu a mesa, confirme no campo "
                     "próprio.",
            dados={"informado": informado, "cadastrado": presidente.nome},
        )


@check("ELEITOS_INFORMADOS", "Chapa eleita informada",
       eventos=(TipoEvento.ELEICAO_DIRETORIA.value, TipoEvento.REELEICAO_DIRETORIA.value,
                TipoEvento.POSSE_DIRETORIA.value))
def eleitos_informados(ctx: ContextoValidacao) -> Iterable[Achado]:
    eleitos = ctx.dado("eleitos") or []
    if not eleitos:
        yield Achado(
            codigo="ELEITOS_NAO_INFORMADOS",
            severidade=Semaforo.BLOQUEADO,
            titulo="DADO NÃO INFORMADO: chapa eleita",
            mensagem="Informe quem foi eleito e para qual cargo. Sem isso não é possível "
                     "gerar ata, termos de posse nem atualizar o quadro diretivo.",
            campo="eleitos",
        )
        return

    sem_cargo = [e for e in eleitos if not e.get("cargo")]
    if sem_cargo:
        yield Achado(
            codigo="ELEITO_SEM_CARGO",
            severidade=Semaforo.PENDENCIA,
            titulo="Eleito sem cargo definido",
            mensagem=f"{len(sem_cargo)} pessoa(s) eleita(s) sem cargo informado.",
            campo="eleitos",
        )

    inicio, fim = ctx.dado("mandato_inicio"), ctx.dado("mandato_fim")
    p = ctx.param("MANDATO_DURACAO_MESES")
    if inicio and fim and p.utilizavel:
        di = dt.date.fromisoformat(inicio) if isinstance(inicio, str) else inicio
        df = dt.date.fromisoformat(fim) if isinstance(fim, str) else fim
        meses = round((df - di).days / 30.44)
        esperado = int(p.valor)
        if abs(meses - esperado) > 1:
            yield Achado(
                codigo="MANDATO_DURACAO_DIVERGENTE",
                severidade=Semaforo.PENDENCIA,
                titulo="Duração do mandato diverge do estatuto",
                mensagem=f"O período informado ({di:%d/%m/%Y} a {df:%d/%m/%Y}) equivale a cerca "
                         f"de {meses} meses, e o estatuto prevê {esperado}.",
                fundamentos=[p.fundamento] if p.fundamento else [],
                campo="mandato_fim",
            )


# ------------------------------------------------------- Prestação de contas


@check("DOCUMENTOS_PRESTACAO_CONTAS", "Documentos da prestação de contas",
       eventos=(TipoEvento.APROVACAO_CONTAS.value, TipoEvento.PRESTACAO_CONTAS.value),
       grupo="DOCUMENTAL", fundamentos=("CC_2002",))
def documentos_prestacao_contas(ctx: ContextoValidacao) -> Iterable[Achado]:
    if not ctx.dado("exercicio"):
        yield Achado(
            codigo="EXERCICIO_NAO_INFORMADO",
            severidade=Semaforo.PENDENCIA,
            titulo="DADO NÃO INFORMADO: exercício",
            mensagem="Informe a qual exercício se referem as contas submetidas.",
            campo="exercicio",
        )
    if "DEMONSTRACOES_CONTABEIS" not in ctx.documentos_anexados:
        yield Achado(
            codigo="DEMONSTRACOES_NAO_ANEXADAS",
            severidade=Semaforo.PENDENCIA,
            titulo="Demonstrações contábeis não anexadas",
            mensagem="As demonstrações do exercício não foram anexadas ao ato. O estatuto deve "
                     "dispor sobre a forma de aprovação das contas.",
            fundamentos=_fund_legal(ctx, "CC_2002", "art. 54"),
            sugestao="Anexe as demonstrações em Documentos → Contábeis.",
        )

    p = ctx.param("CONSELHO_FISCAL_PARECER_OBRIGATORIO")
    parecer_anexado = "PARECER_CONSELHO_FISCAL" in ctx.documentos_anexados
    if p.utilizavel and p.valor in (True, "true", "SIM", 1) and not parecer_anexado:
        yield Achado(
            codigo="PARECER_CONSELHO_FISCAL_AUSENTE",
            severidade=Semaforo.PENDENCIA,
            titulo="Parecer do Conselho Fiscal não anexado",
            mensagem="O estatuto cadastrado exige parecer do Conselho Fiscal para a aprovação "
                     "das contas, e o documento não foi anexado.",
            fundamentos=[p.fundamento] if p.fundamento else [],
        )


# ------------------------------------------------------------------- RCPJ


@check("RCPJ_COMPETENTE", "RCPJ competente identificado", grupo="REGISTRAL")
def rcpj_competente(ctx: ContextoValidacao) -> Iterable[Achado]:
    if ctx.rcpj is None:
        yield Achado(
            codigo="RCPJ_NAO_DEFINIDO",
            severidade=Semaforo.PENDENCIA,
            titulo="RCPJ competente não definido",
            mensagem="Sem o Registro Civil de Pessoas Jurídicas competente o sistema não tem "
                     "como montar o checklist de protocolo nem conferir exigências locais.",
            fundamentos=_fund_legal(ctx, "LRP_1973", "art. 114"),
            sugestao="Cadastre o RCPJ competente em Configurações → RCPJ e vincule à entidade.",
        )
        return

    if ctx.rcpj.regras_desatualizadas:
        ultima = (
            f"{ctx.rcpj.data_ultima_verificacao:%d/%m/%Y}"
            if ctx.rcpj.data_ultima_verificacao
            else "nunca"
        )
        yield Achado(
            codigo="RCPJ_REGRAS_DESATUALIZADAS",
            severidade=Semaforo.PENDENCIA,
            titulo="VALIDAÇÃO NECESSÁRIA: exigências do RCPJ podem estar desatualizadas",
            mensagem=f"As exigências cadastradas para o {ctx.rcpj.nome} foram conferidas pela "
                     f"última vez em {ultima}. Cartórios mudam exigências sem aviso e o sistema "
                     f"não presume o que não foi conferido.",
            sugestao="Reconfira as exigências junto ao cartório e atualize o cadastro.",
        )

    regra = ctx.rcpj.regra_evento
    if regra is None:
        yield Achado(
            codigo="RCPJ_SEM_REGRA_PARA_O_ATO",
            severidade=Semaforo.PENDENCIA,
            titulo="Exigências do RCPJ não cadastradas para este ato",
            mensagem=f"Não há exigências cadastradas no {ctx.rcpj.nome} para o ato "
                     f"“{ctx.tipo_evento}”. O checklist sairá apenas com os documentos que o "
                     f"sistema sabe serem produzidos pelo próprio ato.",
        )
        return

    faltantes = [
        d for d in regra.documentos_exigidos
        if d.get("obrigatorio", True) and d.get("codigo") not in ctx.documentos_anexados
    ]
    if faltantes:
        yield Achado(
            codigo="DOCUMENTOS_RCPJ_FALTANTES",
            severidade=Semaforo.PENDENCIA,
            titulo="Documentos exigidos pelo RCPJ ainda não reunidos",
            mensagem="Faltam: " + ", ".join(d.get("descricao", d.get("codigo", "?")) for d in faltantes),
            dados={"faltantes": [d.get("codigo") for d in faltantes]},
        )

    if regra.exige_visto_advogado is None and ctx.rcpj.exige_visto_advogado is None:
        yield Achado(
            codigo="VISTO_ADVOGADO_NAO_CONFERIDO",
            severidade=Semaforo.PENDENCIA,
            titulo="VALIDAÇÃO NECESSÁRIA: visto de advogado",
            mensagem="Não está cadastrado se este cartório exige visto de advogado para este "
                     "ato. A exigência varia conforme o ato e a praça.",
            fundamentos=_fund_legal(ctx, "EOAB_1994", "art. 1º, §2º"),
        )
    if regra.exige_reconhecimento_firma is None and ctx.rcpj.exige_reconhecimento_firma is None:
        yield Achado(
            codigo="RECONHECIMENTO_FIRMA_NAO_CONFERIDO",
            severidade=Semaforo.PENDENCIA,
            titulo="VALIDAÇÃO NECESSÁRIA: reconhecimento de firma",
            mensagem="Não está cadastrado se este cartório exige reconhecimento de firma nas "
                     "assinaturas deste ato.",
        )


# ------------------------------------------------------- Atualização normativa


@check("IMPACTO_NORMATIVO", "Mudança normativa pendente de tratamento", grupo="NORMATIVO")
def impacto_normativo(ctx: ContextoValidacao) -> Iterable[Achado]:
    for impacto in ctx.impactos_normativos:
        severidade = {
            "BLOQUEANTE": Semaforo.BLOQUEADO,
            "REVISAO_OBRIGATORIA": Semaforo.BLOQUEADO,
            "REVISAO_RECOMENDADA": Semaforo.PENDENCIA,
            "INFORMATIVA": Semaforo.PENDENCIA,
        }.get(impacto.severidade, Semaforo.PENDENCIA)
        yield Achado(
            codigo=f"NORMA_ALTERADA::{impacto.alvo_ref}",
            severidade=severidade,
            titulo="Norma alterada afeta este ato",
            mensagem=impacto.descricao,
            fundamentos=[
                Fundamento(origem=OrigemDado.LEI, referencia=impacto.norma or "Norma alterada")
            ] if impacto.norma else [],
            dados={"alvo": impacto.alvo_ref, "alvo_tipo": impacto.alvo_tipo},
            sugestao="Trate o impacto na Central de Fontes antes de concluir o ato.",
        )
