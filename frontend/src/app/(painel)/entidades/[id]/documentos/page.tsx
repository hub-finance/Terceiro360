import { Cartao, Metrica, Vazio } from "@/componentes/base";
import { ListaDocumentos } from "@/componentes/documentos";
import { chamarApi } from "@/lib/api";
import type { DocumentoResumo } from "@/lib/tipos";

export const metadata = { title: "Acervo documental" };

/** Agrupa por categoria porque é assim que se procura um documento: primeiro
 *  "onde isso estaria", depois qual dos três. */
const CATEGORIAS: Record<string, string> = {
  CONSTITUTIVO: "Constitutivos",
  DELIBERATIVO: "Deliberativos",
  REGISTRAL: "Registrais",
  CONTABIL: "Contábeis",
  FISCAL: "Fiscais",
  TRABALHISTA: "Trabalhistas",
  CONTRATUAL: "Contratuais",
  CERTIDAO: "Certidões",
  OUTRO: "Outros",
};

export default async function PaginaAcervo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const documentos = await chamarApi<DocumentoResumo[]>(`/entidades/${id}/documentos`);
  const base = `/entidades/${id}`;

  const porCategoria = new Map<string, DocumentoResumo[]>();
  for (const d of documentos) {
    const chave = d.categoria || "OUTRO";
    porCategoria.set(chave, [...(porCategoria.get(chave) ?? []), d]);
  }

  const registrados = documentos.filter((d) => d.status === "REGISTRADO").length;
  const aguardandoAssinatura = documentos.filter((d) => d.assinaturas_pendentes > 0).length;
  const emRascunho = documentos.filter((d) => d.status === "RASCUNHO" || d.status === "GERADO");

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Acervo documental</h1>
        <p className="mt-1 max-w-3xl text-[0.875rem] leading-relaxed text-[var(--color-tinta-3)]">
          Todo documento que o sistema gerou, na versão em que está e no ponto do
          caminho em que parou. Versão antiga não some: o que foi assinado continua
          acessível exatamente como foi assinado.
        </p>
      </header>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <Cartao>
          <Metrica rotulo="No acervo" valor={documentos.length} detalhe="documentos" />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Registrados"
            valor={registrados}
            tom={registrados ? "var(--color-apto)" : undefined}
            detalhe="com registro concluído"
          />
        </Cartao>
        <Cartao>
          <Metrica
            rotulo="Aguardando assinatura"
            valor={aguardandoAssinatura}
            tom={aguardandoAssinatura ? "var(--color-pendencia)" : undefined}
            detalhe="documentos parados"
          />
        </Cartao>
      </div>

      {emRascunho.length > 0 && (
        <Cartao
          titulo="Ainda não revisados"
          descricao="Gerados pelo sistema, sem passar por conferência humana"
          className="mb-4"
          denso
        >
          <ListaDocumentos documentos={emRascunho} base={base} />
        </Cartao>
      )}

      {documentos.length === 0 ? (
        <Cartao>
          <Vazio>
            Nenhum documento ainda. Eles aparecem aqui quando um ato é gerado.
          </Vazio>
        </Cartao>
      ) : (
        <div className="space-y-4">
          {[...porCategoria.entries()].map(([categoria, itens]) => (
            <Cartao
              key={categoria}
              titulo={CATEGORIAS[categoria] ?? categoria}
              descricao={`${itens.length} documento(s)`}
              denso
            >
              <ListaDocumentos documentos={itens} base={base} />
            </Cartao>
          ))}
        </div>
      )}
    </div>
  );
}
