import Link from "next/link";
import { notFound } from "next/navigation";

import { Aviso, Cartao, Etiqueta } from "@/componentes/base";
import {
  BotoesDownload,
  EtiquetaStatus,
  PainelAssinaturas,
  TrilhaStatus,
} from "@/componentes/documentos";
import { ErroApi, chamarApi } from "@/lib/api";
import { dataBr } from "@/lib/formato";
import type { DocumentoDetalhado } from "@/lib/tipos";

export const metadata = { title: "Documento" };

export default async function PaginaDocumento({
  params,
}: {
  params: Promise<{ id: string; docId: string }>;
}) {
  const { id, docId } = await params;
  const caminho = `/entidades/${id}/documentos/${docId}`;

  let documento: DocumentoDetalhado;
  try {
    // `html=true` devolve as lacunas já marcadas, para o revisor não ter de
    // caçar "DADO NÃO INFORMADO" no meio de três páginas de texto.
    documento = await chamarApi<DocumentoDetalhado>(`/documentos/${docId}?html=true`);
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 404) notFound();
    throw erro;
  }

  const pendentes = documento.assinaturas.filter((a) => a.status === "PENDENTE");

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <Link
        href={`/entidades/${id}/documentos`}
        className="text-[0.8125rem] text-[var(--color-tinta-3)] hover:underline"
      >
        ← Acervo documental
      </Link>

      <header className="mb-6 mt-2 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight">{documento.titulo}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-[0.8125rem] text-[var(--color-tinta-3)]">
            <EtiquetaStatus status={documento.status} />
            <span>versão {documento.versao_atual}</span>
            {documento.versoes.length > 1 && (
              <span>· {documento.versoes.length} versões no histórico</span>
            )}
          </p>
        </div>
        <BotoesDownload documentoId={documento.id} />
      </header>

      {documento.lacunas.length > 0 && (
        <div className="mb-4">
          <Aviso tom="erro" titulo="Documento incompleto">
            {documento.lacunas.length} dado(s) não informado(s):{" "}
            {documento.lacunas.join(", ")}. O texto abaixo marca cada lacuna, e o
            arquivo exportado também — para que ninguém protocole sem perceber.
          </Aviso>
        </div>
      )}

      {pendentes.length > 0 && documento.status !== "RASCUNHO" && (
        <div className="mb-4">
          <Aviso tom="atencao">
            {pendentes.length} assinatura(s) ainda pendente(s). O documento não avança
            para assinado enquanto houver quem não assinou.
          </Aviso>
        </div>
      )}

      <div className="space-y-4">
        <Cartao titulo="Situação" descricao="Onde o documento está no caminho até o registro">
          <TrilhaStatus documento={documento} caminho={caminho} />
        </Cartao>

        <Cartao titulo="Teor" descricao="Como o documento saiu, com as lacunas marcadas">
          {documento.conteudo ? (
            <div
              className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap rounded-md border bg-[var(--color-superficie-2)] p-4 font-serif text-[0.875rem] leading-relaxed text-[var(--color-tinta)]"
              // O conteúdo vem da própria API, que marca as lacunas com <mark>.
              dangerouslySetInnerHTML={{ __html: documento.conteudo }}
            />
          ) : (
            <p className="py-4 text-center text-[0.8125rem] text-[var(--color-tinta-3)]">
              Este documento ainda não tem conteúdo gerado.
            </p>
          )}
        </Cartao>

        <Cartao
          titulo="Assinaturas"
          descricao="Quem precisa assinar e quem já assinou"
        >
          <PainelAssinaturas documento={documento} caminho={caminho} />
        </Cartao>

        {documento.fundamentos.length > 0 && (
          <Cartao titulo="Fundamentos" descricao="A base legal que o modelo declara">
            <ul className="flex flex-wrap gap-1.5">
              {documento.fundamentos.map((f) => (
                <li key={f}>
                  <Etiqueta>{f}</Etiqueta>
                </li>
              ))}
            </ul>
          </Cartao>
        )}

        <Cartao
          titulo="Histórico de versões"
          descricao="Versão antiga continua acessível, sempre (§20)"
          denso
        >
          <ul className="divide-y">
            {[...documento.versoes]
              .sort((a, b) => b.numero - a.numero)
              .map((v) => (
                <li
                  key={v.numero}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-2.5 text-[0.8125rem]"
                >
                  <span className="font-medium">v{v.numero}</span>
                  <span className="text-[var(--color-tinta-3)]">{dataBr(v.criado_em)}</span>
                  <span className="min-w-0 flex-1 truncate text-[var(--color-tinta-2)]">
                    {v.motivo ?? "—"}
                  </span>
                  {v.lacunas > 0 && (
                    <span
                      className="text-[0.75rem] font-medium"
                      style={{ color: "var(--color-bloqueado)" }}
                    >
                      {v.lacunas} lacuna(s)
                    </span>
                  )}
                  {v.numero === documento.versao_atual && <Etiqueta tom="marca">atual</Etiqueta>}
                </li>
              ))}
          </ul>
        </Cartao>
      </div>
    </div>
  );
}
