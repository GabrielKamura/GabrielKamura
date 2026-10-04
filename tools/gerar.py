#!/usr/bin/env python3
"""Gera os desenhos do README do perfil (img/*.svg), nos temas claro e escuro.

O texto vira contorno, porque fonte de fora não carrega dentro de imagem no GitHub.
Mexeu em texto, cor ou projeto: rode de novo.

    pip install fonttools brotli
    python3 tools/gerar.py
"""
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / 'img'

TINTA, TINTA_2 = '#000', '#374151'
PAPEL, OURO, ROSA = '#fffdf8', '#ffd23f', '#ff9eb5'
L = 1000        # largura de todo desenho; no GitHub ele encolhe pra ~850 px
BORDA = 3.5     # vira ~3 px depois de encolher
SOMBRA = {'claro': TINTA, 'escuro': OURO}   # no tema escuro a sombra preta some, então vira ouro


# ---------- texto em contorno ----------

FONTES = {p: TTFont(RAIZ / 'tools' / 'fontes' / f'Fredoka-{p}.woff2') for p in (500, 600)}


def _pares(fonte):
    """Kerning do GPOS: {(glifo, glifo): ajuste}. Vale o primeiro subtable que cobre o par."""
    pares = {}
    gpos = fonte['GPOS'].table
    todos = fonte.getGlyphOrder()
    indices = sorted({i for r in gpos.FeatureList.FeatureRecord if r.FeatureTag == 'kern'
                      for i in r.Feature.LookupListIndex})
    for i in indices:
        lookup = gpos.LookupList.Lookup[i]
        for sub in lookup.SubTable:
            tipo = lookup.LookupType
            if tipo == 9:
                tipo, sub = sub.ExtensionLookupType, sub.ExtSubTable
            if tipo != 2:
                continue
            if sub.Format == 1:
                for g1, conjunto in zip(sub.Coverage.glyphs, sub.PairSet):
                    for r in conjunto.PairValueRecord:
                        pares.setdefault((g1, r.SecondGlyph), (r.Value1.XAdvance or 0) if r.Value1 else 0)
            else:
                c1, c2 = sub.ClassDef1.classDefs, sub.ClassDef2.classDefs
                for g1 in sub.Coverage.glyphs:
                    linha = sub.Class1Record[c1.get(g1, 0)].Class2Record
                    for g2 in todos:
                        v = linha[c2.get(g2, 0)].Value1
                        pares.setdefault((g1, g2), (v.XAdvance or 0) if v else 0)
    return pares


KERN = {p: _pares(f) for p, f in FONTES.items()}


def texto(s, tam, peso=500):
    """(d, largura) do texto, com o começo em x=0 e a linha de base em y=0."""
    fonte = FONTES[peso]
    glifos, cmap = fonte.getGlyphSet(), fonte.getBestCmap()
    esc = tam / fonte['head'].unitsPerEm
    caneta = SVGPathPen(glifos, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.'))
    x, anterior = 0, None
    for letra in s:
        if ord(letra) not in cmap:
            raise SystemExit(f'A Fredoka não tem o caractere "{letra}" (em "{s}").')
        g = cmap[ord(letra)]
        x += KERN[peso].get((anterior, g), 0)
        glifos[g].draw(TransformPen(caneta, (esc, 0, 0, -esc, x * esc, 0)))
        x += glifos[g].width
        anterior = g
    return caneta.getCommands(), x * esc


# ---------- peças da casa ----------

def folha(y, alt, tema, x=6, larg=L - 22, desloc=8, raio=24):
    """Cartão de papel: tinta grossa e sombra dura deslocada."""
    return (f'<rect x="{x + desloc}" y="{y + desloc}" width="{larg}" height="{alt}" rx="{raio}" fill="{SOMBRA[tema]}"/>'
            f'<rect x="{x}" y="{y}" width="{larg}" height="{alt}" rx="{raio}" fill="{PAPEL}" stroke="{TINTA}" stroke-width="{BORDA}"/>')


def figurinha(s, x_dir, cy, tam=23, giro=-3):
    """Figurinha torta de ouro, encostada pela direita em x_dir."""
    d, larg = texto(s, tam, 600)
    w, h = larg + 34, tam + 22
    return (f'<g transform="translate({x_dir - w / 2:.1f} {cy}) rotate({giro})">'
            f'<rect x="{-w / 2 + 3:.1f}" y="{-h / 2 + 3:.1f}" width="{w:.1f}" height="{h}" rx="12" fill="{TINTA}"/>'
            f'<rect x="{-w / 2:.1f}" y="{-h / 2:.1f}" width="{w:.1f}" height="{h}" rx="12" fill="{OURO}" stroke="{TINTA}" stroke-width="{BORDA}"/>'
            f'<path transform="translate({-larg / 2:.1f} {tam * .34:.1f})" fill="{TINTA}" d="{d}"/></g>')


def svg(alt, corpo, estilo=''):
    estilo = f'<style>{estilo}</style>' if estilo else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{alt}" viewBox="0 0 {L} {alt}">'
            f'{estilo}{corpo}</svg>\n')


