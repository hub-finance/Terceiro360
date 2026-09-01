import Link from "next/link";

import { Aviso, Cartao, Metrica } from "@/componentes/base";
import { ListaProtocolos } from "@/componentes/protocolos";
import { chamarApi } from "@/lib/api";
import type { Protocolo } from "@/lib/tipos";

export const metadata = { title: "Protocolos" };

export default async function PaginaProtocolos({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const caminho = `/entidades/${id}/protocolos`;
  const protocolos = await chamarApi<Protocolo[]>(`/entidades/${id}/protocolos`);

  const emExigencia = protocolos.filter((p) => p.status === "EM_EXIGENCIA");
  const registrados = protocolos.filter((p) => p.status === "REGISTRADO").length;
  const exigenciasAbertas = protocolos.reduce((soma, p) => soma + p.exigencias_abertas, 0);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Protocolos</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          O andamento de cada ato no Registro Civil de Pessoas Jurídicas: o que entrou,
          o que o oficial exigiu, o que já foi cumprido e o que voltou registrado.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="Protocolos" valor={protocolos.length} detalhe="no total" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Exigências abertas"
            valor={exigenciasAbertas}
            tom={exigenciasAbertas ? "var(--color-pendencia)" : undefined}
            detalhe="travando registro"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Registrados"
            valor={registrados}
            tom={registrados ? "var(--color-apto)" : undefined}
            detalhe="com certidão"
          />
        </Cartao>
      </div>

      {emExigencia.length > 0 && (
        <div className="mb-4">
          <Aviso tom="atencao" titulo="Há protocolo parado em exigência">
            Exigência tem prazo, e prazo perdido costuma significar reingressar do
            zero, pagando custas de novo. As que têm data informada entram na agenda
            e passam a alertar sozinhas.
          </Aviso>
        </div>
      )}

      <Cartao
        titulo="Andamento"
        descricao="Do protocolo ao registro"
        acao={
          <Link
            href={`/entidades/${id}/atos`}
            className="text-[0.8125rem] font-medium text-[var(--color-marca)] hover:underline"
          >
            Ver atos
          </Link>
        }
      >
        <ListaProtocolos protocolos={protocolos} caminho={caminho} />
      </Cartao>
    </div>
  );
}
