/** Abertura e encerramento de sessão.
 *
 * A senha é enviada do formulário para cá (servidor) e daqui para a API. O
 * token volta e é gravado num cookie httpOnly — nunca chega ao JavaScript da
 * página, o que o mantém fora do alcance de XSS.
 */
import { NextResponse } from "next/server";

import { ErroApi, SegundoFatorExigido, autenticar } from "@/lib/api";
import { COOKIE_SESSAO, opcoesCookie } from "@/lib/sessao";

export async function POST(requisicao: Request) {
  let email: string;
  let senha: string;
  let codigo: string | undefined;

  try {
    const corpo = await requisicao.json();
    email = String(corpo.email ?? "").trim().toLowerCase();
    senha = String(corpo.senha ?? "");
    codigo = corpo.codigo ? String(corpo.codigo).trim() : undefined;
  } catch {
    return NextResponse.json({ erro: "Requisição malformada." }, { status: 400 });
  }

  if (!email || !senha) {
    return NextResponse.json({ erro: "Informe e-mail e senha." }, { status: 400 });
  }

  try {
    const { access_token, expira_em_minutos } = await autenticar(email, senha, codigo);
    const resposta = NextResponse.json({ ok: true });
    resposta.cookies.set(COOKIE_SESSAO, access_token, opcoesCookie(expira_em_minutos * 60));
    return resposta;
  } catch (erro) {
    if (erro instanceof SegundoFatorExigido) {
      return NextResponse.json({ erro: erro.message, mfa: true }, { status: 401 });
    }
    if (erro instanceof ErroApi) {
      return NextResponse.json({ erro: erro.message }, { status: erro.status });
    }
    return NextResponse.json(
      { erro: "Não foi possível falar com o servidor. Verifique se a API está no ar." },
      { status: 503 },
    );
  }
}

export async function DELETE() {
  const resposta = NextResponse.json({ ok: true });
  resposta.cookies.set(COOKIE_SESSAO, "", opcoesCookie(0));
  return resposta;
}
