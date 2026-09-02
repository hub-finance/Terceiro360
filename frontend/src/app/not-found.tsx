import Link from "next/link";

/** Página de endereço inexistente.
 *
 * Sem este arquivo o Next mostra o 404 padrão dele: fundo branco, sem estilo,
 * em inglês. Quem esbarra num link velho conclui que o sistema quebrou.
 */
export const metadata = { title: "Página não encontrada" };

export default function NaoEncontrada() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-6 text-center">
      <p className="text-[0.8125rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
        Erro 404
      </p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight">
        Esta página não existe
      </h1>
      <p className="mt-2 max-w-md text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
        O endereço pode estar incompleto, ou o item que estava aqui pode ter sido
        removido. Nada foi perdido — volte ao painel e siga daqui.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center rounded-md bg-[var(--color-marca)] px-4 py-2 text-[0.8125rem] font-semibold text-white hover:bg-[var(--color-marca-forte)]"
      >
        Voltar ao painel
      </Link>
    </div>
  );
}
