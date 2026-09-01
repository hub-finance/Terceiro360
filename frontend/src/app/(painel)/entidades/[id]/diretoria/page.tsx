import { Aviso, Cartao, Etiqueta, Metrica, Vazio } from "@/componentes/base";
import { chamarApi } from "@/lib/api";
import { dataBr, iniciais, prazoRelativo } from "@/lib/formato";
import type { Mandato, MapaGovernanca, NoGovernanca } from "@/lib/tipos";

export const metadata = { title: "Diretoria" };

const SITUACAO: Record<string, { rotulo: string; cor: string }> = {
  ATIVO: { rotulo: "ativo", cor: "var(--color-apto)" },
  RENUNCIOU: { rotulo: "renunciou", cor: "var(--color-pendencia)" },
  DESTITUIDO: { rotulo: "destituído", cor: "var(--color-bloqueado)" },
  FALECIDO: { rotulo: "falecido", cor: "var(--color-tinta-3)" },
  AFASTADO: { rotulo: "afastado", cor: "var(--color-pendencia)" },
};

function diasAte(data: string): number {
  const limite = new Date(`${data.slice(0, 10)}T12:00:00`);
  const hoje = new Date();
  return Math.round((limite.getTime() - hoje.getTime()) / 86_400_000);
}

export default async function PaginaDiretoria({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [mandatos, mapa] = await Promise.all([
    chamarApi<Mandato[]>(`/entidades/${id}/mandatos`),
    chamarApi<MapaGovernanca>(`/entidades/${id}/governanca/mapa`),
  ]);

  const vigentes = mandatos.filter((m) => m.vigente && !m.encerrado);
  const encerrados = mandatos.filter((m) => !m.vigente || m.encerrado);
  const membrosAtivos = vigentes.flatMap((m) =>
    m.membros.filter((mm) => mm.situacao === "ATIVO"),
  );
  const proximoFim = vigentes.map((m) => diasAte(m.data_fim)).sort((a, b) => a - b)[0];

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Diretoria</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Quem responde pela entidade hoje, com que mandato e até quando. A eleição
          seguinte não apaga a gestão anterior: o histórico é o que prova quem
          assinava o quê em cada data.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="Em exercício" valor={membrosAtivos.length} detalhe="membros ativos" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Mandatos vigentes"
            valor={vigentes.length}
            tom={vigentes.length ? undefined : "var(--color-bloqueado)"}
            detalhe={vigentes.length ? "órgãos com gestão" : "nenhum mandato vigente"}
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Próximo encerramento"
            valor={proximoFim === undefined ? "—" : prazoRelativo(proximoFim)}
            tom={
              proximoFim !== undefined && proximoFim <= 90 ? "var(--color-pendencia)" : undefined
            }
            detalhe="fim de mandato"
          />
        </Cartao>
      </div>

      {vigentes.length === 0 && (
        <div className="mb-4">
          <Aviso tom="erro" titulo="Sem diretoria vigente">
            Nenhum mandato em vigor. Entidade sem diretoria regular não protocola ato,
            não movimenta conta e não assina convênio — a eleição é o primeiro passo
            para destravar todo o resto.
          </Aviso>
        </div>
      )}

      <div className="space-y-4">
        {vigentes.map((m) => (
          <QuadroMandato key={m.id} mandato={m} />
        ))}

        <Cartao
          titulo="Mapa de governança"
          descricao="Como os órgãos se organizam e quem os ocupa"
        >
          {mapa.orgaos.length === 0 ? (
            <Vazio>Nenhum órgão cadastrado.</Vazio>
          ) : (
            <ul className="space-y-2">
              {mapa.orgaos.map((o) => (
                <NoOrgao key={o.id} no={o} nivel={0} />
              ))}
            </ul>
          )}
        </Cartao>

        {encerrados.length > 0 && (
          <Cartao
            titulo="Gestões anteriores"
            descricao="Preservadas para prova de representação em atos passados"
            denso
          >
            <ul className="divide-y">
              {encerrados.map((m) => (
                <li key={m.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-2.5">
                  <span className="text-[0.875rem] font-medium">{m.designacao}</span>
                  <span className="text-[0.8125rem] text-[var(--color-tinta-3)]">
                    {m.orgao} · {dataBr(m.data_inicio)} a {dataBr(m.data_fim)}
                  </span>
                  <span className="ml-auto text-[0.75rem] text-[var(--color-tinta-3)]">
                    {m.membros.length} membro(s)
                  </span>
                </li>
              ))}
            </ul>
          </Cartao>
        )}
      </div>
    </div>
  );
}

function QuadroMandato({ mandato }: { mandato: Mandato }) {
  const dias = diasAte(mandato.data_fim);
  const acabando = dias <= 90;

  return (
    <Cartao
      titulo={mandato.designacao}
      descricao={`${mandato.orgao} · ${dataBr(mandato.data_inicio)} a ${dataBr(mandato.data_fim)}`}
      acao={
        <span
          className="text-[0.8125rem] font-medium"
          style={{ color: acabando ? "var(--color-pendencia)" : "var(--color-tinta-3)" }}
        >
          encerra {prazoRelativo(dias)}
        </span>
      }
    >
      {acabando && (
        <div className="mb-3">
          <Aviso tom="atencao">
            A eleição precisa acontecer antes do encerramento. Diretoria vencida não é
            só irregularidade formal: os atos praticados depois podem ser questionados.
          </Aviso>
        </div>
      )}
      <ul className="grid gap-2 sm:grid-cols-2">
        {mandato.membros.map((m) => {
          const situacao = SITUACAO[m.situacao] ?? {
            rotulo: m.situacao.toLowerCase(),
            cor: "var(--color-tinta-3)",
          };
          return (
            <li
              key={`${m.pessoa}-${m.cargo}`}
              className="flex items-center gap-3 rounded-md border px-3 py-2.5"
            >
              <span
                aria-hidden
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-superficie-2)] text-[0.6875rem] font-semibold text-[var(--color-tinta-2)]"
              >
                {iniciais(m.pessoa)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.875rem] font-medium">{m.pessoa}</span>
                <span className="block truncate text-[0.75rem] text-[var(--color-tinta-3)]">
                  {m.cargo}
                  {m.cpf && ` · ${m.cpf}`}
                </span>
              </span>
              {m.situacao !== "ATIVO" && (
                <span className="text-[0.6875rem] font-medium" style={{ color: situacao.cor }}>
                  {situacao.rotulo}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </Cartao>
  );
}

function NoOrgao({ no, nivel }: { no: NoGovernanca; nivel: number }) {
  return (
    <li style={{ marginLeft: nivel * 16 }}>
      <div className="rounded-md border px-3.5 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[0.875rem] font-medium">{no.nome}</span>
          <Etiqueta>{no.tipo.toLowerCase().replace(/_/g, " ")}</Etiqueta>
          {no.mandato && (
            <span className="text-[0.75rem] text-[var(--color-tinta-3)]">{no.mandato}</span>
          )}
        </div>
        {no.responsaveis.length > 0 ? (
          <p className="mt-1 text-[0.8125rem] text-[var(--color-tinta-2)]">
            {no.responsaveis.map((r) => `${r.nome} (${r.cargo})`).join(" · ")}
          </p>
        ) : (
          <p className="mt-1 text-[0.8125rem]" style={{ color: "var(--color-pendencia)" }}>
            Sem ocupante em exercício.
          </p>
        )}
      </div>
      {no.filhos.length > 0 && (
        <ul className="mt-2 space-y-2">
          {no.filhos.map((f) => (
            <NoOrgao key={f.id} no={f} nivel={nivel + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}
