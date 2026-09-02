"use client";

/** Barra que diz, em toda tela de entidade, qual entidade é.
 *
 * O seletor vive no menu lateral, que some abaixo de 1024px e fica fora do
 * campo de visão quando se rola um formulário longo. Sem esta barra, quem
 * estava preenchendo uma ata não tinha como conferir se a entidade certa
 * estava selecionada — e o erro só apareceria no documento pronto.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

export function BarraEntidade({
  entidades,
}: {
  entidades: { id: string; razao_social: string; cnpj?: string | null }[];
}) {
  const caminho = usePathname();
  const id = caminho.match(/^\/entidades\/([0-9a-f-]{36})/)?.[1];
  if (!id) return null;

  const entidade = entidades.find((e) => e.id === id);
  if (!entidade) return null;

  return (
    <div className="sticky top-0 z-20 border-b bg-[var(--color-superficie)]/95 px-6 py-2 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-baseline gap-x-3 gap-y-0.5 pl-16 lg:pl-0">
        <span className="text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
          Entidade
        </span>
        <span className="min-w-0 truncate text-[0.875rem] font-semibold text-[var(--color-tinta)]">
          {entidade.razao_social}
        </span>
        {entidade.cnpj && (
          <span className="text-[0.75rem] text-[var(--color-tinta-3)]">{entidade.cnpj}</span>
        )}
        {entidades.length > 1 && (
          <Link
            href="/"
            className="ml-auto shrink-0 text-[0.75rem] font-medium text-[var(--color-marca)] underline-offset-2 hover:underline"
          >
            Trocar
          </Link>
        )}
      </div>
    </div>
  );
}
