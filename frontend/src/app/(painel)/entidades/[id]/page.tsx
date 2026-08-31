import Link from "next/link";

import {
  Aviso,
  Cartao,
  Etiqueta,
  Farol,
  Metrica,
  SeloPrioridade,
  SeloSemaforo,
  Vazio,
} from "@/componentes/base";
import { PainelScore } from "@/componentes/score";
import { chamarApi } from "@/lib/api";
import { dataBr, prazoRelativo, tituloDoAto } from "@/lib/formato";
import type { Dashboard } from "@/lib/tipos";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const painel = await chamarApi<Dashboard>(`/entidades/${id}/dashboard`);
  return { title: painel.entidade.razao_social };
}

export default async function PaginaPainel({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const painel = await chamarApi<Dashboard>(`/entidades/${id}/dashboard`);
  const { entidade, estatuto, diretoria, score, pendencias, prazos, atos_em_andamento } = painel;

  const bloqueios = pendencias.filter((p) => p.severidade === "BLOQUEADO");
  const proximo = prazos.find((p) => p.dias_restantes >= 0) ?? prazos[0];
  const parametrosPendentes = estatuto.parametros_totais - estatuto.parametros_confirmados;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <header className="mb-7">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="text-xl font-semibold tracking-tight">{entidade.razao_social}</h1>
          <Etiqueta>{entidade.tipo.replaceAll("_", " ").toLowerCase()}</Etiqueta>
          {entidade.situacao_cadastral && <Etiqueta tom="marca">{entidade.situacao_cadastral}</Etiqueta>}
        </div>
        <p className="mt-1 text-[0.875rem] text-[var(--color-tinta-3)]">
          {entidade.cnpj ?? "CNPJ não informado"}
          {entidade.municipio && ` · ${entidade.municipio}/${entidade.uf}`}
        </p>
      </header>

      {/* O que impede a entidade de operar vem antes de qualquer indicador. */}
      {bloqueios.length > 0 && (
        <div className="mb-6 space-y-2">
          {bloqueios.map((b) => (
            <Aviso key={b.codigo} tom="erro" titulo={b.titulo}>
              {b.descricao}
              {b.sugestao && (
                <span className="mt-1 block text-[var(--color-tinta-2)]">{b.sugestao}</span>
              )}
            </Aviso>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Cartao>
          <Metrica
            rotulo="Conformidade"
            valor={Math.round(score.pontuacao)}
            detalhe={score.classificacao}
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Mandato"
            valor={diretoria.vigente ? "Vigente" : "Vencido"}
            tom={diretoria.vigente ? undefined : "var(--color-bloqueado)"}
            detalhe={diretoria.gestao ?? "Sem gestão cadastrada"}
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Próximo prazo"
            valor={proximo ? prazoRelativo(proximo.dias_restantes) : "—"}
            detalhe={proximo?.descricao ?? "Nenhum prazo aberto"}
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Pendências"
            valor={pendencias.length}
            tom={bloqueios.length ? "var(--color-bloqueado)" : undefined}
            detalhe={bloqueios.length ? `${bloqueios.length} impeditiva(s)` : "Nenhuma impeditiva"}
          />
        </Cartao>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          <Cartao
            titulo="Diretoria"
            descricao={
              diretoria.gestao
                ? `${diretoria.gestao} · ${dataBr(diretoria.inicio)} a ${dataBr(diretoria.fim)}`
                : undefined
            }
            acao={
              <SeloSemaforo
                estado={diretoria.vigente ? "APTO" : "BLOQUEADO"}
                texto={diretoria.vigente ? "Mandato vigente" : "Mandato vencido"}
              />
            }
          >
            {diretoria.membros.length === 0 ? (
              <Vazio>Nenhum dirigente cadastrado na gestão vigente.</Vazio>
            ) : (
              <ul className="divide-y">
                {diretoria.membros.map((m) => (
                  <li key={m.nome + m.cargo} className="flex items-baseline justify-between gap-3 py-2 first:pt-0 last:pb-0">
                    <span className="text-[0.875rem]">{m.nome}</span>
                    <span className="shrink-0 text-[0.8125rem] text-[var(--color-tinta-3)]">
                      {m.cargo}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {diretoria.cargos_vagos.length > 0 && (
              <div className="mt-3">
                <Aviso tom="atencao">
                  Cargos obrigatórios vagos: {diretoria.cargos_vagos.join(", ")}.
                </Aviso>
              </div>
            )}
          </Cartao>

          <Cartao
            titulo="Prazos"
            descricao="Calculados a partir do estatuto e dos atos em curso"
            acao={
              <Link
                href={`/entidades/${id}/atos`}
                className="text-[0.8125rem] font-medium text-[var(--color-marca)] hover:underline"
              >
                Novo ato
              </Link>
            }
          >
            {prazos.length === 0 ? (
              <Vazio>Nenhum prazo em aberto.</Vazio>
            ) : (
              <ul className="divide-y">
                {prazos.slice(0, 6).map((p) => (
                  <li key={p.descricao + p.data_limite} className="py-2.5 first:pt-0 last:pb-0">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[0.875rem]">{p.descricao}</span>
                      <span
                        className="shrink-0 text-[0.8125rem] font-medium tabular-nums"
                        style={{
                          color:
                            p.dias_restantes < 0
                              ? "var(--color-bloqueado)"
                              : p.dias_restantes <= 30
                                ? "var(--color-pendencia)"
                                : "var(--color-tinta-2)",
                        }}
                      >
                        {prazoRelativo(p.dias_restantes)}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[0.75rem] text-[var(--color-tinta-3)]">
                      {dataBr(p.data_limite)} · {p.fundamento ?? `origem: ${p.origem.toLowerCase()}`}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>

          <Cartao titulo="Atos em andamento">
            {atos_em_andamento.length === 0 ? (
              <Vazio>Nenhum ato em curso.</Vazio>
            ) : (
              <ul className="divide-y">
                {atos_em_andamento.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={`/entidades/${id}/atos/${a.id}`}
                      className="flex items-center justify-between gap-3 py-2.5 hover:text-[var(--color-marca)]"
                    >
                      <span className="flex min-w-0 items-center gap-2.5">
                        {a.semaforo && <Farol estado={a.semaforo} tamanho={13} />}
                        <span className="truncate text-[0.875rem]">
                          {a.titulo ?? tituloDoAto(a.tipo)}
                        </span>
                      </span>
                      <span className="shrink-0 text-[0.75rem] uppercase tracking-wide text-[var(--color-tinta-3)]">
                        {a.status.replaceAll("_", " ").toLowerCase()}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>
        </div>

        <div className="space-y-4">
          <Cartao
            titulo="Estatuto"
            acao={
              <Link
                href={`/entidades/${id}/estatuto`}
                className="text-[0.8125rem] font-medium text-[var(--color-marca)] hover:underline"
              >
                Abrir
              </Link>
            }
          >
            {estatuto.versao === null ? (
              <Aviso tom="erro" titulo="Estatuto não cadastrado">
                Sem as regras do estatuto o sistema não valida quórum, prazo de
                convocação nem competência.
              </Aviso>
            ) : (
              <dl className="space-y-2.5 text-[0.875rem]">
                <Linha rotulo="Versão vigente" valor={`v${estatuto.versao}`} />
                <Linha rotulo="Data" valor={dataBr(estatuto.data)} />
                <Linha rotulo="Registro" valor={estatuto.registro ?? "—"} />
                <Linha
                  rotulo="Regras confirmadas"
                  valor={`${estatuto.parametros_confirmados} de ${estatuto.parametros_totais}`}
                />
              </dl>
            )}
            {parametrosPendentes > 0 && (
              <div className="mt-3">
                <Aviso tom="atencao">
                  {parametrosPendentes} regra(s) sem confirmação. Enquanto não forem
                  confirmadas, não são usadas nas validações.
                </Aviso>
              </div>
            )}
          </Cartao>

          <Cartao titulo="Score de conformidade" descricao="Pesos configuráveis por cliente">
            <PainelScore score={score} />
          </Cartao>

          <Cartao titulo="Pendências" descricao={`${pendencias.length} no total`}>
            {pendencias.length === 0 ? (
              <Vazio>Nenhuma pendência aberta.</Vazio>
            ) : (
              <ul className="divide-y">
                {pendencias.map((p) => (
                  <li key={p.codigo} className="py-2.5 first:pt-0 last:pb-0">
                    <div className="flex items-start gap-2.5">
                      <span className="mt-0.5">
                        <Farol estado={p.severidade} tamanho={13} />
                      </span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-baseline gap-x-2.5">
                          <span className="text-[0.875rem] font-medium">{p.titulo}</span>
                          <SeloPrioridade prioridade={p.prioridade} />
                        </div>
                        <p className="mt-0.5 text-[0.8125rem] leading-snug text-[var(--color-tinta-3)]">
                          {p.descricao}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>
        </div>
      </div>
    </div>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-[var(--color-tinta-3)]">{rotulo}</dt>
      <dd className="font-medium">{valor}</dd>
    </div>
  );
}
