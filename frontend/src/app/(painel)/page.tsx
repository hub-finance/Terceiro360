import Link from "next/link";
import { redirect } from "next/navigation";

import { Cartao, Etiqueta, Vazio } from "@/componentes/base";
import { chamarApi } from "@/lib/api";
import type { EntidadeResumo } from "@/lib/tipos";

export default async function PaginaInicial() {
  const entidades = await chamarApi<EntidadeResumo[]>("/entidades");

  // Escritório com uma entidade só não precisa escolher nada.
  if (entidades.length === 1) redirect(`/entidades/${entidades[0].id}`);

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-xl font-semibold tracking-tight">Entidades</h1>
      <p className="mt-1 text-[0.875rem] text-[var(--color-tinta-3)]">
        {entidades.length === 0
          ? "Nenhuma entidade cadastrada ainda."
          : `${entidades.length} entidades sob sua gestão.`}
      </p>

      <div className="mt-6 space-y-2">
        {entidades.length === 0 && (
          <Cartao>
            <Vazio>
              Cadastre a primeira entidade para começar. É dela que saem todos os
              dados dos documentos.
            </Vazio>
          </Cartao>
        )}
        {entidades.map((e) => (
          <Link
            key={e.id}
            href={`/entidades/${e.id}`}
            className="block rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] px-5 py-4 shadow-[var(--shadow-cartao)] transition-colors hover:border-[var(--color-marca-contorno)]"
          >
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-semibold tracking-tight">{e.razao_social}</span>
              <Etiqueta>{e.tipo_entidade.replaceAll("_", " ").toLowerCase()}</Etiqueta>
            </div>
            <p className="mt-1 text-[0.8125rem] text-[var(--color-tinta-3)]">
              {e.cnpj ?? "CNPJ não informado"}
              {e.municipio && ` · ${e.municipio}/${e.uf}`}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