# ---------- topo ----------

# o letreiro "eu faço ___": a palavra troca sozinha
PALAVRAS = ['apps de Mac', 'extensões', 'jogos']

TROCA = ('.p{opacity:0;animation:troca 7.5s infinite}.p1{opacity:1}.p2{animation-delay:2.5s}.p3{animation-delay:5s}'
         '@keyframes troca{0%{opacity:0;transform:translateY(16px)}4%,31%{opacity:1;transform:none}'
         '35%,100%{opacity:0;transform:translateY(-16px)}}'
         '@media (prefers-reduced-motion:reduce){.p{animation:none}}')


def topo(tema):
    y0, alt = 30, 296
    corpo = folha(y0, alt, tema)
    d, _ = texto('Gabriel Kamura', 124, 600)
    corpo += f'<path transform="translate(52 {y0 + 140})" fill="{TINTA}" d="{d}"/>'

    base = y0 + 236
    d, larg = texto('eu faço', 56)
    corpo += f'<path transform="translate(56 {base})" fill="{TINTA}" d="{d}"/>'
    x = 56 + larg + 24
    for i, palavra in enumerate(PALAVRAS, 1):
        d, w = texto(palavra, 56, 600)
        corpo += (f'<g class="p p{i}"><g transform="rotate(-1.5 {x:.1f} {base})">'
                  f'<rect x="{x + 4:.1f}" y="{base - 55}" width="{w + 40:.1f}" height="78" rx="15" fill="{TINTA}"/>'
                  f'<rect x="{x:.1f}" y="{base - 59}" width="{w + 40:.1f}" height="78" rx="15" fill="{OURO}" stroke="{TINTA}" stroke-width="{BORDA}"/>'
                  f'<path transform="translate({x + 20:.1f} {base})" fill="{TINTA}" d="{d}"/></g></g>')

    corpo += figurinha('18 anos, de São Paulo', 952, y0 + 6, tam=24)
    return svg(y0 + alt + 14, corpo, TROCA)


# ---------- cartões dos projetos ----------

PISCA = ('.o{transform-box:fill-box;transform-origin:center;animation:pisca 4.6s infinite}'
         '@keyframes pisca{0%,93%,100%{transform:none}96%{transform:scaleY(.1)}}'
         '@media (prefers-reduced-motion:reduce){.o{animation:none}}')

