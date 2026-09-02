# Guia "Como este sistema foi construído"

PDF de nove páginas, escrito para quem não programa: quais ferramentas foram
usadas, por que cada uma, onde o sistema mora, quanto custa e o que foi feito
de segurança. Serve como anexo comercial e como material de apresentação.

Para regerar depois de editar o texto:

```sh
cd backend
.venv/bin/python ../docs/guia/conteudo.py ../docs/guia \
  ../docs/guia/TERCEIRO360-como-foi-construido.pdf
```

`layout.py` tem a capa, os títulos e as caixas; `conteudo.py` tem o texto.
Usa a mesma biblioteca (fpdf2) que o sistema usa para exportar atas — o guia
é, ele próprio, uma demonstração do exportador.
