"use server";

/** Ações do servidor. Rodam no Next, falam com a API com o token da sessão. */
import { revalidatePath } from "next/cache";

import { ErroApi, chamarApi } from "@/lib/api";

export interface Resultado {
  ok: boolean;
  mensagem?: string;
}

export async function confirmarParametro(
  versaoId: string,
  chave: string,
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/estatuto/versoes/${versaoId}/parametros/${chave}/confirmar`, {
      method: "POST",
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao confirmar." };
  }
}

export async function gravarParametro(
  versaoId: string,
  parametro: {
    chave: string;
    valor: string;
    tipo_valor: string;
    dispositivo?: string;
    confirmado: boolean;
  },
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/estatuto/versoes/${versaoId}/parametros`, {
      method: "PUT",
      corpo: [parametro],
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao gravar." };
  }
}
