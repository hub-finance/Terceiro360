/** Cliente da API do TERCEIRO360.
 *
 * Roda apenas no servidor: o endereço da API e o token de sessão não chegam
 * ao navegador. Erros da API viram `ErroApi`, com a mensagem que o backend
 * escreveu — que é redigida para o usuário final, não para o log.
 */
import { tokenDaSessao } from "@/lib/sessao";

const BASE = process.env.API_URL ?? "http://localhost:8000";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    mensagem: string,
    readonly corpo?: unknown,
  ) {
    super(mensagem);
    this.name = "ErroApi";
  }

  get naoAutenticado() {
    return this.status === 401;
  }
}

interface Opcoes extends Omit<RequestInit, "body"> {
  corpo?: unknown;
  /** Segundos de cache. 0 = sempre fresco (o padrão para dados de ato). */
  revalidar?: number;
}

export async function chamarApi<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const { corpo, revalidar = 0, headers, ...resto } = opcoes;
  const token = await tokenDaSessao();

  const resposta = await fetch(`${BASE}/api/v1${caminho}`, {
    ...resto,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(corpo !== undefined ? { body: JSON.stringify(corpo) } : {}),
    next: { revalidate: revalidar },
  });

  if (!resposta.ok) {
    throw new ErroApi(resposta.status, await mensagemDeErro(resposta), await corpoSeguro(resposta));
  }
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

async function mensagemDeErro(resposta: Response): Promise<string> {
  const dados = await corpoSeguro(resposta.clone());
  if (dados && typeof dados === "object" && "detail" in dados) {
    const detalhe = (dados as { detail: unknown }).detail;
    if (typeof detalhe === "string") return detalhe;
    if (detalhe && typeof detalhe === "object" && "mensagem" in detalhe) {
      return String((detalhe as { mensagem: unknown }).mensagem);
    }
    if (Array.isArray(detalhe) && detalhe.length > 0) {
      // Erro de validação do FastAPI: aponta o campo, não despeja o JSON.
      const primeiro = detalhe[0] as { loc?: unknown[]; msg?: string };
      const campo = Array.isArray(primeiro.loc) ? primeiro.loc.at(-1) : null;
      return campo ? `${campo}: ${primeiro.msg ?? "valor inválido"}` : String(primeiro.msg);
    }
  }
  return `A API respondeu ${resposta.status}.`;
}

async function corpoSeguro(resposta: Response): Promise<unknown> {
  try {
    return await resposta.json();
  } catch {
    return null;
  }
}

/** Autenticação: o único ponto que fala com a API sem token. */
export async function autenticar(
  email: string,
  senha: string,
): Promise<{ access_token: string; expira_em_minutos: number }> {
  const resposta = await fetch(`${BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password: senha }),
    cache: "no-store",
  });

  if (!resposta.ok) {
    throw new ErroApi(
      resposta.status,
      resposta.status === 401
        ? "E-mail ou senha inválidos."
        : "Não foi possível concluir a autenticação. Tente novamente.",
    );
  }
  return resposta.json();
}