# a bateria do Kamurafy (geometria de ui/js/mascote.js), 260 x 200
BATERIA = (
    '<clipPath id="corpo"><rect x="24" y="40" width="176" height="128" rx="38"/></clipPath>'
    f'<rect x="192" y="82" width="28" height="44" rx="11" fill="{OURO}" stroke="{TINTA}" stroke-width="7"/>'
    '<rect x="24" y="40" width="176" height="128" rx="38" fill="#fff"/>'
    '<path clip-path="url(#corpo)" fill="#0ca30c" d="M24 128q22-9 44 0t44 0 44 0 44 0V170H24Z"/>'
    f'<rect x="24" y="40" width="176" height="128" rx="38" fill="none" stroke="{TINTA}" stroke-width="7"/>'
    '<g transform="translate(112 104) scale(1.2) translate(-112 -104)">'
    f'<ellipse cx="66" cy="113" rx="11.5" ry="7" fill="{ROSA}"/><ellipse cx="158" cy="113" rx="11.5" ry="7" fill="{ROSA}"/>'
    '<g class="o"><circle cx="88" cy="95" r="10.5"/><circle cx="136" cy="95" r="10.5"/>'
    '<circle cx="91.8" cy="91" r="3.7" fill="#fff"/><circle cx="139.8" cy="91" r="3.7" fill="#fff"/></g>'
    '<clipPath id="boca"><path d="M97 110Q112 134 127 110 112 115.5 97 110Z"/></clipPath>'
    f'<path d="M97 110Q112 134 127 110 112 115.5 97 110Z" stroke="{TINTA}" stroke-width="2.5" stroke-linejoin="round"/>'
    f'<ellipse cx="112" cy="120.5" rx="7" ry="3.6" fill="{ROSA}" clip-path="url(#boca)"/>'
    '</g>')

# a caixa com zíper do Kamurar, no traço da casa, 96 x 96
CAIXA = (
    '<clipPath id="caixa"><rect x="16" y="13" width="64" height="72" rx="10"/></clipPath>'
    '<rect x="16" y="13" width="64" height="72" rx="10" fill="#fff"/>'
    '<rect x="16" y="13" width="64" height="20" fill="#d9dcee" clip-path="url(#caixa)"/>'
    f'<path d="M16 33H80" stroke="{TINTA}" stroke-width="4"/>'
    + ''.join(f'<rect x="{36 if i % 2 else 48}" y="{38 + i * 7.6:.1f}" width="12" height="5.4" rx="2" fill="#4a3ae0"/>'
              for i in range(6))
    + f'<rect x="16" y="13" width="64" height="72" rx="10" fill="none" stroke="{TINTA}" stroke-width="5"/>'
    f'<rect x="41" y="20" width="14" height="25" rx="7" fill="#4a3ae0" stroke="{TINTA}" stroke-width="3"/>'
    '<rect x="45.5" y="32" width="5" height="7.5" rx="2.5" fill="#fff"/>')

# a raposa do Kamurafox (extension/icons/kamurafox.svg), 96 x 96
RAPOSA = (
    f'<path d="M15 5 37 27q11-4 22 0L81 5q7 22 3 38l8 11-17 6Q63 79 48 90 33 79 21 60L4 54l8-11Q8 27 15 5Z" fill="{OURO}"/>'
    '<path d="M19 15 31 28 20 33Q17 24 19 15ZM77 15 65 28l11 5q3-9 1-18Z"/>'
    '<path d="M4 54l17 6Q33 79 48 90 63 79 75 60l17-6Q72 49 61 59 48 47 35 59 24 49 4 54Z" fill="#fff"/>'
    f'<path d="M15 5 37 27q11-4 22 0L81 5q7 22 3 38l8 11-17 6Q63 79 48 90 33 79 21 60L4 54l8-11Q8 27 15 5Z" fill="none" stroke="{TINTA}" stroke-width="5" stroke-linejoin="round"/>'
    '<path class="o" d="M27 43q7-6 13 1-6 5-13-1ZM69 43q-7-6-13 1 6 5 13-1Z"/>'
    f'<circle cx="24" cy="57" r="4" fill="{ROSA}"/><circle cx="72" cy="57" r="4" fill="{ROSA}"/>'
    f'<path d="M42 68h12l-6 7Z" stroke="{TINTA}" stroke-width="2.5" stroke-linejoin="round"/>')

