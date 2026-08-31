/** Referências do estatuto para exibir ao lado das perguntas (§52). */
import { chamarApi } from "@/lib/api";
import type { ReferenciaEstatuto } from "@/componentes/questionario";

interface ParametroApi {
  chave: string;
  rotulo: string;
  valor: string | null;
  dispositivo: string | null;
  status: string;
}

export async function referenciasDoEstatuto(
  entidadeId: string,
): Promise<Record<string, ReferenciaEstatuto>> {
  const estatuto = await chamarApi<{ versoes: { id: string; vigente: boolean }[] }>(
    `/entidades/${entidadeId}/estatuto`,
  );
  const vigente = estatuto.versoes.find((v) => v.vigente) ?? estatuto.versoes[0];
  if (!vigente) return {};

  const parametros = await chamarApi<ParametroApi[]>(
    `/estatuto/versoes/${vigente.id}/parametros`,
  );
  return Object.fromEntries(
    parametros.map((p) => [
      p.chave,
      { valor: p.valor, status: p.status, rotulo: p.rotulo, dispositivo: p.dispositivo },
    ]),
  );
}
