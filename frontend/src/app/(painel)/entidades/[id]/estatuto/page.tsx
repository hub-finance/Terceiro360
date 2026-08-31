import { Aviso, Cartao, Etiqueta } from "@/componentes/base";
import { ListaParametros, type ParametroApi } from "@/componentes/parametros";
import { chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";

export const metadata = { title: "Estatuto" };

interface VersaoApi {
  id: string;
  numero: number;
  vigente: boolean;
  data_estatuto: string | null;
  data_registro: string | null;
  numero_registro: string | null;
  livro: string | null;
  folha: string | null;
  motivo_alteracao: string | null;
  parametros: number;
  parametros_confirmados: number;
}

interface EstatutoApi {
  estatuto_id?: string;
  versoes: VersaoApi[];
}

export default async function PaginaEstatuto({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const caminho = `/entidades/${id}/estatuto`;
  const estatuto = await chamarApi<EstatutoApi>(caminho);
  const vigente = estatuto.versoes.find((v) => v.vigente) ?? estatuto.versoes[0];

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Estatuto</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          O estatuto não fica guardado como PDF: vira regra utilizável. Cada valor
          abaixo só entra nas validações depois de confirmado por um responsável —
          é o que separa uma leitura do documento de uma decisão sobre ele.
        </p>
      </header>

      {!vigente ? (
        <Aviso tom="erro" titulo="Nenhuma versão cadastrada">
          Sem o estatuto, o sistema não valida quórum, prazo de convocação nem
          competência do órgão. Cadastre a versão vigente para começar.
        </Aviso>
      ) : (
        <div className="space-y-4">
          <Cartao
            titulo={`Versão ${vigente.numero}`}
            descricao={vigente.motivo_alteracao ?? "Versão vigente do estatuto social"}
            acao={
              <Etiqueta tom="marca">
                {vigente.parametros_confirmados} de {vigente.parametros} regras confirmadas
              </Etiqueta>
            }
          >
            <dl className="grid gap-x-8 gap-y-2 text-[0.875rem] sm:grid-cols-2">
              <Linha rotulo="Data do estatuto" valor={dataBr(vigente.data_estatuto)} />
              <Linha rotulo="Data do registro" valor={dataBr(vigente.data_registro)} />
              <Linha rotulo="Número de registro" valor={vigente.numero_registro ?? "—"} />
              <Linha
                rotulo="Livro / folha"
                valor={
                  vigente.livro || vigente.folha
                    ? `${vigente.livro ?? "—"} / ${vigente.folha ?? "—"}`
                    : "—"
                }
              />
            </dl>
          </Cartao>

          <Cartao
            titulo="Regras do estatuto"
            descricao="As perguntas estão em linguagem comum; a resposta é o que o sistema usa"
          >
            <ListaParametros
              versaoId={vigente.id}
              parametros={await chamarApi<ParametroApi[]>(
                `/estatuto/versoes/${vigente.id}/parametros`,
              )}
              caminho={caminho}
            />
          </Cartao>

          {estatuto.versoes.length > 1 && (
            <Cartao titulo="Histórico de versões" descricao="Nenhuma versão é sobrescrita">
              <ul className="divide-y">
                {estatuto.versoes.map((v) => (
                  <li key={v.id} className="flex items-baseline justify-between gap-3 py-2 first:pt-0 last:pb-0">
                    <span className="text-[0.875rem]">
                      Versão {v.numero}
                      {v.vigente && <span className="ml-2 text-[var(--color-apto)]">· vigente</span>}
                    </span>
                    <span className="text-[0.8125rem] text-[var(--color-tinta-3)]">
                      {dataBr(v.data_estatuto)}
                      {v.motivo_alteracao && ` · ${v.motivo_alteracao}`}
                    </span>
                  </li>
                ))}
              </ul>
            </Cartao>
          )}
        </div>
      )}
    </div>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-[var(--color-tinta-3)]">{rotulo}</dt>
      <dd className="font-medium">{valor}</dd>
    </div>
  );
}
