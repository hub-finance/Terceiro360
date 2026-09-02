"""Gera o guia em PDF: como o TERCEIRO360 foi construído, para leigos."""
from fpdf import FPDF

MARCA = (28, 74, 94)
MARCA_CLARA = (232, 239, 242)
TINTA = (26, 29, 33)
TINTA_2 = (74, 80, 88)
TINTA_3 = (118, 125, 134)
BORDA = (226, 222, 215)
DESTAQUE = (156, 116, 0)

F = "/usr/share/fonts/truetype/liberation/"


class Guia(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.add_font("Sans", "", F + "LiberationSans-Regular.ttf")
        self.add_font("Sans", "B", F + "LiberationSans-Bold.ttf")
        self.add_font("Sans", "I", F + "LiberationSans-Italic.ttf")
        self.add_font("Serif", "B", F + "LiberationSerif-Bold.ttf")
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=22)
        self.capa_pronta = False

    def footer(self):
        # A capa não leva rodapé: ela é a página 1, e a numeração visível
        # começa na primeira página de conteúdo.
        if not self.capa_pronta or self.page_no() == 1:
            return
        self.set_y(-16)
        self.set_font("Sans", "", 8)
        self.set_text_color(*TINTA_3)
        self.cell(0, 5, "TERCEIRO360 - Como o sistema foi construído", align="L")
        self.cell(0, 5, str(self.page_no() - 1), align="R")


def capa(p):
    p.add_page()
    p.set_fill_color(*MARCA)
    p.rect(0, 0, 210, 120, "F")

    p.set_xy(20, 38)
    p.set_font("Serif", "B", 30)
    p.set_text_color(255, 255, 255)
    p.cell(0, 13, "TERCEIRO360")

    p.set_xy(20, 54)
    p.set_font("Sans", "", 13)
    p.set_text_color(200, 220, 230)
    p.multi_cell(150, 7, "Como este sistema foi construído")

    p.set_xy(20, 74)
    p.set_font("Sans", "", 10.5)
    p.set_text_color(180, 205, 218)
    p.multi_cell(
        150, 6,
        "Um guia sem jargão: quais ferramentas foram usadas, onde o sistema mora, "
        "quanto custa e por que cada escolha foi feita assim.",
    )

    p.set_xy(20, 140)
    p.set_font("Sans", "", 10)
    p.set_text_color(*TINTA_2)
    p.multi_cell(
        170, 6,
        "Se você nunca programou, este documento foi escrito para você. Cada ferramenta "
        "aparece com uma comparação do mundo real antes do nome técnico. Não é preciso ler "
        "na ordem: o índice abaixo leva direto ao que interessa.",
    )

    p.set_xy(20, 175)
    p.set_draw_color(*BORDA)
    p.set_line_width(0.3)
    p.line(20, 173, 190, 173)

    p.set_font("Sans", "B", 9.5)
    p.set_text_color(*MARCA)
    p.set_xy(20, 180)
    p.cell(0, 6, "NESTE GUIA")

    itens = [
        "1. O que o sistema faz, em um parágrafo",
        "2. As seis camadas, explicadas como uma casa",
        "3. As ferramentas, uma a uma",
        "4. Onde o sistema mora, hoje",
        "5. Quanto custa",
        "6. Segurança, sem jargão",
        "7. Vocabulário de bolso",
    ]
    y = 190
    p.set_font("Sans", "", 10)
    p.set_text_color(*TINTA_2)
    for item in itens:
        p.set_xy(24, y)
        p.cell(0, 6, item)
        y += 7

    p.set_xy(20, 262)
    p.set_font("Sans", "I", 8.5)
    p.set_text_color(*TINTA_3)
    p.multi_cell(170, 5, "Documento gerado pelo próprio sistema, com a mesma biblioteca "
                         "que ele usa para exportar atas e requerimentos em PDF.")
    p.capa_pronta = True


