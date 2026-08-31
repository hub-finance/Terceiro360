/** Sessão do usuário.
 *
 * O token JWT vive num cookie httpOnly: nunca é lido por JavaScript do
 * navegador, o que o coloca fora do alcance de XSS. Só o servidor Next o
 * repassa para a API.
 */
import { cookies } from "next/headers";

export const COOKIE_SESSAO = "t360_sessao";

export async function tokenDaSessao(): Promise<string | null> {
  const armazem = await cookies();
  return armazem.get(COOKIE_SESSAO)?.value ?? null;
}

export function opcoesCookie(maxAgeSegundos: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: maxAgeSegundos,
  };
}
