/** Marca do TERCEIRO360. O “360” é o anel que fecha o ciclo do ato. */
export function Marca({ tamanho = 28, comTexto = true }: { tamanho?: number; comTexto?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg
        width={tamanho}
        height={tamanho}
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden="true"
        className="shrink-0"
      >
        <circle cx="16" cy="16" r="13" stroke="var(--color-marca)" strokeWidth="2.5" opacity="0.25" />
        <path
          d="M16 3a13 13 0 0 1 11.3 6.6"
          stroke="var(--color-apto)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path
          d="M27.3 22.4A13 13 0 0 1 16 29"
          stroke="var(--color-pendencia)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <path d="M16 9.5v7l4.5 2.6" stroke="var(--color-marca)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {comTexto && (
        <span className="text-[0.9375rem] font-bold tracking-[0.02em] text-[var(--color-tinta)]">
          TERCEIRO<span className="text-[var(--color-marca)]">360</span>
        </span>
      )}
    </span>
  );
}
