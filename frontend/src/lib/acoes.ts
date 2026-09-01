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

/* ──────────────────────────────────────────────────────────── Atos */

export async function criarAto(
  entidadeId: string,
  tipo: string,
  dados: Record<string, unknown>,
): Promise<Resultado & { id?: string }> {
  try {
    const evento = await chamarApi<{ id: string }>(`/entidades/${entidadeId}/eventos`, {
      method: "POST",
      corpo: { tipo, dados, data_referencia: dados.data_ato ?? null },
    });
    revalidatePath(`/entidades/${entidadeId}/atos`);
    return { ok: true, id: evento.id };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao criar o ato." };
  }
}

export async function salvarRespostas(
  eventoId: string,
  respostas: Record<string, unknown>,
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/eventos/${eventoId}/respostas`, { method: "PUT", corpo: respostas });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao salvar." };
  }
}

export async function validarAto(eventoId: string, caminho: string): Promise<Resultado> {
  try {
    await chamarApi(`/eventos/${eventoId}/validar`, { method: "POST" });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao validar." };
  }
}

export async function gerarDocumentos(
  eventoId: string,
  caminho: string,
  forcar = false,
): Promise<Resultado & { gerados?: number; semModelo?: string[]; comLacunas?: string[] }> {
  try {
    const r = await chamarApi<{
      gerados: { tipo: string; titulo: string; lacunas: string[] }[];
      sem_modelo_cadastrado: string[];
    }>(`/eventos/${eventoId}/gerar-documentos${forcar ? "?forcar=true" : ""}`, {
      method: "POST",
    });
    revalidatePath(caminho);
    return {
      ok: true,
      gerados: r.gerados.length,
      // O que o ato previa mas não pôde ser gerado precisa aparecer: um
      // documento faltando em silêncio vira exigência no cartório.
      semModelo: r.sem_modelo_cadastrado,
      comLacunas: r.gerados.filter((g) => g.lacunas.length > 0).map((g) => g.titulo),
    };
  } catch (erro) {
    if (erro instanceof ErroApi && erro.status === 409) {
      return {
        ok: false,
        mensagem:
          "Existem inconsistências que impedem a geração. Resolva os pontos em vermelho, "
          + "ou gere assumindo a responsabilidade pela ressalva.",
      };
    }
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao gerar." };
  }
}

/* ────────────────────────────────────────── Central de Fontes Jurídicas */

export async function verificarVigilia(
  monitoramentoId: string,
  conteudo?: string,
): Promise<Resultado & { houveMudanca?: boolean; atualizacaoId?: string }> {
  try {
    const r = await chamarApi<{
      houve_mudanca: boolean;
      atualizacao_id?: string;
      erro?: string | null;
      diff?: string;
    }>(`/normativo/monitoramentos/${monitoramentoId}/verificar`, {
      method: "POST",
      corpo: conteudo ? { conteudo } : {},
    });
    revalidatePath("/fontes");
    return {
      ok: true,
      houveMudanca: r.houve_mudanca,
      atualizacaoId: r.atualizacao_id,
      // Falha de coleta não é "nada mudou": é conferência manual pendente.
      mensagem: r.erro ?? undefined,
    };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao verificar." };
  }
}

export async function publicarAtualizacao(
  atualizacaoId: string,
  dados: {
    texto_novo: string;
    vigente_desde: string;
    resumo?: string;
    dispositivos_alterados: string[];
    parecer_curadoria?: string;
  },
): Promise<Resultado & { impactos?: number }> {
  try {
    const r = await chamarApi<{ impactos: unknown[] }>(
      `/normativo/atualizacoes/${atualizacaoId}/publicar`,
      { method: "POST", corpo: dados },
    );
    revalidatePath("/fontes");
    return { ok: true, impactos: r.impactos.length };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao publicar." };
  }
}

export async function descartarAtualizacao(
  atualizacaoId: string,
  parecer: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/normativo/atualizacoes/${atualizacaoId}/descartar`, {
      method: "POST",
      corpo: { parecer },
    });
    revalidatePath("/fontes");
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao descartar." };
  }
}

export async function tratarImpacto(impactoId: string, dispensado = false): Promise<Resultado> {
  try {
    await chamarApi(`/normativo/impactos/${impactoId}/tratar?dispensado=${dispensado}`, {
      method: "POST",
    });
    revalidatePath("/fontes");
    return { ok: true };
  } catch (erro) {
    return { ok: false, mensagem: erro instanceof ErroApi ? erro.message : "Falha ao tratar." };
  }
}

/* ─────────────────────────────────── Acervo, protocolos e agenda (2.7 / 3) */

export async function mudarStatusDocumento(
  documentoId: string,
  status: string,
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/documentos/${documentoId}/status`, {
      method: "POST",
      corpo: { status },
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao mudar o status.",
    };
  }
}

export async function registrarAssinatura(
  assinaturaId: string,
  caminho: string,
  provedor?: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/assinaturas/${assinaturaId}/registrar`, {
      method: "POST",
      corpo: { provedor: provedor || null, evidencia: {} },
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao registrar a assinatura.",
    };
  }
}

export async function adicionarSignatario(
  documentoId: string,
  dados: { nome_signatario: string; papel?: string; exige_reconhecimento_firma?: boolean },
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/documentos/${documentoId}/assinaturas`, { method: "POST", corpo: dados });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao incluir o signatário.",
    };
  }
}

export async function lancarExigencia(
  protocoloId: string,
  dados: { descricao: string; prazo?: string | null },
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/protocolos/${protocoloId}/exigencias`, {
      method: "POST",
      corpo: { descricao: dados.descricao, prazo: dados.prazo || null },
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao lançar a exigência.",
    };
  }
}

export async function cumprirExigencia(
  protocoloId: string,
  indice: number,
  observacao: string,
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/protocolos/${protocoloId}/exigencias/${indice}/cumprir`, {
      method: "POST",
      corpo: { observacao: observacao || null },
    });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao dar baixa na exigência.",
    };
  }
}

export async function concluirRegistro(
  protocoloId: string,
  dados: { data_registro: string; numero_registro: string; livro?: string; folha?: string },
  caminho: string,
): Promise<Resultado> {
  try {
    await chamarApi(`/protocolos/${protocoloId}/registrar`, { method: "POST", corpo: dados });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao registrar.",
    };
  }
}

export async function resolverPendencia(pendenciaId: string, caminho: string): Promise<Resultado> {
  try {
    await chamarApi(`/pendencias/${pendenciaId}/resolver`, { method: "POST" });
    revalidatePath(caminho);
    return { ok: true };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao resolver a pendência.",
    };
  }
}

export async function rodarVarredura(
  tarefa: "vigilias" | "prazos",
  caminho: string,
): Promise<Resultado & { detalhe?: string }> {
  try {
    const r = await chamarApi<{ detalhe: string; resultado: string }>(
      `/agendador/executar/${tarefa}`,
      { method: "POST" },
    );
    revalidatePath(caminho);
    return { ok: true, detalhe: `${r.resultado}: ${r.detalhe}` };
  } catch (erro) {
    return {
      ok: false,
      mensagem: erro instanceof ErroApi ? erro.message : "Falha ao rodar a varredura.",
    };
  }
}
