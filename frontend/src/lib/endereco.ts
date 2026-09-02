/** Endereço da API, normalizado.
 *
 * No Render a variável `API_URL` é preenchida pelo próprio serviço da API
 * (`fromService` / `hostport`) e chega como "terceiro360-api:10000" — só host
 * e porta, sem esquema. `fetch` recusa uma URL assim, e o erro só apareceria
 * na primeira página que consultasse a API, já em produção. Completar o
 * esquema aqui, num lugar só, evita ter que lembrar disso a cada chamada.
 *
 * O esquema suprido é http porque a rede interna do Render não usa TLS: o
 * tráfego não sai da rede privada da conta. Se `API_URL` já vier com esquema
 * (é o caso em desenvolvimento), ele é respeitado como está.
 */
const bruto = process.env.API_URL ?? "http://localhost:8000";

export const BASE_API = (/^https?:\/\//.test(bruto) ? bruto : `http://${bruto}`)
  .replace(/\/+$/, "");
