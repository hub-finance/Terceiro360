import Link from "next/link";

import { Aviso, Cartao } from "@/componentes/base";
import { CatalogoAtos } from "@/componentes/catalogo-atos";
import { ClassificacaoAto } from "@/componentes/classificacao-ato";
import { Questionario } from "@/componentes/questionario";
import { ErroApi, chamarApi } from "@/lib/api";
import { referenciasDoEstatuto } from "@/lib/estatuto";
import type { Ato, AtoDetalhado } from "@/lib/tipos";

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

  // Sem tipo escolhido — ou com um tipo que o catálogo não reconhece — esta
  // tela mostra a escolha, em vez de 404. A URL é legítima nos dois casos:
  // quem chega aqui quer criar um ato, só não disse qual.
  let ato: AtoDetalhado | null = null;
  let tipoDesconhecido = false;

  if (tipo) {
    try {
      ato = await chamarApi<AtoDetalhado>(`/catalogo/eventos/${tipo}`);
    } catch (erro) {
      if (erro instanceof ErroApi && erro.status === 404) tipoDesconhecido = true;
      else throw erro;
    }
  }

  if (!ato) {
    const catalogo = await chamarApi<Record<string, Ato[]>>("/catalogo/eventos");
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <Link
          href={`/entidades/${id}/atos`}
          className="text-[0.8125rem] text-[var(--color-tinta-3)] hover:text-[var(--color-marca)]"
        >
          ← Atos
        </Link>
        <h1 className="mt-2 text-xl font-semibold tracking-tight">Novo ato</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Escolha o ato. O sistema lê o estatuto, pergunta apenas o que é próprio dele
          e diz o que impede o protocolo antes de gerar qualquer documento.
        </p>

        {tipoDesconhecido && (
          <div className="mt-5">
            <Aviso tom="atencao" titulo="Tipo de ato não reconhecido">
              O endereço apontava para <strong>{tipo}</strong>, que não existe no
              catálogo. Escolha abaixo.
            </Aviso>
          </div>
        )}

        <div className="mt-6">
          <CatalogoAtos entidadeId={id} catalogo={catalogo} />
        </div>
      </div>
    );
  }

  const referencias = await referenciasDoEstatuto(id);

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
