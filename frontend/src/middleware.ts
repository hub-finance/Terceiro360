/** Guarda de rotas.
 *
 * Confere apenas a presença do cookie: quem valida o token é a API, e é ela
 * que decide o que cada perfil pode. O middleware só evita que a pessoa
 * chegue a uma tela que não teria como carregar.
 */
import { NextResponse, type NextRequest } from "next/server";

import { COOKIE_SESSAO } from "@/lib/sessao";

const PUBLICAS = ["/entrar", "/api/sessao"];

export function middleware(requisicao: NextRequest) {
  const { pathname } = requisicao.nextUrl;
  if (PUBLICAS.some((p) => pathname.startsWith(p))) return NextResponse.next();

  if (!requisicao.cookies.get(COOKIE_SESSAO)) {
    const destino = new URL("/entrar", requisicao.url);
    if (pathname !== "/") destino.searchParams.set("de", pathname);
    return NextResponse.redirect(destino);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|webp)$).*)"],
};