# o Snip do Money Sniper (favicon.svg do jogo), 80 x 80 a partir de (-29, -76)
SNIP = (
    f'<g stroke="{TINTA}" stroke-linejoin="round" stroke-linecap="round">'
    '<ellipse cx="20" cy="-30" rx="4.5" ry="6" fill="#fff" stroke-width="2.4"/>'
    '<ellipse cx="-2" cy="-34" rx="23" ry="22" fill="#fff" stroke-width="3"/>'
    '<path d="M14-44 27-41 20-37 29-33 18-32Z" stroke-width="2"/>'
    '<path d="M16-52Q36-61 47-52 36-46 20-45Z" fill="#dc2626" stroke-width="2.6"/>'
    '<path d="M-25-40C-26-66 22-68 21-41Q-2-46-25-40Z" fill="#dc2626" stroke-width="2.6"/>'
    '<path d="M-12-42.5Q-6-51 0-43.5Z" fill="#fff" stroke-width="1.8"/>'
    '<path d="M-20.5-40-11.5-39M4.5-40Q0-48-4.5-41" fill="none" stroke-width="3"/>'
    '<rect x="-24" y="-36" width="15" height="10" rx="3.5" stroke-width="2"/>'
    '<rect x="-6" y="-36" width="14" height="10" rx="3.5" stroke-width="2"/>'
    '<path d="M-9-32H-6M8-33 19-32" fill="none" stroke-width="2"/>'
    '<path d="M-20-34-17-30M-2-34 1-30" stroke="#fff" stroke-width="1.6"/>'
    '<path d="M-14.5-18Q-6.2-12.7 1.5-23.2" fill="none" stroke-width="2.8"/>'
    '<rect x="-5.2" y="-17.5" width="3" height="2.6" rx="1" fill="#fff" stroke-width="1.2"/></g>'
    '<circle cx="-2" cy="-60.5" r="2.6"/>')

# arquivo, nome, frase, figurinha, desenho, caixa do desenho (x y larg alt), largura no cartão, giro
PROJETOS = [
    ('kamurafy', 'Kamurafy', 'Cuida do seu Mac e, principalmente, da sua bateria.',
     'app de Mac', BATERIA, (20, 36, 204, 136), 132, -7),
    ('kamurar', 'Kamurar', 'Abre .rar, .zip e .7z no Mac e cria .zip e .7z com senha.',
     'app de Mac em obras', CAIXA, (13, 10, 70, 78), 96, 6),
    ('kamurafox', 'Kamurafox', 'Deixa o Claude Code dirigir o Firefox: clicar, digitar e ler.',
     'extensão do Firefox', RAPOSA, (1, 2, 94, 91), 118, -5),
    ('moneysniper', 'Money Sniper', 'Jogo de ritmo no navegador: acerte as notas na batida.',
     'jogue em moneysniper.io', SNIP, (-27, -64, 76, 55), 128, 5),
]


def cartao(tema, nome, frase, selo, desenho, caixa, larg_desenho, giro):
    y0, alt = 24, 164
    corpo = folha(y0, alt, tema)

    # o mascote do projeto, solto no papel
    cx, cy = 106, y0 + alt / 2
    bx, by, bl, ba = caixa
    esc = larg_desenho / bl
    corpo += (f'<g transform="translate({cx} {cy}) rotate({giro}) scale({esc:.3f}) '
              f'translate({-(bx + bl / 2):.1f} {-(by + ba / 2):.1f})">{desenho}</g>')

    d, _ = texto(nome, 54, 600)
    corpo += f'<path transform="translate(204 {y0 + 78})" fill="{TINTA}" d="{d}"/>'
    d, larg = texto(frase, 27)
    if 204 + larg > L - 46:
        raise SystemExit(f'Frase comprida demais pro cartão: "{frase}"')
    corpo += f'<path transform="translate(204 {y0 + 124})" fill="{TINTA_2}" d="{d}"/>'
    corpo += figurinha(selo, 954, y0 + 4)
    return svg(y0 + alt + 16, corpo, PISCA if 'class="o"' in desenho else '')


def main():
    SAIDA.mkdir(exist_ok=True)
    for tema in SOMBRA:
        (SAIDA / f'topo-{tema}.svg').write_text(topo(tema), encoding='utf-8')
        for arquivo, *resto in PROJETOS:
            (SAIDA / f'{arquivo}-{tema}.svg').write_text(cartao(tema, *resto), encoding='utf-8')
    for f in sorted(SAIDA.glob('*.svg')):
        print(f'{f.name:28} {f.stat().st_size / 1024:5.1f} kB')


if __name__ == '__main__':
    main()
