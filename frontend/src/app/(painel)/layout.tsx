import { redirect } from "next/navigation";

import { BarraEntidade } from "@/componentes/barra-entidade";
import { MenuLateral } from "@/componentes/navegacao";
import { ErroApi, chamarApi } from "@/lib/api";
import type { EntidadeResumo, Usuario } from "@/lib/tipos";

export default async function LayoutPainel({ children }: { children: React.ReactNode }) {
  let usuario: Usuario;
  let entidades: EntidadeResumo[];

  try {
    [usuario, entidades] = await Promise.all([
      chamarApi<Usuario>("/auth/eu"),
      chamarApi<EntidadeResumo[]>("/entidades"),
    ]);
  } catch (erro) {
    if (erro instanceof ErroApi && erro.naoAutenticado) redirect("/entrar");
    throw erro;
  }

  return (
    <div className="flex min-h-dvh">
      <MenuLateral entidades={entidades} usuario={usuario} />
      <main className="min-w-0 flex-1">
        <BarraEntidade entidades={entidades} />
        {children}
      </main>
    </div>
  );
}
