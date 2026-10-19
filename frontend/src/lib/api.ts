/** Cliente da API do TERCEIRO360.
 *
 * Roda apenas no servidor: o endereço da API e o token de sessão não chegam
 * ao navegador. Erros da API viram `ErroApi`, com a mensagem que o backend
 * escreveu — que é redigida para o usuário final, não para o log.
 */
import { headers as cabecalhosDoPedido } from "next/headers";

import { BASE_API as BASE } from "@/lib/endereco";
import { tokenDaSessao } from "@/lib/sessao";

/** O endereço de quem está no navegador, para repassar à API.
 *
 * Quem chama a API é este servidor, em nome de todos os usuários. Sem repassar
 * a origem, a API veria um endereço só — o do painel — e o freio de senha
 * errada contaria as tentativas de todos juntos: cinco erros de qualquer
 * pessoa travariam o login de todas. O intermediário do Render põe o endereço
 * real no início de X-Forwarded-For.
 */
async function origemDoNavegador(): Promise<Record<string, string>> {
  try {
    const cabecalhos = await cabecalhosDoPedido();
    const encaminhado = cabecalhos.get("x-forwarded-for")?.split(",")[0]?.trim();
    const endereco = encaminhado || cabecalhos.get("x-real-ip")?.trim();
    return endereco ? { "X-Forwarded-For": endereco } : {};
  } catch {
    // Fora de um pedido (não deveria acontecer aqui): segue sem a origem.
    return {};
  }
}

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
      ...(await origemDoNavegador()),
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
  // 502, 503 e 504 sem corpo não vêm da nossa API: vêm do intermediário do
  // Render, quando o servidor está acordando, reiniciando ou demorou demais.
  // "A API respondeu 502" não diz a ninguém o que fazer.
  if ([502, 503, 504].includes(resposta.status)) {
    return "O servidor não respondeu agora — ele pode estar iniciando. Tente de novo em alguns segundos.";
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
export class SegundoFatorExigido extends Error {
  constructor() {
    super("Informe o código do seu aplicativo autenticador.");
    this.name = "SegundoFatorExigido";
  }
}

export async function autenticar(
  email: string,
  senha: string,
  codigo?: string,
): Promise<{ access_token: string; expira_em_minutos: number }> {
  const corpo = new URLSearchParams({ username: email, password: senha });
  // O código vai no campo `client_secret` do formulário OAuth2 — é o campo
  // padrão disponível sem inventar um protocolo próprio para isto.
  if (codigo) corpo.set("client_secret", codigo);

  const resposta = await fetch(`${BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      ...(await origemDoNavegador()),
    },
    body: corpo,
    cache: "no-store",
  });

  if (!resposta.ok) {
    // A senha estava certa; falta o segundo fator. Distinguir os dois casos é
    // o que permite à tela pedir o código em vez de dizer "senha inválida".
    if (resposta.headers.get("x-mfa-exigido") === "1") throw new SegundoFatorExigido();
    if (resposta.status === 429) {
      // A mensagem da API, e não uma frase fixa. São duas causas diferentes —
      // senhas erradas demais, ou pedidos demais por minuto — com esperas
      // diferentes; dizer "15 minutos" para as duas mandou esperar à toa
      // quem só precisava de um minuto.
      throw new ErroApi(429, await mensagemDeErro(resposta));
    }
    throw new ErroApi(
      resposta.status,
      resposta.status === 401
        ? "E-mail ou senha inválidos."
        : "Não foi possível concluir a autenticação. Tente novamente.",
    );
  }
  return resposta.json();
}
