/** Resultado do motor de validação: semáforo, achados e checklist (§12, §13). */
import { Aviso, Farol, SeloSemaforo, Vazio } from "@/componentes/base";
import type { Achado, Checklist, ResultadoValidacao } from "@/lib/tipos";

const RESUMO: Record<string, string> = {
  APTO: "Nenhuma inconsistência nos pontos verificados.",
  PENDENCIA: "O ato pode seguir, mas há pontos a confirmar antes do protocolo.",
  BLOQUEADO: "Há inconsistência que impede a geração dos documentos.",
};

export function PainelValidacao({ resultado }: { resultado: ResultadoValidacao }) {
  const ordenados = [...resultado.achados].sort(
    (a, b) => peso(b.severidade) - peso(a.severidade),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <Farol estado={resultado.semaforo} tamanho={22} />
        <div>
          <p className="text-[0.9375rem] font-semibold leading-tight">
            {resultado.semaforo === "APTO"
              ? "Apto"
              : resultado.semaforo === "PENDENCIA"
                ? "Com pendências"
                : "Bloqueado"}
          </p>
          <p className="mt-0.5 text-[0.8125rem] leading-snug text-[var(--color-tinta-3)]">
            {RESUMO[resultado.semaforo]}
          </p>
        </div>
      </div>

      {ordenados.length === 0 ? (
        <Vazio>Nada a apontar.</Vazio>
      ) : (
        <ul className="space-y-2.5">
          {ordenados.map((a) => (
            <ItemAchado key={a.codigo} achado={a} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ItemAchado({ achado }: { achado: Achado }) {
  return (
    <li className="rounded-md border px-3.5 py-3">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5">
          <Farol estado={achado.severidade} tamanho={14} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[0.875rem] font-medium leading-snug">{achado.titulo}</p>
          <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
            {achado.mensagem}
          </p>

          {achado.sugestao && (
            <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-3)]">
              {achado.sugestao}
            </p>
          )}

          {/* §38 — toda conclusão jurídica mostra de onde veio. */}
          {achado.fundamentos.length > 0 && (
            <ul className="mt-2 space-y-1">
              {achado.fundamentos.map((f, i) => (
                <li key={i} className="text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
                  <span className="font-medium">{f.referencia}</span>
                  {f.dispositivo && `, ${f.dispositivo}`}
                  {f.curado === false && (
                    <span
                      className="ml-1.5"
                      title="Redação ainda não conferida por um responsável habilitado"
                    >
                      · não conferida
                    </span>
                  )}
                  {f.url && (
                    <>
                      {" · "}
                      <a
                        href={f.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline underline-offset-2 hover:text-[var(--color-marca)]"
                      >
                        texto oficial
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </li>
  );
}

export function PainelChecklist({ checklist }: { checklist: Checklist }) {
  const ORIGEM: Record<string, string> = {
    ATO: "produzido pelo ato",
    ESTATUTO: "exigido pelo estatuto",
    RCPJ: "exigido pelo cartório",
    LEI: "exigido por lei",
    SISTEMA: "sistema",
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <SeloSemaforo
          estado={checklist.completo ? "APTO" : "PENDENCIA"}
          texto={
            checklist.completo
              ? "Documentação reunida"
              : `${checklist.pendentes} de ${checklist.total} pendentes`
          }
        />
      </div>

      <ul className="space-y-1">
        {checklist.itens.map((i) => (
          <li key={i.codigo} className="flex items-start gap-2.5 py-1">
            <span
              aria-hidden
              className="mt-[0.3rem] flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-[3px] border text-[0.6rem] font-bold"
              style={
                i.status === "OK"
                  ? {
                      background: "var(--color-apto)",
                      borderColor: "var(--color-apto)",
                      color: "#fff",
                    }
                  : undefined
              }
            >
              {i.status === "OK" ? "✓" : ""}
            </span>
            <span className="min-w-0 flex-1">
              <span
                className="text-[0.8125rem]"
                style={i.status === "OK" ? { color: "var(--color-tinta-3)" } : undefined}
              >
                {i.descricao}
                {!i.obrigatorio && (
                  <span className="text-[var(--color-tinta-3)]"> (opcional)</span>
                )}
              </span>
              <span className="block text-[0.6875rem] text-[var(--color-tinta-3)]">
                {(i.origens ?? [i.origem]).map((o) => ORIGEM[o] ?? o).join(" · ")}
                {i.fundamento && ` — ${i.fundamento}`}
              </span>
            </span>
          </li>
        ))}
      </ul>

      {checklist.avisos.map((a) => (
        <Aviso key={a} tom="atencao">
          {a}
        </Aviso>
      ))}
    </div>
  );
}

function peso(s: string) {
  return s === "BLOQUEADO" ? 2 : s === "PENDENCIA" ? 1 : 0;
}
