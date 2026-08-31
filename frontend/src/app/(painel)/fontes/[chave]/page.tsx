import Link from "next/link";

import { Aviso, Cartao, Etiqueta, SeloSemaforo } from "@/componentes/base";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type { FonteDetalhada } from "@/lib/tipos";

export async function generateMetadata({ params }: { params: Promise<{ chave: string }> }) {
  const { chave } = await params;
  const fonte = await chamarApi<FonteDetalhada>(`/normativo/fontes/${chave}`);
  return { title: fonte.apelido ?? fonte.identificacao };
}

export default async function PaginaFonte({
  params,
  searchParams,
}: {
  params: Promise<{ chave: string }>;
  searchParams: Promise<{ em?: string }>;
}) {
  const { chave } = await params;
  const { em } = await searchParams;
  const fonte = await chamarApi<FonteDetalhada>(
    `/normativo/fontes/${chave}${em ? `?em=${em}` : ""}`,
  );
  const versao = fonte.versao_aplicavel;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Link
        href="/fontes"
        className="text-[0.8125rem] text-[var(--color-tinta-3)] hover:text-[var(--color-marca)]"
      >
        ← Central de Fontes
      </Link>
      <h1 className="mt-2 text-xl font-semibold tracking-tight">
        {fonte.apelido ?? fonte.identificacao}
      </h1>
      <p className="mt-1 text-[0.875rem] text-[var(--color-tinta-3)]">{fonte.identificacao}</p>
      {fonte.ementa && (
        <p className="mt-2 text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
          {fonte.ementa}
        </p>
      )}
      {fonte.url_oficial && (
        <a
          href={fonte.url_oficial}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1.5 inline-block text-[0.8125rem] text-[var(--color-marca)] underline underline-offset-2"
        >
          texto oficial
        </a>
      )}

      <div className="mt-6 space-y-4">
        {!versao ? (
          <Aviso tom="erro" titulo="Nenhuma redação aplicável">
            Não há versão desta norma vigente na data consultada
            {em && ` (${dataBr(em)})`}.
          </Aviso>
        ) : (
          <>
            <Cartao
              titulo={`Redação vigente${em ? ` em ${dataBr(em)}` : ""}`}
              descricao={
                versao.vigente_desde
                  ? `Versão ${versao.numero}, desde ${dataBr(versao.vigente_desde)}`
                  : `Versão ${versao.numero}`
              }
              acao={
                <SeloSemaforo
                  estado={versao.curada ? "APTO" : "PENDENCIA"}
                  texto={versao.curada ? "Conferida" : "Não conferida"}
                />
              }
            >
              {!versao.curada && (
                <div className="mb-3">
                  <Aviso tom="atencao">
                    Esta redação é base de trabalho: entrou na carga inicial e ainda não
                    foi conferida por um responsável habilitado. O motor a cita marcando
                    &ldquo;não conferida&rdquo; nos achados.
                  </Aviso>
                </div>
              )}

              {versao.resumo_alteracao && (
                <p className="mb-3 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
                  {versao.resumo_alteracao}
                </p>
              )}

              {versao.dispositivos && versao.dispositivos.length > 0 ? (
                <ul className="space-y-3">
                  {versao.dispositivos.map((d) => (
                    <li key={d.identificacao} className="border-l-2 pl-3.5">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="text-[0.875rem] font-semibold">{d.identificacao}</span>
                        {d.revogado && <Etiqueta>revogado</Etiqueta>}
                        {d.tags.map((t) => (
                          <Etiqueta key={t}>{t}</Etiqueta>
                        ))}
                      </div>
                      {d.texto && (
                        <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
                          {d.texto}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[0.8125rem] text-[var(--color-tinta-3)]">
                  Nenhum dispositivo cadastrado nesta versão.
                </p>
              )}
            </Cartao>

            <Cartao
              titulo="Histórico"
              descricao="A redação antiga continua citável para os atos praticados na vigência dela"
            >
              <ul className="divide-y">
                {fonte.historico.map((v) => (
                  <li key={v.numero} className="py-2.5 first:pt-0 last:pb-0">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <span className="text-[0.875rem]">
                        Versão {v.numero}
                        <span className="ml-2 text-[0.75rem] text-[var(--color-tinta-3)]">
                          {v.situacao.toLowerCase()}
                        </span>
                      </span>
                      <span className="text-[0.8125rem] text-[var(--color-tinta-3)]">
                        {v.vigente_desde && dataBr(v.vigente_desde)}
                        {v.vigente_ate ? ` a ${dataBr(v.vigente_ate)}` : v.vigente_desde && " — hoje"}
                      </span>
                    </div>
                    {v.resumo_alteracao && (
                      <p className="mt-0.5 text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
                        {v.resumo_alteracao}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </Cartao>
          </>
        )}
      </div>
    </div>
  );
}
