/** Componentes de base do TERCEIRO360. */
import type { ReactNode } from "react";

import type { Prioridade, Semaforo } from "@/lib/tipos";

/* ─────────────────────────────────────────────────────────── Superfícies */

export function Cartao({
  children, titulo, descricao, acao, className = "", denso = false,
}: {
  children?: ReactNode;
  titulo?: ReactNode;
  descricao?: ReactNode;
  acao?: ReactNode;
  className?: string;
  denso?: boolean;
}) {
  return (
    <section
      className={`rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] shadow-[var(--shadow-cartao)] ${className}`}
    >
      {(titulo || acao) && (
        <header className="flex items-start justify-between gap-4 border-b px-5 py-3.5">
          <div className="min-w-0">
            {titulo && (
              <h2 className="text-[0.9375rem] font-semibold tracking-tight text-[var(--color-tinta)]">
                {titulo}
              </h2>
            )}
            {descricao && (
              <p className="mt-0.5 text-[0.8125rem] text-[var(--color-tinta-3)]">{descricao}</p>
            )}
          </div>
          {acao && <div className="shrink-0">{acao}</div>}
        </header>
      )}
      <div className={denso ? "" : "px-5 py-4"}>{children}</div>
    </section>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return (
    <p className="py-6 text-center text-[0.8125rem] text-[var(--color-tinta-3)]">{children}</p>
  );
}

/* ────────────────────────────────────────────────────────────── Semáforo */

const SEMAFORO: Record<Semaforo, { rotulo: string; cor: string; fundo: string; contorno: string }> = {
  APTO: {
    rotulo: "Apto",
    cor: "var(--color-apto)",
    fundo: "var(--color-apto-fundo)",
    contorno: "var(--color-apto-contorno)",
  },
  PENDENCIA: {
    rotulo: "Pendência",
    cor: "var(--color-pendencia)",
    fundo: "var(--color-pendencia-fundo)",
    contorno: "var(--color-pendencia-contorno)",
  },
  BLOQUEADO: {
    rotulo: "Bloqueado",
    cor: "var(--color-bloqueado)",
    fundo: "var(--color-bloqueado-fundo)",
    contorno: "var(--color-bloqueado-contorno)",
  },
};

/** O farol do semáforo.
 *
 *  A cor aqui é o canal *secundário*. Verde, âmbar e vermelho não se separam
 *  para quem tem deuteranopia ou protanopia — rodamos o validador e não existe
 *  tríade que resolva isso. Então cada estado tem forma própria: círculo com
 *  visto, losango com exclamação, octógono com xis. Quem não distingue as
 *  cores lê a forma; quem distingue lê as duas.
 */
export function Farol({ estado, tamanho = 14 }: { estado: Semaforo; tamanho?: number }) {
  const { cor, rotulo } = SEMAFORO[estado];
  const comum = { width: tamanho, height: tamanho, viewBox: "0 0 16 16", role: "img" as const };
  const traco = {
    stroke: "var(--color-superficie)",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  if (estado === "APTO") {
    return (
      <svg {...comum} aria-label={rotulo} className="shrink-0">
        <circle cx="8" cy="8" r="8" fill={cor} />
        <path d="M4.5 8.3l2.4 2.4 4.6-5" {...traco} />
      </svg>
    );
  }

  if (estado === "PENDENCIA") {
    return (
      <svg {...comum} aria-label={rotulo} className="shrink-0">
        <path d="M8 0l8 8-8 8-8-8z" fill={cor} />
        <path d="M8 4.2v4.4" {...traco} />
        <circle cx="8" cy="11.6" r="1.15" fill="var(--color-superficie)" />
      </svg>
    );
  }

  return (
    <svg {...comum} aria-label={rotulo} className="shrink-0">
      <path d="M5 0h6l5 5v6l-5 5H5l-5-5V5z" fill={cor} />
      <path d="M5.4 5.4l5.2 5.2M10.6 5.4l-5.2 5.2" {...traco} />
    </svg>
  );
}

export function SeloSemaforo({
  estado, texto, className = "",
}: {
  estado: Semaforo;
  texto?: string;
  className?: string;
}) {
  const s = SEMAFORO[estado];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.75rem] font-semibold ${className}`}
      style={{ color: s.cor, background: s.fundo, borderColor: s.contorno }}
    >
      <Farol estado={estado} tamanho={12} />
      {texto ?? s.rotulo}
    </span>
  );
}

const PRIORIDADE: Record<Prioridade, { rotulo: string; cor: string }> = {
  URGENTE: { rotulo: "Urgente", cor: "var(--color-urgente)" },
  ALTA: { rotulo: "Alta", cor: "var(--color-alta)" },
  MEDIA: { rotulo: "Média", cor: "var(--color-media)" },
  BAIXA: { rotulo: "Baixa", cor: "var(--color-baixa)" },
};

export function SeloPrioridade({ prioridade }: { prioridade: Prioridade }) {
  const p = PRIORIDADE[prioridade];
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[0.6875rem] font-semibold uppercase tracking-wide"
      style={{ color: p.cor }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: p.cor }} />
      {p.rotulo}
    </span>
  );
}

export function Etiqueta({ children, tom = "neutro" }: { children: ReactNode; tom?: "neutro" | "marca" }) {
  const estilo =
    tom === "marca"
      ? "border-[var(--color-marca-contorno)] bg-[var(--color-marca-clara)] text-[var(--color-marca)]"
      : "border-[var(--color-borda)] bg-[var(--color-superficie-2)] text-[var(--color-tinta-2)]";
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[0.6875rem] font-medium ${estilo}`}>
      {children}
    </span>
  );
}

