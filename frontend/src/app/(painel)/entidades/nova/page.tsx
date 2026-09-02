import Link from "next/link";

import { Aviso } from "@/componentes/base";
import { FormularioNovaEntidade } from "@/componentes/nova-entidade";

export const metadata = { title: "Nova entidade" };

export default function PaginaNovaEntidade() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Nova entidade</h1>
        <p className="mt-1 text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Serve tanto para uma entidade que já existe e você vai passar a
          acompanhar, quanto para uma que está sendo constituída agora.
        </p>
      </header>

      <div className="mb-7">
        <Aviso titulo="Começando do zero?">
          Cadastre a entidade com o nome pretendido e deixe CNPJ, endereço e data
          de constituição em branco. Depois, em <strong>Atos → Novo</strong>,
          escolha <strong>Constituição da Entidade</strong>: é ali que o sistema
          monta a ata de fundação e o estatuto inicial, e lista o que o cartório
          vai exigir no registro. Os campos que ficarem vazios aparecem como
          lacuna no documento — nunca preenchidos por suposição.
        </Aviso>
      </div>

      <FormularioNovaEntidade />

      <p className="mt-8 text-[0.8125rem] text-[var(--color-tinta-3)]">
        Em dúvida sobre o próximo passo depois do cadastro?{" "}
        <Link href="/ajuda" className="text-[var(--color-marca)] underline underline-offset-2">
          Veja a Ajuda
        </Link>
        .
      </p>
    </div>
  );
}
