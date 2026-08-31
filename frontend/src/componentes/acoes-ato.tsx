"use client";

import { useState, useTransition } from "react";

import { Aviso, Botao } from "@/componentes/base";
import { gerarDocumentos, validarAto } from "@/lib/acoes";

interface ResultadoGeracao {
  ok: boolean;
  mensagem?: string;
  gerados?: number;
  semModelo?: string[];
  comLacunas?: string[];
}

export function AcoesAto({
  eventoId,
  caminho,
  podeGerar,
  bloqueado,
}: {
  eventoId: string;
  caminho: string;
  podeGerar: boolean;
  bloqueado: boolean;
}) {
  const [mensagem, definirMensagem] = useState<string | null>(null);
  const [tom, definirTom] = useState<"erro" | "sucesso" | "atencao">("sucesso");
  const [detalhes, definirDetalhes] = useState<string[]>([]);
  const [confirmandoForca, definirConfirmandoForca] = useState(false);
  const [pendente, iniciar] = useTransition();

  function executar(acao: () => Promise<ResultadoGeracao>, sucesso: string) {
    definirMensagem(null);
    definirDetalhes([]);
    iniciar(async () => {
      const r = await acao();
      if (!r.ok) {
        definirTom("erro");
        definirMensagem(r.mensagem ?? "Não foi possível concluir.");
        return;
      }
      definirConfirmandoForca(false);

      const avisos: string[] = [];
      if (r.semModelo?.length) {
        avisos.push(
          `Sem modelo cadastrado: ${r.semModelo
            .map((t) => t.replaceAll("_", " ").toLowerCase())
            .join(", ")}. Estes documentos o ato prevê, mas o sistema não tem como `
            + "produzir — cadastre o modelo ou junte-os manualmente ao protocolo.",
        );
      }
      if (r.comLacunas?.length) {
        avisos.push(
          `Com DADO NÃO INFORMADO no texto: ${r.comLacunas.join(", ")}. Reveja antes `
            + "de levar a assinatura.",
        );
      }

      definirTom(avisos.length ? "atencao" : "sucesso");
      definirMensagem(r.gerados !== undefined ? `${r.gerados} documento(s) gerado(s).` : sucesso);
      definirDetalhes(avisos);
    });
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Botao
          variante="secundario"
          disabled={pendente}
          onClick={() => executar(() => validarAto(eventoId, caminho), "Validação atualizada.")}
        >
          {pendente ? "Verificando…" : "Validar novamente"}
        </Botao>

        {!bloqueado && (
          <Botao
            disabled={pendente || !podeGerar}
            onClick={() =>
              executar(() => gerarDocumentos(eventoId, caminho), "Documentos gerados.")
            }
          >
            Gerar documentos
          </Botao>
        )}
      </div>

      {/* §13/§47 — o bloqueio não é uma parede intransponível, mas passar por
          ele é uma decisão que alguém assume, e fica registrada. */}
      {bloqueado && !confirmandoForca && (
        <Botao variante="silencioso" onClick={() => definirConfirmandoForca(true)}>
          Gerar assumindo a ressalva
        </Botao>
      )}

      {bloqueado && confirmandoForca && (
        <Aviso tom="erro" titulo="Gerar com inconsistência apontada?">
          O sistema identificou impedimento a este ato. Gerar assim é decisão sua, e
          fica registrada na versão do documento. Atos com vício desta natureza
          costumam gerar exigência no cartório ou anulação da deliberação.
          <div className="mt-2.5 flex flex-wrap gap-2">
            <Botao
              variante="perigo"
              disabled={pendente}
              onClick={() =>
                executar(
                  () => gerarDocumentos(eventoId, caminho, true),
                  "Documentos gerados com ressalva registrada.",
                )
              }
            >
              {pendente ? "Gerando…" : "Sim, assumo a responsabilidade"}
            </Botao>
            <Botao variante="silencioso" onClick={() => definirConfirmandoForca(false)}>
              Cancelar
            </Botao>
          </div>
        </Aviso>
      )}

      {mensagem && (
        <Aviso tom={tom}>
          {mensagem}
          {detalhes.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {detalhes.map((d) => (
                <li key={d} className="leading-snug">
                  {d}
                </li>
              ))}
            </ul>
          )}
        </Aviso>
      )}
    </div>
  );
}
