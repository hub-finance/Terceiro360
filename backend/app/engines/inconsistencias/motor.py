"""MOTOR DE INCONSISTÊNCIAS CADASTRAIS (§24, §43).

Enquanto o motor de validação olha para *um ato*, este varre o *cadastro* da
entidade procurando o que já está errado antes de qualquer ato começar. É o que
alimenta a Central de Pendências e o Dashboard.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.core.enums import Prioridade, Semaforo


@dataclass
class Inconsistencia:
    codigo: str
    severidade: Semaforo
    titulo: str
    descricao: str
    prioridade: Prioridade = Prioridade.MEDIA
    referencia: str | None = None
    sugestao: str | None = None

    def to_dict(self) -> dict:
        return {
            "codigo": self.codigo, "severidade": self.severidade.value,
            "icone": self.severidade.icone, "titulo": self.titulo,
            "descricao": self.descricao, "prioridade": self.prioridade.value,
            "referencia": self.referencia, "sugestao": self.sugestao,
        }


@dataclass
class RetratoCadastral:
    """O que o motor precisa saber sobre a entidade para varrer o cadastro."""

    entidade_id: str
    razao_social: str
    cnpj: str | None = None
    municipio: str | None = None
    uf: str | None = None
    rcpj_definido: bool = False
    rcpj_regras_desatualizadas: bool = False
    tem_estatuto_vigente: bool = False
    total_parametros: int = 0
    parametros_confirmados: int = 0
    mandato_vigente: bool = False
    mandato_designacao: str | None = None
    mandato_data_fim: dt.date | None = None
    cargos_obrigatorios_vagos: list[str] = field(default_factory=list)
    pessoas_sem_cpf: list[str] = field(default_factory=list)
    associados_ativos: int = 0
    associados_aptos: int = 0
    certidoes_vencidas: list[str] = field(default_factory=list)
    protocolos_em_exigencia: int = 0
    documentos_aguardando_assinatura: int = 0
    exercicios_sem_aprovacao: list[int] = field(default_factory=list)
    impactos_normativos_abertos: int = 0


def varrer(r: RetratoCadastral, hoje: dt.date | None = None) -> list[Inconsistencia]:
    hoje = hoje or dt.date.today()
    achados: list[Inconsistencia] = []

    def add(**kw):
        achados.append(Inconsistencia(**kw))

    if not r.cnpj:
        add(codigo="ENTIDADE_SEM_CNPJ", severidade=Semaforo.PENDENCIA,
            titulo="CNPJ não cadastrado", prioridade=Prioridade.MEDIA,
            descricao="Sem CNPJ os documentos saem com DADO NÃO INFORMADO nesse campo.",
            sugestao="Complete o cadastro da entidade.")

    if not r.tem_estatuto_vigente:
        add(codigo="ESTATUTO_AUSENTE", severidade=Semaforo.BLOQUEADO,
            titulo="Estatuto atualizado não cadastrado", prioridade=Prioridade.URGENTE,
            descricao="Nenhuma versão vigente do estatuto está cadastrada. Nenhum ato pode ser "
                      "validado com segurança nessa condição.",
            sugestao="Cadastre ou importe o estatuto vigente.")
    elif r.total_parametros and r.parametros_confirmados < r.total_parametros:
        faltam = r.total_parametros - r.parametros_confirmados
        add(codigo="PARAMETROS_NAO_CONFIRMADOS", severidade=Semaforo.PENDENCIA,
            titulo=f"{faltam} regra(s) do estatuto sem confirmação",
            prioridade=Prioridade.ALTA,
            descricao="Parâmetros extraídos do estatuto ainda não foram confirmados por um "
                      "responsável e, por isso, não são usados nas validações.",
            sugestao="Revise em Estatuto → Parâmetros.")

    if not r.mandato_vigente:
        add(codigo="MANDATO_VENCIDO", severidade=Semaforo.BLOQUEADO,
            titulo="Diretoria sem mandato vigente", prioridade=Prioridade.URGENTE,
            descricao=(f"O mandato {r.mandato_designacao} encerrou-se em "
                       f"{r.mandato_data_fim:%d/%m/%Y}."
                       if r.mandato_data_fim else
                       "Não há mandato vigente cadastrado para a diretoria."),
            referencia=r.mandato_designacao,
            sugestao="Registre a eleição que renovou a gestão ou convoque a assembleia eleitoral.")
    elif r.mandato_data_fim:
        dias = (r.mandato_data_fim - hoje).days
        if dias <= 90:
            add(codigo="MANDATO_A_VENCER", severidade=Semaforo.PENDENCIA,
                titulo=f"Mandato encerra em {dias} dias",
                prioridade=Prioridade.ALTA if dias <= 30 else Prioridade.MEDIA,
                descricao=f"O mandato {r.mandato_designacao} termina em "
                          f"{r.mandato_data_fim:%d/%m/%Y}.",
                sugestao="Programe a assembleia eleitoral respeitando o prazo de convocação.")

    if r.cargos_obrigatorios_vagos:
        add(codigo="CARGOS_VAGOS", severidade=Semaforo.PENDENCIA,
            titulo="Cargos obrigatórios vagos", prioridade=Prioridade.ALTA,
            descricao="Estão vagos: " + ", ".join(r.cargos_obrigatorios_vagos) + ".",
            sugestao="Registre a substituição ou a eleição complementar.")

    if r.pessoas_sem_cpf:
        add(codigo="DIRIGENTES_SEM_CPF", severidade=Semaforo.PENDENCIA,
            titulo="Dirigentes sem CPF cadastrado", prioridade=Prioridade.MEDIA,
            descricao="Sem CPF a qualificação nos termos e requerimentos fica incompleta: "
                      + ", ".join(r.pessoas_sem_cpf[:5])
                      + ("…" if len(r.pessoas_sem_cpf) > 5 else ""))

    if r.associados_ativos and not r.associados_aptos:
        add(codigo="SEM_ASSOCIADOS_APTOS", severidade=Semaforo.PENDENCIA,
            titulo="Nenhum associado apto a votar", prioridade=Prioridade.ALTA,
            descricao=f"Há {r.associados_ativos} associados ativos, mas nenhum com direito a "
                      f"voto reconhecido. O quórum não tem base de cálculo.")

    if not r.rcpj_definido:
        add(codigo="RCPJ_NAO_DEFINIDO", severidade=Semaforo.PENDENCIA,
            titulo="RCPJ competente não vinculado", prioridade=Prioridade.MEDIA,
            descricao="Sem o cartório competente o checklist de protocolo fica incompleto.")
    elif r.rcpj_regras_desatualizadas:
        add(codigo="RCPJ_DESATUALIZADO", severidade=Semaforo.PENDENCIA,
            titulo="Exigências do cartório fora do prazo de reconferência",
            prioridade=Prioridade.MEDIA,
            descricao="As regras cadastradas para o RCPJ competente não são conferidas há mais "
                      "tempo do que o configurado.")

    for certidao in r.certidoes_vencidas:
        add(codigo=f"CERTIDAO_VENCIDA::{certidao}", severidade=Semaforo.PENDENCIA,
            titulo=f"Certidão vencida: {certidao}", prioridade=Prioridade.ALTA,
            descricao="Documento fora da validade pode inviabilizar protocolos e parcerias.")

    if r.protocolos_em_exigencia:
        add(codigo="PROTOCOLOS_EM_EXIGENCIA", severidade=Semaforo.PENDENCIA,
            titulo=f"{r.protocolos_em_exigencia} protocolo(s) em exigência",
            prioridade=Prioridade.URGENTE,
            descricao="Há atos protocolados aguardando cumprimento de exigência no cartório.")

    if r.documentos_aguardando_assinatura:
        add(codigo="DOCUMENTOS_SEM_ASSINATURA", severidade=Semaforo.PENDENCIA,
            titulo=f"{r.documentos_aguardando_assinatura} documento(s) aguardando assinatura",
            prioridade=Prioridade.MEDIA,
            descricao="Documentos gerados e aprovados que ainda não foram assinados.")

    for ano in r.exercicios_sem_aprovacao:
        add(codigo=f"CONTAS_NAO_APROVADAS::{ano}", severidade=Semaforo.PENDENCIA,
            titulo=f"Contas de {ano} sem aprovação registrada", prioridade=Prioridade.ALTA,
            descricao="Não há assembleia registrada aprovando as contas desse exercício.")

    if r.impactos_normativos_abertos:
        add(codigo="IMPACTOS_NORMATIVOS", severidade=Semaforo.PENDENCIA,
            titulo=f"{r.impactos_normativos_abertos} impacto(s) normativo(s) sem tratamento",
            prioridade=Prioridade.ALTA,
            descricao="Mudanças na legislação publicadas na Central de Fontes atingem regras ou "
                      "modelos usados por esta entidade e ainda não foram revisadas.",
            sugestao="Trate os impactos na Central de Fontes → Atualizações.")

    ordem = {Prioridade.URGENTE: 0, Prioridade.ALTA: 1, Prioridade.MEDIA: 2, Prioridade.BAIXA: 3}
    achados.sort(key=lambda i: (ordem[i.prioridade], i.codigo))
    return achados
