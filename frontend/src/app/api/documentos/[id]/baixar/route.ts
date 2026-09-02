/** Download de documento em DOCX ou PDF.
 *
 * O token da sessão está num cookie httpOnly — de propósito: o JavaScript da
 * página não o alcança, e portanto também não consegue chamar a API direto.
 * Esta rota é a ponte: o navegador pede aqui, o servidor Next repassa com o
 * token e devolve o arquivo. O token nunca aparece na URL nem no histórico.
 */
import { NextResponse } from "next/server";

import { BASE_API as BASE } from "@/lib/endereco";
import { tokenDaSessao } from "@/lib/sessao";

const FORMATOS = new Set(["docx", "pdf"]);

export async function GET(
  requisicao: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const formato = new URL(requisicao.url).searchParams.get("formato") ?? "docx";
  if (!FORMATOS.has(formato)) {
    return NextResponse.json({ erro: "Formato inválido." }, { status: 422 });
  }

  const token = await tokenDaSessao();
  if (!token) return NextResponse.json({ erro: "Sessão expirada." }, { status: 401 });

  const resposta = await fetch(
    `${BASE}/api/v1/documentos/${id}/exportar?formato=${formato}`,
    { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" },
  );

  if (!resposta.ok) {
    // A API redige a mensagem para o usuário final (documento sem conteúdo,
    // por exemplo). Repassar é melhor do que traduzir de novo aqui.
    const detalhe = await resposta.json().catch(() => null);
    return NextResponse.json(
      { erro: detalhe?.detail ?? "Não foi possível gerar o arquivo." },
      { status: resposta.status },
    );
  }

  return new NextResponse(resposta.body, {
    headers: {
      "Content-Type":
        resposta.headers.get("content-type") ?? "application/octet-stream",
      "Content-Disposition":
        resposta.headers.get("content-disposition") ?? "attachment",
      "Cache-Control": "no-store",
    },
  });
}
