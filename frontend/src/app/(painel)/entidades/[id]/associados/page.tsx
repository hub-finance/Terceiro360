import { Aviso, Cartao, Etiqueta, Metrica, Vazio } from "@/componentes/base";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type { Associado, QuadroAssociados } from "@/lib/tipos";

export const metadata = { title: "Associados" };

const SITUACAO: Record<string, { rotulo: string; cor: string }> = {
  ATIVO: { rotulo: "Ativo", cor: "var(--color-apto)" },
  SUSPENSO: { rotulo: "Suspenso", cor: "var(--color-pendencia)" },
  LICENCIADO: { rotulo: "Licenciado", cor: "var(--color-pendencia)" },
  DESLIGADO: { rotulo: "Desligado", cor: "var(--color-tinta-3)" },
};

export default async function PaginaAssociados({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const quadro = await chamarApi<QuadroAssociados>(`/entidades/${id}/associados`);

  const porCategoria = new Map<string, Associado[]>();
  for (const a of quadro.associados) {
    const chave = a.categoria || "Sem categoria";
    porCategoria.set(chave, [...(porCategoria.get(chave) ?? []), a]);
  }
  const semVoto = quadro.total - quadro.aptos_a_votar;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Quadro de associados</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Quem é associado e quem, hoje, está apto a votar. Este número não é
          estatística: é a base de cálculo do quórum de toda assembleia — errar aqui
          vicia a deliberação inteira.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="No quadro" valor={quadro.total} detalhe="associados cadastrados" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Aptos a votar"
            valor={quadro.aptos_a_votar}
            tom="var(--color-apto)"
            detalhe="base do quórum hoje"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Sem direito de voto"
            valor={semVoto}
            tom={semVoto ? "var(--color-pendencia)" : undefined}
            detalhe="suspensos, desligados ou sem voto"
          />
        </Cartao>
      </div>

      {quadro.total === 0 ? (
        <Cartao>
          <Vazio>
            Nenhum associado cadastrado. Sem o quadro social, o sistema não consegue
            conferir quórum nem legitimidade de convocação.
          </Vazio>
        </Cartao>
      ) : (
        <div className="space-y-4">
          {quadro.aptos_a_votar === 0 && (
            <Aviso tom="erro" titulo="Nenhum associado apto a votar">
              Com o quadro assim, nenhuma assembleia se instala validamente. Confira as
              situações antes de convocar.
            </Aviso>
          )}

          {[...porCategoria.entries()].map(([categoria, associados]) => (
            <Cartao
              key={categoria}
              titulo={categoria}
              descricao={`${associados.length} associado(s) · ${
                associados.filter((a) => a.apto_hoje).length
              } apto(s) a votar`}
              denso
            >
              <ul className="divide-y">
                {associados.map((a) => {
                  const situacao = SITUACAO[a.situacao] ?? {
                    rotulo: a.situacao,
                    cor: "var(--color-tinta-3)",
                  };
                  return (
                    <li
                      key={a.id}
                      className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-2.5"
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[0.875rem] font-medium">
                          {a.pessoa}
                        </span>
                        <span className="block text-[0.75rem] text-[var(--color-tinta-3)]">
                          {a.cpf ?? "CPF não informado"}
                          {a.data_admissao && ` · desde ${dataBr(a.data_admissao)}`}
                        </span>
                      </span>
                      {a.elegivel && <Etiqueta>elegível</Etiqueta>}
                      <span
                        className="text-[0.75rem] font-medium"
                        style={{ color: situacao.cor }}
                      >
                        {situacao.rotulo}
                      </span>
                      <span
                        className="w-24 text-right text-[0.75rem] font-medium"
                        style={{
                          color: a.apto_hoje
                            ? "var(--color-apto)"
                            : "var(--color-tinta-3)",
                        }}
                      >
                        {a.apto_hoje ? "vota hoje" : "não vota"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Cartao>
          ))}
        </div>
      )}
    </div>
  );
}
