/** Score de conformidade (§30).
 *
 *  A pontuação é um número de manchete — não um gráfico. O gráfico é a
 *  abertura por critério, que responde "por que esse número?". Sem essa
 *  abertura o score é palpite com aparência de medida.
 */
import type { Score } from "@/lib/tipos";

const COR_CLASSIFICACAO: Record<Score["classificacao"], string> = {
  Excelente: "var(--color-apto)",
  Regular: "var(--color-apto)",
  Atenção: "var(--color-pendencia)",
  "Risco elevado": "var(--color-bloqueado)",
};

export function PainelScore({ score }: { score: Score }) {
  const cor = COR_CLASSIFICACAO[score.classificacao];
  const criterios = [...score.criterios].sort((a, b) => a.atingido - b.atingido);

  return (
    <div className="space-y-5">
      <div className="flex items-end gap-4">
        <div>
          <span className="text-[3rem] font-semibold leading-none tracking-tight" style={{ color: cor }}>
            {Math.round(score.pontuacao)}
          </span>
          <span className="ml-1 text-[1rem] text-[var(--color-tinta-3)]">/100</span>
        </div>
        <div className="pb-1.5">
          <span className="text-[0.875rem] font-semibold" style={{ color: cor }}>
            {score.classificacao}
          </span>
          <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
            {criterios.filter((c) => c.atingido < 1).length} de {criterios.length} critérios
            com espaço para melhorar
          </p>
        </div>
      </div>

      {/* Uma série, ordenada do pior para o melhor: quem abre isto quer saber
          onde agir primeiro. Rótulo direto em cada barra dispensa legenda. */}
      <ul className="space-y-2.5">
        {criterios.map((c) => (
          <li key={c.codigo}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[0.8125rem] text-[var(--color-tinta-2)]">{c.rotulo}</span>
              <span className="shrink-0 text-[0.75rem] tabular-nums text-[var(--color-tinta-3)]">
                {c.pontos.toFixed(1)}/{c.peso}
              </span>
            </div>
            <div
              className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-superficie-2)]"
              role="img"
              aria-label={`${c.rotulo}: ${Math.round(c.atingido * 100)} por cento. ${c.justificativa}`}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(c.atingido * 100, c.atingido > 0 ? 3 : 0)}%`,
                  background:
                    c.atingido >= 0.999
                      ? "var(--color-apto)"
                      : c.atingido >= 0.5
                        ? "var(--color-marca)"
                        : "var(--color-pendencia)",
                }}
              />
            </div>
            <p className="mt-1 text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
              {c.justificativa}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
