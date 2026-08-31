"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Aviso, Botao, Campo } from "@/componentes/base";

export function FormularioEntrada({ destino }: { destino?: string }) {
  const router = useRouter();
  const [erro, definirErro] = useState<string | null>(null);
  const [enviando, definirEnviando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    definirErro(null);
    definirEnviando(true);

    const dados = new FormData(evento.currentTarget);
    try {
      const resposta = await fetch("/api/sessao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: dados.get("email"),
          senha: dados.get("senha"),
        }),
      });

      if (!resposta.ok) {
        const corpo = await resposta.json().catch(() => ({}));
        definirErro(corpo.erro ?? "Não foi possível entrar.");
        definirEnviando(false);
        return;
      }
      router.replace(destino ?? "/");
      router.refresh();
    } catch {
      definirErro("Falha de conexão. Verifique sua rede e tente novamente.");
      definirEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="mt-7 space-y-4" noValidate>
      {erro && <Aviso tom="erro">{erro}</Aviso>}

      <Campo
        rotulo="E-mail"
        name="email"
        type="email"
        autoComplete="username"
        required
        autoFocus
        placeholder="voce@escritorio.com.br"
      />
      <Campo
        rotulo="Senha"
        name="senha"
        type="password"
        autoComplete="current-password"
        required
        placeholder="••••••••"
      />

      <Botao tipo="submit" disabled={enviando} className="w-full">
        {enviando ? "Entrando…" : "Entrar"}
      </Botao>
    </form>
  );
}
