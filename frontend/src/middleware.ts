/** Guarda de rotas e política de conteúdo (§31).
 *
 * Três responsabilidades que precisam rodar antes de qualquer página:
 *
 * 0. **Tranca do ambiente de testes** — quando `T360_SENHA_SITE` existe, nem
 *    a tela de login aparece sem a senha. É para o período em que o sistema
 *    está publicado mas ainda não é para ser visto: sem ela, qualquer pessoa
 *    que descubra o endereço chega ao formulário e pode tentar senhas.
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

/** Senha única que tranca o site inteiro. Vazia = sem tranca.
 *
 * Lida do ambiente a cada requisição, e não numa constante de módulo, porque
 * é assim que ela acompanha uma troca de valor no painel do Render sem exigir
 * nova construção da imagem. */
function senhaDoSite(): string {
  return process.env.T360_SENHA_SITE ?? "";
}

/** Comparação que não vaza o tamanho nem o prefixo pelo tempo gasto.
 *
 * Um `===` de string curto-circuita no primeiro caractere diferente. A
 * diferença é de nanossegundos, mas é mensurável através da rede com
 * repetição suficiente, e descobrir a senha caractere a caractere é um
 * ataque conhecido. Aqui todo caractere é sempre comparado. */
function iguaisEmTempoConstante(a: string, b: string): boolean {
  const tamanho = Math.max(a.length, b.length);
  let diferenca = a.length ^ b.length;
  for (let i = 0; i < tamanho; i++) {
    diferenca |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diferenca === 0;
}

/** Confere o cabeçalho `Authorization: Basic`. Qualquer usuário serve; o que
 *  vale é a senha. Pedir um nome de usuário que ninguém definiu só geraria
 *  dúvida na hora de digitar. */
function trancaLiberada(requisicao: NextRequest, senha: string): boolean {
  const cabecalho = requisicao.headers.get("authorization") ?? "";
  if (!cabecalho.toLowerCase().startsWith("basic ")) return false;
  try {
    const decodificado = atob(cabecalho.slice(6).trim());
    const separador = decodificado.indexOf(":");
    const informada = separador === -1 ? decodificado : decodificado.slice(separador + 1);
    return iguaisEmTempoConstante(informada, senha);
  } catch {
    // Base64 malformado é tentativa inválida, não erro do servidor.
    return false;
  }
}

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

  const senha = senhaDoSite();
  if (senha && !trancaLiberada(requisicao, senha)) {
    return new NextResponse("Acesso restrito.", {
      status: 401,
      headers: {
        // `realm` é o texto que o navegador mostra na caixa de senha.
        "WWW-Authenticate": 'Basic realm="TERCEIRO360 - ambiente de testes", charset="UTF-8"',
        "Content-Type": "text/plain; charset=utf-8",
        // Sem isto, um proxy ou a cache do navegador poderia guardar o 401 e
        // continuar recusando depois que a tranca for removida.
        "Cache-Control": "no-store",
      },
    });
  }

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
