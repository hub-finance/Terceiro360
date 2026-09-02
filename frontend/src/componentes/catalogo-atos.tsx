import Link from "next/link";

import type { Ato } from "@/lib/tipos";

const REFORMA_CURTA: Record<string, string> = {
  SEMPRE: "reforma estatutária",
  DEPENDE_DO_ESTATUTO: "pode ser reforma",
};

/** A grade de tipos de ato, agrupada por categoria.
 *
 * Vive fora da página porque duas telas precisam dela: a lista de atos e a
 * própria `/atos/novo` quando chega sem tipo escolhido. Antes, esse segundo
 * caso devolvia 404 — a URL era legítima, faltava só a escolha.
 */
export function CatalogoAtos({
  entidadeId,
  catalogo,
}: {
  entidadeId: string;
  catalogo: Record<string, Ato[]>;
}) {
  return (
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
                  href={`/entidades/${entidadeId}/atos/novo?tipo=${a.tipo}`}
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
  );
}
