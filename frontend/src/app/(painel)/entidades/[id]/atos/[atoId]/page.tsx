import Link from "next/link";

import { AcoesAto } from "@/componentes/acoes-ato";
import { Aviso, Cartao, Etiqueta, Vazio } from "@/componentes/base";
import { ClassificacaoAto } from "@/componentes/classificacao-ato";
import { Questionario } from "@/componentes/questionario";
import { PainelChecklist, PainelValidacao } from "@/componentes/validacao";
import { chamarApi } from "@/lib/api";
import { referenciasDoEstatuto } from "@/lib/estatuto";
import { dataBr } from "@/lib/formato";
import type {
  AtoDetalhado,
  Checklist,
  DocumentoResumo,
  Evento,
  ResultadoValidacao,
} from "@/lib/tipos";

export default async function PaginaAto({
  params,
}: {
  params: Promise<{ id: string; atoId: string }>;
}) {
  const { id, atoId } = await params;
  const caminho = `/entidades/${id}/atos/${atoId}`;

  const evento = await chamarApi<Evento>(`/eventos/${atoId}`);
  const [ato, referencias, validacao, checklist, documentos] = await Promise.all([
    chamarApi<AtoDetalhado>(`/catalogo/eventos/${evento.tipo}`),
    referenciasDoEstatuto(id),
    chamarApi<ResultadoValidacao>(`/eventos/${atoId}/validacao`),
    chamarApi<Checklist>(`/eventos/${atoId}/checklist`),
    chamarApi<DocumentoResumo[]>(`/entidades/${id}/documentos`),
  ]);

  const documentosDoAto = documentos.filter((d) => d.evento_id === atoId);
  const bloqueado = validacao.semaforo === "BLOQUEADO";

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <Link
        href={`/entidades/${id}/atos`}
        className="text-[0.8125rem] text-[var(--color-tinta-3)] hover:text-[var(--color-marca)]"
      >
        ← Atos
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="text-xl font-semibold tracking-tight">{evento.titulo ?? ato.titulo}</h1>
        <Etiqueta>{evento.status.replaceAll("_", " ").toLowerCase()}</Etiqueta>
        {evento.data_referencia && (
          <span className="text-[0.875rem] text-[var(--color-tinta-3)]">
            {dataBr(evento.data_referencia)}
          </span>
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4">
          <Cartao titulo="Dados do ato">
            <Questionario
              campos={ato.questionario.campos}
              valoresIniciais={evento.dados}
              referencias={referencias}
              eventoId={atoId}
              entidadeId={id}
              tipo={evento.tipo}
              caminho={caminho}
            />
          </Cartao>

          <Cartao
            titulo="Documentos"
            descricao={
              documentosDoAto.length > 0
                ? `${documentosDoAto.length} gerado(s)`
                : "Nenhum documento gerado ainda"
            }
          >
            {documentosDoAto.length === 0 ? (
              <Vazio>
                Os documentos são gerados a partir dos dados acima e do cadastro da
                entidade.
              </Vazio>
            ) : (
              <ul className="divide-y">
                {documentosDoAto.map((d) => (
                  <li key={d.id}>
                    <Link
                      href={`/entidades/${id}/documentos/${d.id}`}
                      className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2.5 hover:text-[var(--color-marca)]"
                    >
                      <span className="text-[0.875rem]">{d.titulo}</span>
                      <span className="flex shrink-0 items-center gap-2.5 text-[0.75rem] text-[var(--color-tinta-3)]">
                        v{d.versao_atual}
                        <Etiqueta>{d.status.toLowerCase()}</Etiqueta>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Cartao>
        </div>

        <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <Cartao titulo="Validação" descricao="Lei + estatuto + regra do cartório">
            <PainelValidacao resultado={validacao} />
            <div className="mt-4 border-t pt-4">
              <AcoesAto
                eventoId={atoId}
                caminho={caminho}
                podeGerar={validacao.pode_gerar_documentos}
                bloqueado={bloqueado}
              />
            </div>
          </Cartao>

          <Cartao titulo="Checklist de protocolo">
            <PainelChecklist checklist={checklist} />
          </Cartao>

          <Cartao titulo="O que este ato exige">
            <ClassificacaoAto ato={ato} />
          </Cartao>

          <Aviso tom="neutro">
            A automação auxilia na preparação, organização, validação e geração dos
            documentos, mas não substitui a análise profissional quando esta for
            necessária.
          </Aviso>
        </div>
      </div>
    </div>
  );
}