def titulo(p, numero, texto):
    if p.get_y() > 215:
        p.add_page()
    p.ln(4)
    p.set_font("Sans", "B", 8.5)
    p.set_text_color(*MARCA)
    p.cell(0, 5, numero.upper(), new_x="LMARGIN", new_y="NEXT")
    p.set_font("Serif", "B", 16)
    p.set_text_color(*TINTA)
    p.multi_cell(170, 8, texto)
    p.set_draw_color(*MARCA)
    p.set_line_width(0.8)
    y = p.get_y() + 1.5
    p.line(20, y, 42, y)
    p.ln(6)


def paragrafo(p, texto, tom=TINTA_2, tamanho=10):
    p.set_font("Sans", "", tamanho)
    p.set_text_color(*tom)
    p.multi_cell(170, 5.6, texto)
    p.ln(3)


def subtitulo(p, texto):
    if p.get_y() > 250:
        p.add_page()
    p.set_font("Sans", "B", 11)
    p.set_text_color(*TINTA)
    p.multi_cell(170, 6, texto)
    p.ln(1.5)


def caixa(p, rotulo, texto):
    p.set_font("Sans", "", 9.5)
    linhas = len(p.multi_cell(158, 5.2, texto, dry_run=True, output="LINES"))
    altura = linhas * 5.2 + 14
    if p.get_y() + altura > 265:
        p.add_page()
    y0 = p.get_y()
    p.set_fill_color(*MARCA_CLARA)
    p.rect(20, y0, 170, altura, "F")
    p.set_fill_color(*MARCA)
    p.rect(20, y0, 1.5, altura, "F")
    p.set_xy(26, y0 + 4)
    p.set_font("Sans", "B", 8.5)
    p.set_text_color(*MARCA)
    p.cell(0, 4.5, rotulo.upper(), new_x="LMARGIN", new_y="NEXT")
    p.set_xy(26, p.get_y() + 1)
    p.set_font("Sans", "", 9.5)
    p.set_text_color(*TINTA_2)
    p.multi_cell(158, 5.2, texto)
    p.set_y(y0 + altura + 5)


def ferramenta(p, nome, papel, analogia, porque, custo):
    bloco = [("O que é", analogia), ("Por que esta", porque), ("Custo hoje", custo)]
    p.set_font("Sans", "", 9.5)
    altura = 13
    for _, txt in bloco:
        altura += len(p.multi_cell(140, 5, txt, dry_run=True, output="LINES")) * 5 + 1.5
    if p.get_y() + altura > 262:
        p.add_page()

    y0 = p.get_y()
    p.set_draw_color(*BORDA)
    p.set_line_width(0.3)
    p.rect(20, y0, 170, altura)

    p.set_xy(25, y0 + 4)
    p.set_font("Sans", "B", 11.5)
    p.set_text_color(*MARCA)
    p.cell(60, 5, nome)
    p.set_font("Sans", "", 9)
    p.set_text_color(*TINTA_3)
    p.cell(0, 5, papel, align="R")

    y = y0 + 12
    for rotulo, txt in bloco:
        p.set_xy(25, y)
        p.set_font("Sans", "B", 8.5)
        p.set_text_color(*TINTA_3)
        p.cell(24, 5, rotulo)
        p.set_xy(49, y)
        p.set_font("Sans", "", 9.5)
        p.set_text_color(*TINTA_2)
        p.multi_cell(138, 5, txt)
        y = p.get_y() + 1.5

    p.set_y(y0 + altura + 4)


def lista(p, itens):
    p.set_font("Sans", "", 10)
    for item in itens:
        if p.get_y() > 258:
            p.add_page()
        y = p.get_y()
        p.set_fill_color(*MARCA)
        p.ellipse(22, y + 2.2, 1.4, 1.4, "F")
        p.set_xy(26, y)
        p.set_text_color(*TINTA_2)
        p.multi_cell(164, 5.6, item)
        p.ln(1.5)
    p.ln(2)
