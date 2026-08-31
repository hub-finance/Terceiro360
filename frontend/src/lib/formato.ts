/** Formatação em português do Brasil. */

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

function paraData(valor: string | Date | null | undefined): Date | null {
  if (!valor) return null;
  const data = typeof valor === "string" ? new Date(`${valor.slice(0, 10)}T12:00:00`) : valor;
  return Number.isNaN(data.getTime()) ? null : data;
}

export function dataBr(valor: string | Date | null | undefined): string {
  const data = paraData(valor);
  if (!data) return "—";
  return data.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function dataExtenso(valor: string | Date | null | undefined): string {
  const data = paraData(valor);
  if (!data) return "—";
  return `${data.getDate()} de ${MESES[data.getMonth()]} de ${data.getFullYear()}`;
}

/** "em 12 dias", "há 3 dias", "hoje" — o que importa num painel de prazos. */
export function prazoRelativo(dias: number): string {
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  if (dias === -1) return "ontem";
  if (dias > 0) return `em ${dias} dias`;
  return `há ${Math.abs(dias)} dias`;
}

export function tituloDoAto(tipo: string): string {
  return tipo
    .toLowerCase()
    .split("_")
    .map((p) => (p.length <= 2 ? p : p[0].toUpperCase() + p.slice(1)))
    .join(" ");
}

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter((p) => p.length > 2);
  if (partes.length === 0) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}
