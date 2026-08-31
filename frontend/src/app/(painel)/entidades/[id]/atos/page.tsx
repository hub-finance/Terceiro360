import Link from "next/link";

import { Cartao, Etiqueta, Farol } from "@/componentes/base";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type { Ato, Evento } from "@/lib/tipos";

export const metadata = { title: "Atos" };

const REFORMA_CURTA: Record<string, string> = {
  SEMPRE: "reforma estatutária",
  DEPENDE_DO_ESTATUTO: "pode ser reforma",
};

export default async function PaginaAtos({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [eventos, catalogo] = await Promise.all([
    chamarApi<Evento[]>(`/entidades/${id}/eventos`),
    chamarApi<Record<string, Ato[]>>("/catalogo/eventos"),
  ]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Atos</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Escolha o ato. O sistema lê o estatuto, pergunta apenas o que é próprio dele
          e diz o que impede o protocolo antes de você gerar qualquer documento.
        </p>
      </header>

      {eventos.length > 0 && (
        <Cartao titulo="Em andamento" className="mb-6">
          <ul className="divide-y">
            {eventos.map((e) => (
              <li key={e.id}>
                <Link
                  href={`/entidades/${id}/atos/${e.id}`}
                  className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2.5 hover:text-[var(--color-marca)]"
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    {e.semaforo ? (
                      <Farol estado={e.semaforo} tamanho={14} />
                    ) : (
                      <span className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border" />
                    )}
                    <span className="truncate text-[0.875rem]">{e.titulo ?? e.tipo}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-3 text-[0.75rem] text-[var(--color-tinta-3)]">
                    {e.data_referencia && dataBr(e.data_referencia)}
                    <Etiqueta>{e.status.replaceAll("_", " ").toLowerCase()}</Etiqueta>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      <h2 className="mb-3 text-[0.9375rem] font-semibold tracking-tight">Novo ato</h2>
      <div className="space-y-5">
        {Object.entries(catalogo).map(([categoria, atos]) => (
          <section key={categoria}>
            <h3 className="mb-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
              {categoria}
            </h3>
            <ul className="grid gap-2 sm:grid-cols-2">
              {atos.map((a) => (
                <li key={a.tipo}>
                  <Link
                    href={`/entidades/${id}/atos/novo?tipo=${a.tipo}`}
                    className="block h-full rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] px-4 py-3 transition-colors hover:border-[var(--color-marca-contorno)]"
                  >
                    <span className="text-[0.875rem] font-medium">{a.titulo}</span>
                    <p className="mt-0.5 text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
                      {a.descricao}
                    </p>
                    {REFORMA_CURTA[a.exige_reforma_estatutaria] && (
                      <span className="mt-1.5 inline-block text-[0.6875rem] font-medium text-[var(--color-pendencia)]">
                        {REFORMA_CURTA[a.exige_reforma_estatutaria]}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
