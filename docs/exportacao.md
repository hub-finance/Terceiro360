# Exportação de documentos — DOCX e PDF

`GET /api/v1/documentos/{id}/exportar?formato=docx|pdf`, e pela tela em
**Acervo → documento → Baixar DOCX / Baixar PDF**.

## Uma estrutura, dois desenhistas

Os documentos são gerados como texto corrido com as convenções de uma peça
jurídica: cabeçalho com a qualificação da entidade, título em caixa alta, corpo
justificado, ordem do dia numerada, fecho de local e data, linhas de assinatura.

`classificar()` lê essas convenções **uma vez** e devolve os blocos já
tipados; o gerador de DOCX e o de PDF apenas desenham esse mesmo resultado. O
risco de o PDF sair diferente do arquivo editável não vem de haver dois
formatos — vem de haver duas leituras do documento. Aqui há uma só.

(Converter o DOCX com LibreOffice daria fidelidade ainda maior, ao preço de
exigir a suíte inteira instalada no servidor para exportar uma ata. Não
compensa.)

## Forma

A4, margens 3-2-3-2 cm, Times New Roman 12, entrelinha 1,5, corpo justificado
com recuo de 1,25 cm na primeira linha — o formato que o balcão espera receber.

No PDF, a fonte é a **Liberation Serif**, métricamente compatível com a Times
New Roman declarada no DOCX: os dois quebram linha no mesmo lugar. Sem nenhuma
fonte Unicode instalada, o gerador cai na Times embutida do PDF, que só conhece
latin-1, e troca travessão e aspas curvas por equivalentes ASCII — feio, mas
entrega o arquivo. A imagem do backend instala `fonts-liberation` para que esse
caminho não seja usado.

## Lacuna exportada continua gritando

`**DADO NÃO INFORMADO**` sai em **negrito e vermelho** nos dois formatos, e o
rodapé do arquivo abre com `DOCUMENTO INCOMPLETO — há dados não informados`.

Um documento incompleto que sai bonitinho é pior do que um que não sai: alguém
protocola sem perceber. O rodapé leva ainda a razão social, o título, o número
da versão e a ressalva de minuta sujeita a revisão de profissional habilitado —
documento jurídico circula por e-mail e chega ao cartório fora de contexto, e
quem recebe precisa saber, olhando só o papel, o que tem em mãos.

## Nome do arquivo

Sem acento, de propósito: `Ata-Eleicao-de-diretoria-v2.docx`. O nome viaja num
cabeçalho HTTP, por e-mail e por pendrive até o balcão, e cada etapa dessas tem
seu próprio jeito de estragar um "ç". O conteúdo é acentuado; o nome não
precisa ser.
