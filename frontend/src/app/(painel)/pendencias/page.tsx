import { Cartao, Metrica } from "@/componentes/base";
import { HistoricoVarreduras, ListaPendencias, VarreduraManual } from "@/componentes/agenda";
import { chamarApi } from "@/lib/api";
import type { ExecucaoAgendador, PendenciaAberta } from "@/lib/tipos";

export const metadata = { title: "Pendências" };

export default async function PaginaPendencias() {
  const [pendencias, execucoes] = await Promise.all([
    chamarApi<PendenciaAberta[]>("/pendencias"),
    chamarApi<ExecucaoAgendador[]>("/agendador/execucoes?limite=15"),
  ]);

  const urgentes = pendencias.filter((p) => p.prioridade === "URGENTE" || p.prioridade === "ALTA");
  const daBase = pendencias.filter((p) => p.entidade_id === null);
  const dasEntidades = pendencias.filter((p) => p.entidade_id !== null);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Central de pendências</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Tudo o que o sistema encontrou e não pode resolver sozinho — porque depende
          de um dado que ninguém informou, de uma conferência em fonte oficial ou de
          uma decisão que é de quem responde tecnicamente pelo ato.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="Em aberto" valor={pendencias.length} detalhe="pendências" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Prioritárias"
            valor={urgentes.length}
            tom={urgentes.length ? "var(--color-bloqueado)" : undefined}
            detalhe="urgentes ou altas"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Da base normativa"
            valor={daBase.length}
            tom={daBase.length ? "var(--color-pendencia)" : undefined}
            detalhe="valem para todas as entidades"
          />
        </Cartao>
      </div>

      <div className="space-y-4">
        {dasEntidades.length > 0 && (
          <Cartao
            titulo="Das entidades"
            descricao="Cadastro, prazo ou ato que precisa de alguém"
            denso
          >
            <ListaPendencias pendencias={dasEntidades} caminho="/pendencias" />
          </Cartao>
        )}

        {daBase.length > 0 && (
          <Cartao
            titulo="Da base normativa"
            descricao="Conferência de fonte e triagem de mudança na lei"
            denso
          >
            <ListaPendencias pendencias={daBase} caminho="/pendencias" />
          </Cartao>
        )}

        {pendencias.length === 0 && (
          <Cartao>
            <p className="py-6 text-center text-[0.8125rem] text-[var(--color-tinta-3)]">
              Nenhuma pendência em aberto. Vale conferir abaixo se a varredura rodou —
              silêncio por falta de verificação não é a mesma coisa que estar em ordem.
            </p>
          </Cartao>
        )}

        <Cartao
          titulo="Varreduras"
          descricao="Quando o agendador rodou e o que encontrou"
          acao={<VarreduraManual tarefa="vigilias" caminho="/pendencias" />}
          denso
        >
          <HistoricoVarreduras execucoes={execucoes} />
        </Cartao>
      </div>
    </div>
  );
}
