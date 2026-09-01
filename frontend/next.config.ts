import type { NextConfig } from "next";

const producao = process.env.NODE_ENV === "production";

// A Content-Security-Policy NÃO fica aqui: ela precisa de um nonce diferente a
// cada resposta, e `headers()` é estático. Ela é montada em `src/middleware.ts`.
const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Empacota só o necessário para rodar, sem node_modules inteiro: imagem
  // menor sobe mais rápido e carrega menos código para alguém explorar.
  output: "standalone",
  // O token de sessão vive em cookie httpOnly; nada de segredo chega ao bundle.
  env: {},
  // Não anunciar a versão do framework: é informação que só serve a quem
  // procura por uma falha conhecida daquela versão.
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
          // Só em produção: em localhost o HSTS gravaria "sempre HTTPS" no
          // navegador do programador, e nada mais abriria.
          ...(producao
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000; includeSubDomains",
                },
              ]
            : []),
        ],
      },
    ];
  },
};

export default nextConfig;
