/** Esqueleto mostrado enquanto a próxima tela é montada no servidor.
 *
 * Sem este arquivo, clicar numa aba deixava a tela anterior congelada até a
 * nova chegar inteira — e com a API em Oregon e o banco em São Paulo, isso
 * leva tempo suficiente para parecer que o clique falhou. Agora a área de
 * conteúdo troca na hora; o menu e a barra da entidade ficam onde estão.
 *
 * Tem um segundo efeito, menos visível: com uma fronteira de carregamento
 * definida, o Next pré-carrega a moldura das rotas cujos links estão na tela.
 * O clique deixa de esperar a rede para dar o primeiro sinal de vida.
 */
export default function Carregando() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando…</span>

      <div className="esqueleto mb-2 h-6 w-56 rounded" />
      <div className="esqueleto mb-8 h-4 w-96 max-w-full rounded" />

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] p-5">
            <div className="esqueleto mb-3 h-3 w-24 rounded" />
            <div className="esqueleto h-7 w-16 rounded" />
          </div>
        ))}
      </div>

      <div className="rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] p-5">
        <div className="esqueleto mb-4 h-4 w-40 rounded" />
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="esqueleto mb-3 h-3 rounded" style={{ width: `${92 - i * 9}%` }} />
        ))}
      </div>
    </div>
  );
}
