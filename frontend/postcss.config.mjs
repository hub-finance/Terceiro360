/** Sem este arquivo o `@import "tailwindcss"` do globals.css não é processado
 *  e o build sai com o CSS-base apenas: a aplicação inteira renderiza sem
 *  estilo, e nada no build acusa o erro. */
export default { plugins: { "@tailwindcss/postcss": {} } };
