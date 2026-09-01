import { Aviso, Cartao, Etiqueta, Metrica, SeloPrioridade, Vazio } from "@/componentes/base";
import { VarreduraManual } from "@/componentes/agenda";
import { chamarApi } from "@/lib/api";
import { dataBr, prazoRelativo } from "@/lib/formato";
import type { ExecucaoAgendador, PrazoRegistrado, Prioridade } from "@/lib/tipos";

export const metadata = { title: "Prazos" };

function prioridadeDe(dias: number): Prioridade {
  if (dias < 0 || dias <= 3) return "URGENTE";
  if (dias <= 15) return "ALTA";
  if (dias <= 60) return "MEDIA";
  return "BAIXA";
}

export default async function PaginaPrazos({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const caminho = `/entidades/${id}/prazos`;
  const [prazos, execucoes] = await Promise.all([
    chamarApi<PrazoRegistrado[]>(`/entidades/${id}/prazos/registrados`),
    chamarApi<ExecucaoAgendador[]>("/agendador/execucoes?limite=5"),
  ]);

  const abertos = prazos.filter((p) => p.status === "ABERTO");
  const vencidos = prazos.filter((p) => p.status === "VENCIDO");
  const encerrados = prazos.filter((p) => p.status === "CUMPRIDO" || p.status === "CANCELADO");
  const ultimaVarredura = execucoes.find((e) => e.tarefa === "PRAZOS");

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Prazos</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          O que vence e quando, com a origem de cada data — lei, estatuto ou exigência
          de cartório. Prazo aqui nunca é chute: se o parâmetro não foi confirmado, o
          sistema abre pendência em vez de inventar a data.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="Em acompanhamento" valor={abertos.length} detalhe="prazos abertos" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Vencidos"
            valor={vencidos.length}
            tom={vencidos.length ? "var(--color-bloqueado)" : undefined}
            detalhe="passaram da data"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Última varredura"
            valor={ultimaVarredura ? dataBr(ultimaVarredura.iniciada_em) : "nunca"}
            tom={ultimaVarredura ? undefined : "var(--color-pendencia)"}
            detalhe={ultimaVarredura?.detalhe ?? "o agendador ainda não rodou"}
          />
        </Cartao>
      </div>

      {!ultimaVarredura && (
        <div className="mb-4">
          <Aviso tom="atencao" titulo="O agendador ainda não rodou nesta base">
            Os prazos abaixo só existem depois da primeira varredura. Enquanto ela não
            roda, ninguém é avisado de nada — nem por aqui, nem por notificação.
          </Aviso>
        </div>
      )}

      <div className="space-y-4">
        <Cartao
          titulo="Agenda"
          descricao="Ordenada pela data limite"
          acao={<VarreduraManual tarefa="prazos" caminho={caminho} />}
          denso
        >
          {[...vencidos, ...abertos].length === 0 ? (
            <Vazio>Nenhum prazo em acompanhamento.</Vazio>
          ) : (
            <ul className="divide-y">
              {[...vencidos, ...abertos].map((p) => (
                <li key={p.id} className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <SeloPrioridade prioridade={prioridadeDe(p.dias_restantes)} />
                    <span className="min-w-0 flex-1 text-[0.875rem] font-medium">
                      {p.descricao}
                    </span>
                    <span
                      className="text-[0.8125rem] font-medium"
                      style={{
                        color:
                          p.dias_restantes < 0
                            ? "var(--color-bloqueado)"
                            : "var(--color-tinta-2)",
                      }}
                    >
                      {prazoRelativo(p.dias_restantes)}
                    </span>
                    <span className="w-24 text-right text-[0.8125rem] text-[var(--color-tinta-3)]">
                      {dataBr(p.data_limite)}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[0.75rem] text-[var(--color-tinta-3)]">
                    <Etiqueta>{p.origem.toLowerCase()}</Etiqueta>
                    {p.fundamento && <span>{p.fundamento}</span>}
                    {p.alertas_disparados.length > 0 && (
                      <span>
                        avisado em {p.alertas_disparados.sort((a, b) => b - a).join(", ")} dia(s)
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Cartao>

        {encerrados.length > 0 && (
          <Cartao titulo="Encerrados" descricao="Saíram da agenda porque foram resolvidos" denso>
            <ul className="divide-y">
              {encerrados.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-2.5 text-[0.8125rem]"
                >
                  <span className="min-w-0 flex-1 text-[var(--color-tinta-2)]">
                    {p.descricao}
                  </span>
                  <span className="text-[var(--color-tinta-3)]">{dataBr(p.data_limite)}</span>
                  <Etiqueta>{p.status.toLowerCase()}</Etiqueta>
                </li>
              ))}
            </ul>
          </Cartao>
        )}
      </div>
    </div>
  );
}
