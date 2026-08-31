import Link from "next/link";
import { notFound } from "next/navigation";

import { Cartao } from "@/componentes/base";
import { ClassificacaoAto } from "@/componentes/classificacao-ato";
import { Questionario } from "@/componentes/questionario";
import { chamarApi } from "@/lib/api";
import { referenciasDoEstatuto } from "@/lib/estatuto";
import type { AtoDetalhado } from "@/lib/tipos";

export const metadata = { title: "Novo ato" };

export default async function PaginaNovoAto({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tipo?: string }>;
}) {
  const { id } = await params;
  const { tipo } = await searchParams;
  if (!tipo) notFound();

  const [ato, referencias] = await Promise.all([
    chamarApi<AtoDetalhado>(`/catalogo/eventos/${tipo}`),
    referenciasDoEstatuto(id),
  ]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <Link
        href={`/entidades/${id}/atos`}
        className="text-[0.8125rem] text-[var(--color-tinta-3)] hover:text-[var(--color-marca)]"
      >
        ← Atos
      </Link>
      <h1 className="mt-2 text-xl font-semibold tracking-tight">{ato.titulo}</h1>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Cartao titulo="Dados do ato" descricao="Só o que é próprio deste ato; o resto vem do cadastro">
          <Questionario
            campos={ato.questionario.campos}
            valoresIniciais={{}}
            referencias={referencias}
            entidadeId={id}
            tipo={ato.tipo}
            caminho={`/entidades/${id}/atos`}
          />
        </Cartao>

        <div className="lg:sticky lg:top-6 lg:self-start">
          <Cartao titulo="O que este ato exige">
            <ClassificacaoAto ato={ato} />
          </Cartao>
        </div>
      </div>
    </div>
  );
}