/* ──────────────────────────────────────────────────────────── Formulário */

export function Botao({
  children, variante = "primario", tipo = "button", ...resto
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "primario" | "secundario" | "silencioso" | "perigo";
  tipo?: "button" | "submit";
}) {
  const estilos = {
    primario:
      "bg-[var(--color-marca)] text-white hover:bg-[var(--color-marca-forte)] border-transparent",
    secundario:
      "bg-[var(--color-superficie)] text-[var(--color-tinta)] hover:bg-[var(--color-superficie-2)] border-[var(--color-borda-forte)]",
    silencioso:
      "bg-transparent text-[var(--color-tinta-2)] hover:bg-[var(--color-superficie-2)] border-transparent",
    perigo:
      "bg-[var(--color-bloqueado)] text-white hover:brightness-110 border-transparent",
  }[variante];

  return (
    <button
      type={tipo}
      {...resto}
      className={`inline-flex items-center justify-center gap-2 rounded-md border px-3.5 py-2 text-[0.8125rem] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${estilos} ${resto.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function Campo({
  rotulo, ajuda, erro, id, ...resto
}: React.InputHTMLAttributes<HTMLInputElement> & {
  rotulo: string;
  ajuda?: string;
  erro?: string;
}) {
  const idCampo = id ?? resto.name;
  return (
    <div className="space-y-1.5">
      <label htmlFor={idCampo} className="block text-[0.8125rem] font-medium text-[var(--color-tinta-2)]">
        {rotulo}
      </label>
      <input
        id={idCampo}
        {...resto}
        aria-invalid={erro ? true : undefined}
        aria-describedby={ajuda || erro ? `${idCampo}-ajuda` : undefined}
        className="w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem] text-[var(--color-tinta)] placeholder:text-[var(--color-tinta-3)]"
        style={erro ? { borderColor: "var(--color-bloqueado)" } : undefined}
      />
      {(ajuda || erro) && (
        <p
          id={`${idCampo}-ajuda`}
          className="text-[0.75rem]"
          style={{ color: erro ? "var(--color-bloqueado)" : "var(--color-tinta-3)" }}
        >
          {erro ?? ajuda}
        </p>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────── Avisos */

export function Aviso({
  children, tom = "neutro", titulo,
}: {
  children: ReactNode;
  tom?: "neutro" | "atencao" | "erro" | "sucesso";
  titulo?: string;
}) {
  const cores = {
    neutro: { cor: "var(--color-tinta-2)", fundo: "var(--color-superficie-2)", borda: "var(--color-borda)" },
    atencao: { cor: "var(--color-pendencia)", fundo: "var(--color-pendencia-fundo)", borda: "var(--color-pendencia-contorno)" },
    erro: { cor: "var(--color-bloqueado)", fundo: "var(--color-bloqueado-fundo)", borda: "var(--color-bloqueado-contorno)" },
    sucesso: { cor: "var(--color-apto)", fundo: "var(--color-apto-fundo)", borda: "var(--color-apto-contorno)" },
  }[tom];

  return (
    <div
      role={tom === "erro" ? "alert" : undefined}
      className="rounded-md border px-3.5 py-2.5 text-[0.8125rem] leading-relaxed"
      style={{ background: cores.fundo, borderColor: cores.borda, color: cores.cor }}
    >
      {titulo && <strong className="mb-0.5 block font-semibold">{titulo}</strong>}
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────── Métrica */

export function Metrica({
  rotulo, valor, detalhe, tom,
}: {
  rotulo: string;
  valor: ReactNode;
  detalhe?: ReactNode;
  tom?: string;
}) {
  return (
    <div>
      <dt className="text-[0.75rem] font-medium uppercase tracking-wide text-[var(--color-tinta-3)]">
        {rotulo}
      </dt>
      <dd
        className="mt-1 text-[1.375rem] font-semibold leading-tight tracking-tight"
        style={{ color: tom ?? "var(--color-tinta)" }}
      >
        {valor}
      </dd>
      {detalhe && <p className="mt-0.5 text-[0.75rem] text-[var(--color-tinta-3)]">{detalhe}</p>}
    </div>
  );
}
