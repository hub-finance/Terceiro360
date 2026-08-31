import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { FormularioEntrada } from "@/app/entrar/formulario";
import { Marca } from "@/componentes/marca";
import { tokenDaSessao } from "@/lib/sessao";

export const metadata: Metadata = { title: "Entrar" };

export default async function PaginaEntrar({
  searchParams,
}: {
  searchParams: Promise<{ de?: string }>;
}) {
  if (await tokenDaSessao()) redirect("/");
  const { de } = await searchParams;

  return (
    <main className="grid min-h-dvh lg:grid-cols-[1fr_minmax(420px,38%)]">
      {/* Painel de apresentação: some no celular, onde o formulário é o que importa. */}
      <aside className="hidden flex-col justify-between bg-[var(--color-marca)] p-12 text-white lg:flex">
        <Marca tamanho={34} comTexto={false} />
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Inteligência e automação para o Terceiro&nbsp;Setor.
          </h1>
          <p className="mt-5 text-[0.9375rem] leading-relaxed text-white/80">
            O sistema não apenas gera documentos. Ele lê o estatuto, confere o
            mandato, o quórum e o prazo de convocação, e diz o que impede o ato
            antes de você levá-lo ao cartório.
          </p>
          <ul className="mt-8 space-y-3 text-[0.875rem] text-white/75">
            {[
              ["Nada é presumido", "Falta informação? DADO NÃO INFORMADO, nunca um chute."],
              ["A lei não decide sozinha", "Lei + estatuto + regra do RCPJ competente."],
              ["A base legal envelhece", "Normas versionadas, com curadoria humana."],
            ].map(([titulo, texto]) => (
              <li key={titulo} className="flex gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/50" />
                <span>
                  <strong className="font-semibold text-white">{titulo}.</strong> {texto}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-[0.75rem] text-white/50">
          A automação auxilia na preparação e validação dos documentos, mas não
          substitui a análise profissional quando esta for necessária.
        </p>
      </aside>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden">
            <Marca tamanho={30} />
          </div>
          <h2 className="mt-8 text-xl font-semibold tracking-tight lg:mt-0">Entrar</h2>
          <p className="mt-1 text-[0.875rem] text-[var(--color-tinta-3)]">
            Acesse com as credenciais do seu escritório ou entidade.
          </p>
          <FormularioEntrada destino={de} />
        </div>
      </div>
    </main>
  );
}
