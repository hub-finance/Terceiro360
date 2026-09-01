"use client";

/** Disparo manual da varredura e baixa de pendência (§21, §43). */
import { useState, useTransition } from "react";

import { Aviso, Botao, Etiqueta, SeloPrioridade, Vazio } from "@/componentes/base";
import { resolverPendencia, rodarVarredura } from "@/lib/acoes";
import { dataBr } from "@/lib/formato";
import type { ExecucaoAgendador, PendenciaAberta, Prioridade } from "@/lib/tipos";

export function VarreduraManual({
  tarefa,
  caminho,
}: {
  tarefa: "vigilias" | "prazos";
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [retorno, definirRetorno] = useState<string | null>(null);

  return (
    <span className="flex flex-wrap items-center justify-end gap-2">
      {retorno && (
        <span className="text-[0.75rem] text-[var(--color-tinta-3)]">{retorno}</span>
      )}
      <Botao
        variante="secundario"
        disabled={pendente}
        onClick={() =>
          iniciar(async () => {
            const r = await rodarVarredura(tarefa, caminho);
            definirRetorno(r.ok ? (r.detalhe ?? "Concluída.") : (r.mensagem ?? "Falhou."));
          })
        }
      >
        {pendente ? "Varrendo…" : "Rodar varredura agora"}
      </Botao>
    </span>
  );
}

export function ListaPendencias({
  pendencias,
  caminho,
}: {
  pendencias: PendenciaAberta[];
  caminho: string;
}) {
  if (pendencias.length === 0) {
    return <Vazio>Nenhuma pendência em aberto.</Vazio>;
  }
  return (
    <ul className="divide-y">
      {pendencias.map((p) => (
        <ItemPendencia key={p.id} pendencia={p} caminho={caminho} />
      ))}
    </ul>
  );
}

function ItemPendencia({
  pendencia,
  caminho,
}: {
  pendencia: PendenciaAberta;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const [resolvida, definirResolvida] = useState(false);

  if (resolvida) {
    return (
      <li className="px-5 py-3 text-[0.8125rem]" style={{ color: "var(--color-apto)" }}>
        {pendencia.descricao} — marcada como resolvida.
      </li>
    );
  }

  return (
    <li className="px-5 py-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <SeloPrioridade prioridade={pendencia.prioridade as Prioridade} />
        <span className="min-w-0 flex-1 text-[0.875rem] font-medium">
          {pendencia.descricao}
        </span>
        <Etiqueta>{pendencia.entidade ?? "base normativa"}</Etiqueta>
        <Botao
          variante="silencioso"
          disabled={pendente}
          onClick={() =>
            iniciar(async () => {
              const r = await resolverPendencia(pendencia.id, caminho);
              if (r.ok) definirResolvida(true);
              else definirErro(r.mensagem ?? "Falha ao resolver.");
            })
          }
        >
          Resolver
        </Botao>
      </div>
      {pendencia.detalhamento && (
        <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
          {pendencia.detalhamento}
        </p>
      )}
      <p className="mt-1 text-[0.75rem] text-[var(--color-tinta-3)]">
        Aberta em {dataBr(pendencia.criado_em)} · origem {pendencia.origem.toLowerCase()}
        {pendencia.prazo_limite && ` · prazo ${dataBr(pendencia.prazo_limite)}`}
      </p>
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}
    </li>
  );
}

export function HistoricoVarreduras({ execucoes }: { execucoes: ExecucaoAgendador[] }) {
  if (execucoes.length === 0) {
    return (
      <Vazio>
        O agendador nunca rodou nesta base. Enquanto isso, nenhum alerta é disparado.
      </Vazio>
    );
  }
  const COR: Record<string, string> = {
    OK: "var(--color-apto)",
    PARCIAL: "var(--color-pendencia)",
    ERRO: "var(--color-bloqueado)",
  };
  return (
    <ul className="divide-y">
      {execucoes.map((e) => (
        <li key={e.id} className="px-5 py-2.5">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.8125rem]">
            <span className="font-medium" style={{ color: COR[e.resultado] }}>
              {e.resultado}
            </span>
            <span className="font-medium">{e.tarefa.toLowerCase()}</span>
            <span className="min-w-0 flex-1 text-[var(--color-tinta-2)]">{e.detalhe}</span>
            <span className="text-[0.75rem] text-[var(--color-tinta-3)]">
              {dataBr(e.iniciada_em)}
              {e.duracao_s !== null && ` · ${e.duracao_s}s`}
              {e.acionada_por === "MANUAL" && " · manual"}
            </span>
          </div>
          {e.falhas.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {e.falhas.map((f, i) => (
                <li
                  key={`${f.alvo}-${i}`}
                  className="text-[0.75rem]"
                  style={{ color: "var(--color-bloqueado)" }}
                >
                  {f.alvo}: {f.erro}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
