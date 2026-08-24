"""Base normativa inicial da Central de Fontes Jurídicas (§4, §38).

REGRAS DESTE ARQUIVO
--------------------
1. Só entra norma que existe e pode ser conferida na URL oficial indicada.
2. O campo `sintese` é redação nossa, resumida — não é transcrição literal.
   O texto oficial é o que está na URL. Isso é sinalizado na interface.
3. Nenhuma dessas versões nasce curada: elas entram como base de trabalho e
   precisam de conferência de um responsável habilitado antes de serem tratadas
   como conferidas (§46). O motor cita e informa `curado: false` até lá.
4. Nada aqui inventa exigência de cartório. Exigência registral vem do módulo
   RCPJ, alimentada manualmente (§22).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DispositivoSeed:
    identificacao: str
    sintese: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class FonteSeed:
    chave: str
    identificacao: str
    apelido: str
    tipo: str
    jurisdicao: str
    url_oficial: str
    ementa: str
    vigente_desde: dt.date
    orgao_emissor: str = "Congresso Nacional"
    dispositivos: tuple[DispositivoSeed, ...] = field(default_factory=tuple)


FONTES: tuple[FonteSeed, ...] = (
    FonteSeed(
        chave="CF_1988",
        identificacao="Constituição da República Federativa do Brasil de 1988",
        apelido="Constituição Federal",
        tipo="LEI",
        jurisdicao="FEDERAL",
        orgao_emissor="Assembleia Nacional Constituinte",
        url_oficial="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
        ementa="Ordem constitucional brasileira.",
        vigente_desde=dt.date(1988, 10, 5),
        dispositivos=(
            DispositivoSeed(
                "art. 5º, VI",
                "Síntese: é inviolável a liberdade de consciência e de crença, assegurado o "
                "livre exercício dos cultos religiosos e garantida, na forma da lei, a proteção "
                "aos locais de culto e a suas liturgias.",
                ("religiosa", "culto"),
            ),
            DispositivoSeed(
                "art. 5º, XVII a XXI",
                "Síntese: liberdade de associação para fins lícitos, vedada a de caráter "
                "paramilitar; a criação de associações independe de autorização, sendo vedada a "
                "interferência estatal em seu funcionamento; as associações só podem ser "
                "compulsoriamente dissolvidas ou ter suas atividades suspensas por decisão "
                "judicial; ninguém pode ser compelido a associar-se ou a permanecer associado.",
                ("associacao", "liberdade"),
            ),
            DispositivoSeed(
                "art. 150, VI, 'b' e 'c'",
                "Síntese: veda-se instituir impostos sobre templos de qualquer culto e sobre "
                "patrimônio, renda ou serviços de partidos políticos, entidades sindicais, "
                "instituições de educação e de assistência social sem fins lucrativos, atendidos "
                "os requisitos de lei.",
                ("imunidade", "templo", "assistencia"),
            ),
        ),
    ),
    FonteSeed(
        chave="CC_2002",
        identificacao="Lei nº 10.406, de 10 de janeiro de 2002",
        apelido="Código Civil",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm",
        ementa="Institui o Código Civil.",
        vigente_desde=dt.date(2003, 1, 11),
        dispositivos=(
            DispositivoSeed(
                "art. 44",
                "Síntese: são pessoas jurídicas de direito privado, entre outras, as associações, "
                "as fundações e as organizações religiosas. O §1º assegura às organizações "
                "religiosas liberdade de criação, organização, estruturação interna e "
                "funcionamento, vedado ao poder público negar-lhes reconhecimento ou registro "
                "dos atos constitutivos.",
                ("tipo_entidade", "religiosa"),
            ),
            DispositivoSeed(
                "art. 45",
                "Síntese: a existência legal das pessoas jurídicas de direito privado começa com "
                "a inscrição do ato constitutivo no respectivo registro, averbando-se no registro "
                "todas as alterações por que passar o ato constitutivo.",
                ("registro", "averbacao", "constituicao"),
            ),
            DispositivoSeed(
                "art. 46",
                "Síntese: o registro declarará denominação, fins, sede, tempo de duração e fundo "
                "social; nome e individualização dos fundadores e diretores; modo de administração "
                "e representação; se o ato constitutivo é reformável quanto à administração e de "
                "que modo; se os membros respondem subsidiariamente pelas obrigações sociais; e as "
                "condições de extinção e o destino do patrimônio.",
                ("registro", "representacao", "estatuto"),
            ),
            DispositivoSeed(
                "art. 54",
                "Síntese: sob pena de nulidade, o estatuto das associações deve conter "
                "denominação, fins e sede; requisitos de admissão, demissão e exclusão de "
                "associados; direitos e deveres dos associados; fontes de recursos; modo de "
                "constituição e funcionamento dos órgãos deliberativos; condições para alteração "
                "estatutária e para a dissolução; e a forma de gestão administrativa e de "
                "aprovação das respectivas contas.",
                ("estatuto", "associados", "contas", "dissolucao"),
            ),
            DispositivoSeed(
                "art. 59",
                "Síntese: compete privativamente à assembleia geral destituir os administradores "
                "e alterar o estatuto. O parágrafo único exige, para essas deliberações, "
                "assembleia especialmente convocada para esse fim, cujo quórum será o estabelecido "
                "no estatuto, bem como os critérios de eleição dos administradores (redação dada "
                "pela Lei nº 11.127/2005).",
                ("quorum", "destituicao", "reforma_estatutaria", "competencia"),
            ),
            DispositivoSeed(
                "art. 60",
                "Síntese: a convocação dos órgãos deliberativos far-se-á na forma do estatuto, "
                "garantido a 1/5 (um quinto) dos associados o direito de promovê-la.",
                ("convocacao", "prazo", "legitimidade"),
            ),
            DispositivoSeed(
                "art. 61",
                "Síntese: dissolvida a associação, o remanescente do seu patrimônio líquido, "
                "depois de deduzidas as quotas ou frações ideais eventualmente restituíveis, será "
                "destinado à entidade de fins não econômicos designada no estatuto ou, sendo "
                "omisso, por deliberação dos associados, a instituição municipal, estadual ou "
                "federal de fins idênticos ou semelhantes.",
                ("dissolucao", "patrimonio"),
            ),
        ),
    ),
    FonteSeed(
        chave="LRP_1973",
        identificacao="Lei nº 6.015, de 31 de dezembro de 1973",
        apelido="Lei de Registros Públicos",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/leis/l6015compilada.htm",
        ementa="Dispõe sobre os registros públicos.",
        vigente_desde=dt.date(1976, 1, 1),
        dispositivos=(
            DispositivoSeed(
                "art. 114",
                "Síntese: no Registro Civil de Pessoas Jurídicas serão inscritos os contratos, "
                "atos constitutivos, estatutos ou compromissos das sociedades civis, religiosas, "
                "pias, morais, científicas ou literárias, das fundações e das associações de "
                "utilidade pública, entre outros atos indicados no dispositivo.",
                ("rcpj", "registro"),
            ),
            DispositivoSeed(
                "art. 120",
                "Síntese: o registro do ato constitutivo, estatuto ou compromisso será requerido "
                "com a declaração dos elementos ali listados — denominação, fins, sede, tempo de "
                "duração, nome e qualificação dos fundadores e diretores, modo de representação, "
                "condições de extinção e destino do patrimônio, entre outros.",
                ("rcpj", "requerimento", "protocolo"),
            ),
            DispositivoSeed(
                "art. 121",
                "Síntese: para o registro serão apresentadas vias do estatuto, compromisso ou "
                "contrato, mediante petição do representante legal, lançando o oficial a certidão "
                "de registro com número de ordem, livro e folha.",
                ("rcpj", "protocolo", "vias"),
            ),
        ),
    ),
    FonteSeed(
        chave="MROSC_2014",
        identificacao="Lei nº 13.019, de 31 de julho de 2014",
        apelido="Marco Regulatório das Organizações da Sociedade Civil",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l13019.htm",
        ementa="Estabelece o regime jurídico das parcerias entre a administração pública e as "
               "organizações da sociedade civil.",
        vigente_desde=dt.date(2016, 1, 23),
        dispositivos=(
            DispositivoSeed(
                "art. 2º, I",
                "Síntese: define organização da sociedade civil, abrangendo entidade privada sem "
                "fins lucrativos, sociedades cooperativas em hipóteses específicas e organizações "
                "religiosas que se dediquem a atividades ou projetos de interesse público.",
                ("osc", "definicao"),
            ),
            DispositivoSeed(
                "art. 33",
                "Síntese: relaciona os requisitos que a organização da sociedade civil deve "
                "preencher para celebrar parcerias, incluindo previsões estatutárias sobre "
                "objetivos, destinação do patrimônio em caso de dissolução e escrituração "
                "contábil conforme os princípios fundamentais de contabilidade e as normas "
                "brasileiras de contabilidade.",
                ("parceria", "estatuto", "requisitos", "contabil"),
            ),
        ),
    ),
    FonteSeed(
        chave="OSCIP_1999",
        identificacao="Lei nº 9.790, de 23 de março de 1999",
        apelido="Lei das OSCIP",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/leis/l9790.htm",
        ementa="Dispõe sobre a qualificação de pessoas jurídicas de direito privado, sem fins "
               "lucrativos, como Organizações da Sociedade Civil de Interesse Público.",
        vigente_desde=dt.date(1999, 3, 24),
        dispositivos=(
            DispositivoSeed(
                "art. 4º",
                "Síntese: exige que o estatuto disponha expressamente sobre observância dos "
                "princípios da legalidade, impessoalidade, moralidade, publicidade, economicidade "
                "e eficiência; adoção de práticas de gestão que coíbam a obtenção de vantagens "
                "pessoais; constituição de conselho fiscal ou órgão equivalente; destinação do "
                "patrimônio em caso de dissolução ou perda da qualificação; e prestação de contas.",
                ("oscip", "estatuto", "conselho_fiscal", "prestacao_contas"),
            ),
        ),
    ),
    FonteSeed(
        chave="LGPD_2018",
        identificacao="Lei nº 13.709, de 14 de agosto de 2018",
        apelido="Lei Geral de Proteção de Dados Pessoais",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
        ementa="Dispõe sobre o tratamento de dados pessoais.",
        vigente_desde=dt.date(2020, 9, 18),
        dispositivos=(
            DispositivoSeed(
                "art. 6º",
                "Síntese: disciplina os princípios do tratamento de dados — finalidade, adequação, "
                "necessidade, livre acesso, qualidade, transparência, segurança, prevenção, não "
                "discriminação e responsabilização.",
                ("lgpd", "principios", "minimizacao"),
            ),
            DispositivoSeed(
                "art. 7º",
                "Síntese: lista as hipóteses que autorizam o tratamento de dados pessoais, entre "
                "elas o consentimento, o cumprimento de obrigação legal ou regulatória, o exercício "
                "regular de direitos e o legítimo interesse.",
                ("lgpd", "base_legal"),
            ),
            DispositivoSeed(
                "art. 46",
                "Síntese: os agentes de tratamento devem adotar medidas de segurança, técnicas e "
                "administrativas aptas a proteger os dados pessoais de acessos não autorizados e "
                "de situações acidentais ou ilícitas.",
                ("lgpd", "seguranca"),
            ),
        ),
    ),
    FonteSeed(
        chave="EOAB_1994",
        identificacao="Lei nº 8.906, de 4 de julho de 1994",
        apelido="Estatuto da Advocacia e da OAB",
        tipo="LEI",
        jurisdicao="FEDERAL",
        url_oficial="https://www.planalto.gov.br/ccivil_03/leis/l8906.htm",
        ementa="Dispõe sobre o Estatuto da Advocacia e a Ordem dos Advogados do Brasil.",
        vigente_desde=dt.date(1994, 7, 5),
        dispositivos=(
            DispositivoSeed(
                "art. 1º, §2º",
                "Síntese: os atos e contratos constitutivos de pessoas jurídicas, sob pena de "
                "nulidade, só podem ser admitidos a registro nos órgãos competentes quando visados "
                "por advogado. A aplicação concreta a cada tipo de ato e de entidade deve ser "
                "conferida junto ao RCPJ competente antes do protocolo.",
                ("advogado", "visto", "registro"),
            ),
        ),
    ),
)

FONTES_POR_CHAVE = {f.chave: f for f in FONTES}
