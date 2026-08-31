"use client";

/** As vigílias da base normativa (§38).
 *
 *  Onde existe endereço oficial estável, o sistema busca o texto e compara a
 *  impressão digital. Onde não existe — o caso dos cartórios —, a vigília é
 *  uma tarefa de reconferência humana, e o sistema diz isso com todas as
 *  letras em vez de fingir que consultou.
 */
import { useState, useTransition } from "react";

import { Aviso, Botao, Etiqueta } from "@/componentes/base";
import { verificarVigilia } from "@/lib/acoes";
import { dataBr } from "@/lib/formato";
import type { Vigilia } from "@/lib/tipos";

const SITUACAO: Record<Vigilia["situacao"], { rotulo: string; cor: string }> = {
  EM_DIA: { rotulo: "Em dia", cor: "var(--color-apto)" },
  VENCIDA: { rotulo: "Vencida", cor: "var(--color-pendencia)" },
  ATRASADA: { rotulo: "Atrasada", cor: "var(--color-bloqueado)" },
  NUNCA_VERIFICADA: { rotulo: "Nunca verificada", cor: "var(--color-pendencia)" },
};

export function ListaVigilias({ vigilias }: { vigilias: Vigilia[] }) {
  if (vigilias.length === 0) {
    return (
      <Aviso tom="sucesso">
        Todas as fontes foram reconferidas dentro da periodicidade configurada.
      </Aviso>
    );
  }
  return (
    <ul className="divide-y">
      {vigilias.map((v) => (
        <ItemVigilia key={v.id} vigilia={v} />
      ))}
    </ul>
  );
}

function ItemVigilia({ vigilia }: { vigilia: Vigilia }) {
  const [resultado, definirResultado] = useState<string | null>(null);
  const [tom, definirTom] = useState<"sucesso" | "atencao" | "erro">("sucesso");
  const [colando, definirColando] = useState(false);
  const [texto, definirTexto] = useState("");
  const [pendente, iniciar] = useTransition();
  const s = SITUACAO[vigilia.situacao];

  function verificar(conteudo?: string) {
    definirResultado(null);
    iniciar(async () => {
      const r = await verificarVigilia(vigilia.id, conteudo);
      if (!r.ok) {
        definirTom("erro");
        definirResultado(r.mensagem ?? "Falha ao verificar.");
        return;
      }
      if (r.houveMudanca) {
        definirTom("atencao");
        definirResultado(
          "O texto publicado mudou desde a última verificação. Uma atualização foi "
            + "aberta para triagem — nada entra em vigor sem curadoria.",
        );
      } else if (r.mensagem) {
        definirTom("atencao");
        definirResultado(`${r.mensagem} Registre a conferência colando o texto oficial.`);
      } else {
        definirTom("sucesso");
        definirResultado("Conteúdo idêntico ao da última verificação.");
      }
      definirColando(false);
      definirTexto("");
    });
  }

  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="text-[0.875rem] font-medium leading-snug">{vigilia.nome}</p>
          <p className="mt-0.5 text-[0.75rem] text-[var(--color-tinta-3)]">
            {vigilia.ultima_verificacao
              ? `Última conferência em ${dataBr(vigilia.ultima_verificacao)}`
              : "Nunca conferida"}
            {" · a cada "}
            {vigilia.periodicidade_dias} dias
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Etiqueta>{vigilia.modo === "HTTP" ? "automática" : "manual"}</Etiqueta>
          <span className="text-[0.75rem] font-semibold" style={{ color: s.cor }}>
            {s.rotulo}
          </span>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        <Botao variante="secundario" disabled={pendente} onClick={() => verificar()}>
          {pendente ? "Verificando…" : "Verificar agora"}
        </Botao>
        <Botao variante="silencioso" onClick={() => definirColando((v) => !v)}>
          {colando ? "Cancelar" : "Registrar conferência manual"}
        </Botao>
      </div>

      {colando && (
        <div className="mt-2.5 space-y-2">
          <label className="block text-[0.75rem] font-medium text-[var(--color-tinta-2)]">
            Cole o texto que você encontrou na fonte oficial
            <textarea
              rows={5}
              value={texto}
              onChange={(e) => definirTexto(e.target.value)}
              className="mt-1 w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.8125rem] font-normal"
              placeholder="O sistema compara com a redação registrada e abre uma atualização se houver diferença."
            />
          </label>
          <Botao disabled={pendente || !texto.trim()} onClick={() => verificar(texto)}>
            Comparar com a redação registrada
          </Botao>
        </div>
      )}

      {resultado && (
        <div className="mt-2">
          <Aviso tom={tom}>{resultado}</Aviso>
        </div>
      )}
    </li>
  );
}
