/** Download da cópia de segurança.
 *
 * Mesma ponte do download de documentos: o token vive num cookie httpOnly que
 * o JavaScript da página não alcança, então é o servidor do Next que chama a
 * API e devolve o arquivo. O token nunca aparece em URL nem em histórico.
 */
import { NextResponse } from "next/server";

import { BASE_API as BASE } from "@/lib/endereco";
import { tokenDaSessao } from "@/lib/sessao";

export async function GET() {
  const token = await tokenDaSessao();
  if (!token) return NextResponse.json({ erro: "Sessão expirada." }, { status: 401 });

  const resposta = await fetch(`${BASE}/api/v1/backup`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!resposta.ok) {
    const detalhe = await resposta.json().catch(() => null);
    return NextResponse.json(
      { erro: detalhe?.detail ?? "Não foi possível gerar a cópia." },
      { status: resposta.status },
    );
  }

  return new NextResponse(resposta.body, {
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": resposta.headers.get("content-disposition") ?? "attachment",
      // O arquivo leva dado pessoal decifrado: nada de cache no caminho.
      "Cache-Control": "no-store",
    },
  });
}
