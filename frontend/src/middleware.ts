/** Guarda de rotas e política de conteúdo (§31).
 *
 * Duas responsabilidades que precisam rodar antes de qualquer página:
 *
 * 1. **Sessão** — confere só a presença do cookie. Quem valida o token é a
 *    API, e é ela que decide o que cada perfil pode; aqui só se evita que a
 *    pessoa chegue a uma tela que não teria como carregar.
 *
 * 2. **CSP com nonce por requisição** — a política precisa nascer aqui, e não
 *    no `next.config`, porque cada resposta tem o seu próprio nonce. É o que
 *    permite manter `script-src` fechado sem quebrar o Next: ele injeta script
 *    inline para hidratar a página, e um `'self'` seco bloqueia esse script —
 *    a tela renderiza mas nada funciona, e nenhum erro aparece no servidor.
 */
import { NextResponse, type NextRequest } from "next/server";

import { COOKIE_SESSAO } from "@/lib/sessao";

const PUBLICAS = ["/entrar", "/api/sessao"];
const producao = process.env.NODE_ENV === "production";

function politica(nonce: string): string {
  return [
    "default-src 'self'",
    // `strict-dynamic` deixa o script já autorizado carregar os seus próprios
    // pedaços, sem precisar listar cada arquivo do Next. Em desenvolvimento o
    // recarregamento a quente exige `eval`, que em produção fica de fora.
    producao
      ? `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`
      : `script-src 'self' 'unsafe-eval' 'unsafe-inline'`,
    // `'unsafe-inline'` só no estilo: o Next injeta CSS crítico no HTML e não
    // há como evitar. Estilo não executa código — risco muito menor.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    // A página nunca fala com a API direto, sempre pelo servidor Next. Então
    // mandar dado para fora — objetivo de quase todo XSS — esbarra aqui.
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    producao ? "upgrade-insecure-requests" : "",
  ]
    .filter(Boolean)
    .join("; ");
}

export function middleware(requisicao: NextRequest) {
  const { pathname } = requisicao.nextUrl;

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = politica(nonce);

  // O Next lê o nonce do cabeçalho da *requisição* e o aplica sozinho aos
  // scripts que injeta. Sem repassar aqui, o nonce da resposta não bateria com
  // o do script e a página ficaria inerte.
  const cabecalhos = new Headers(requisicao.headers);
  cabecalhos.set("x-nonce", nonce);
  cabecalhos.set("Content-Security-Policy", csp);

  const publica = PUBLICAS.some((p) => pathname.startsWith(p));
  if (!publica && !requisicao.cookies.get(COOKIE_SESSAO)) {
    const destino = new URL("/entrar", requisicao.url);
    if (pathname !== "/") destino.searchParams.set("de", pathname);
    const redirecionamento = NextResponse.redirect(destino);
    redirecionamento.headers.set("Content-Security-Policy", csp);
    return redirecionamento;
  }

  const resposta = NextResponse.next({ request: { headers: cabecalhos } });
  resposta.headers.set("Content-Security-Policy", csp);
  return resposta;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|webp)$).*)"],
};
