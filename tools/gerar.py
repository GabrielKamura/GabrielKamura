#!/usr/bin/env python3
"""Gera os desenhos do README do perfil, nos temas claro e escuro.

    python3 tools/gerar.py                 # os fixos (topo, projetos, redes) em img/
    python3 tools/gerar.py --vivo <pasta>  # os vivos (números e cobrinha), com os dados do GitHub de agora

Os vivos são refeitos todo dia pelo .github/workflows/vivo.yml e vão pro ramo "vivo".
O texto vira contorno, porque fonte de fora não carrega dentro de imagem no GitHub.
Mexeu em texto, cor ou projeto: rode de novo. Precisa de: pip install fonttools brotli
"""
import json
import math
import os
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from icones import ICONES

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


def svg(alt, corpo, estilo='', larg=L):
    estilo = f'<style>{estilo}</style>' if estilo else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg}" height="{alt}" viewBox="0 0 {larg} {alt}">'
            f'{estilo}{corpo}</svg>\n')


# ---------- topo ----------

# o letreiro "eu faço ___": a palavra troca sozinha, mesmo com "Reduzir movimento" ligado (decisão do dono)
PALAVRAS = ['apps de Mac', 'extensões', 'jogos']

TROCA = ('.p{opacity:0;animation:troca 7.5s infinite}.p1{opacity:1}.p2{animation-delay:2.5s}.p3{animation-delay:5s}'
         '@keyframes troca{0%{opacity:0;transform:translateY(16px)}4%,31%{opacity:1;transform:none}'
         '35%,100%{opacity:0;transform:translateY(-16px)}}')


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
         '@keyframes pisca{0%,93%,100%{transform:none}96%{transform:scaleY(.1)}}')

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


# ---------- redes ----------

# arquivo, ícone (None = o Snip, que é a cara do site), texto, giro
REDES = [
    ('instagram', 'Instagram', '@gabriel_kamura', -3),
    ('linkedin', 'LinkedIn', 'gabrielkamura', 2),
    ('site', None, 'moneysniper.io', -2),
]


def rede(tema, icone, s, giro):
    """Figurinha solta, com ícone e texto. Cada uma é um link no README."""
    d, larg = texto(s, 28, 600)
    lado = 30 if icone else 46
    w, h = 20 + lado + 12 + larg + 24, 58
    if icone:
        desenho = f'<path transform="translate({-w / 2 + 20:.1f} -15) scale(1.25)" d="{ICONES[icone]}"/>'
    else:
        desenho = f'<g transform="translate({-w / 2 + 20 + lado / 2:.1f} 0) scale(.62) translate(-11 36.5)">{SNIP}</g>'
    sombra = TINTA if tema == 'claro' else PAPEL
    larg_total, alt = round(w + 26), h + 28
    corpo = (f'<g transform="translate({larg_total / 2} {alt / 2}) rotate({giro})">'
             f'<rect x="{-w / 2 + 4:.1f}" y="{-h / 2 + 4}" width="{w:.1f}" height="{h}" rx="14" fill="{sombra}"/>'
             f'<rect x="{-w / 2:.1f}" y="{-h / 2}" width="{w:.1f}" height="{h}" rx="14" fill="{OURO}" stroke="{TINTA}" stroke-width="{BORDA}"/>'
             f'{desenho}<path transform="translate({-w / 2 + 20 + lado + 12:.1f} 10)" d="{d}"/></g>')
    return svg(alt, corpo, larg=larg_total)


# ---------- desenhos vivos: dados do GitHub ----------

CONSULTA = """query($login: String!) { user(login: $login) {
  repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
    totalCount
    nodes {
      releases { totalCount }
      languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      defaultBranchRef { target { ... on Commit { history { totalCount } } } }
    }
  }
  contributionsCollection { contributionCalendar {
    weeks { contributionDays { contributionCount weekday } }
  } }
} }"""


def dados_do_github(login='GabrielKamura'):
    ficha = os.environ.get('GH_TOKEN') or subprocess.run(
        ['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
    pedido = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': CONSULTA, 'variables': {'login': login}}).encode(),
        headers={'Authorization': f'bearer {ficha}', 'User-Agent': 'perfil-github'})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        resposta = json.load(r)
    if resposta.get('errors'):
        raise SystemExit(f'O GitHub recusou a consulta: {resposta["errors"]}')
    return resposta['data']['user']


def milhar(n):
    return f'{n:,}'.replace(',', '.')


def plural(n, um, varios):
    return um if n == 1 else varios


# ---------- números e linguagens ----------

CORES_LINGUA = {'JavaScript': OURO, 'Swift': '#eb6834', 'CSS': '#7b6cff', 'HTML': '#dc2626', 'Python': '#2a78d6',
                'Shell': '#0ca30c', 'TypeScript': ROSA, 'C': '#6b7280'}
CORES_RESERVA = ['#fab219', '#ec835a', '#0ca30c', '#6b7280']


def numeros(dados, tema, hoje):
    repos = dados['repositories']
    commits = sum(((r['defaultBranchRef'] or {}).get('target') or {}).get('history', {}).get('totalCount', 0)
                  for r in repos['nodes'])
    versoes = sum(r['releases']['totalCount'] for r in repos['nodes'])
    contas = [(commits, plural(commits, 'commit', 'commits')),
              (repos['totalCount'], plural(repos['totalCount'], 'repositório público', 'repositórios públicos')),
              (versoes, plural(versoes, 'versão lançada', 'versões lançadas'))]

    y0 = 24
    corpo = ''
    for i, (n, rotulo) in enumerate(contas):
        x = 56 + i * 300
        d, _ = texto(milhar(n), 76, 600)
        corpo += f'<path transform="translate({x} {y0 + 96})" fill="{TINTA}" d="{d}"/>'
        d, _ = texto(rotulo, 25)
        corpo += f'<path transform="translate({x} {y0 + 132})" fill="{TINTA_2}" d="{d}"/>'
    corpo += f'<path d="M56 {y0 + 160}H944" stroke="#e7e4dc" stroke-width="2.5"/>'

    # do que os projetos são feitos: uma barra só, com a legenda embaixo
    bytes_por_lingua = Counter()
    for r in repos['nodes']:
        for e in r['languages']['edges']:
            bytes_por_lingua[e['node']['name']] += e['size']
    total = sum(bytes_por_lingua.values()) or 1
    linguas = [(nome, b / total) for nome, b in bytes_por_lingua.most_common(6) if b / total >= .005]
    reserva = iter(CORES_RESERVA * 2)
    cores = {nome: CORES_LINGUA.get(nome) or next(reserva) for nome, _ in linguas}

    bx, by, bl, ba = 56, y0 + 186, 888, 30
    if linguas:
        larguras = [max(10, f) for f in (f / sum(f for _, f in linguas) * bl for _, f in linguas)]
        larguras = [w * bl / sum(larguras) for w in larguras]
        corpo += f'<clipPath id="barra"><rect x="{bx}" y="{by}" width="{bl}" height="{ba}" rx="15"/></clipPath><g clip-path="url(#barra)">'
        x = bx
        for (nome, _), w in zip(linguas, larguras):
            corpo += f'<rect x="{x:.1f}" y="{by}" width="{w + 1:.1f}" height="{ba}" fill="{cores[nome]}"/>'
            if x > bx:
                corpo += f'<path d="M{x:.1f} {by}v{ba}" stroke="{TINTA}" stroke-width="3"/>'
            x += w
        corpo += f'</g><rect x="{bx}" y="{by}" width="{bl}" height="{ba}" rx="15" fill="none" stroke="{TINTA}" stroke-width="{BORDA}"/>'

    lx, ly = bx, by + ba + 46
    for nome, f in linguas:
        d1, w1 = texto(nome, 27, 600)
        d2, w2 = texto('menos de 1%' if f < .01 else f'{round(f * 100)}%', 27)
        icone = ICONES.get(nome)
        larg = 26 + 12 + (30 + 10 if icone else 0) + w1 + 9 + w2
        if lx > bx and lx + larg > bx + bl:
            lx, ly = bx, ly + 50
        corpo += (f'<rect x="{lx:.1f}" y="{ly - 13}" width="26" height="26" rx="7" fill="{cores[nome]}" '
                  f'stroke="{TINTA}" stroke-width="3"/>')
        x = lx + 38
        if icone:
            corpo += f'<path transform="translate({x:.1f} {ly - 15}) scale(1.25)" d="{icone}"/>'
            x += 40
        corpo += f'<path transform="translate({x:.1f} {ly + 9.5})" fill="{TINTA}" d="{d1}"/>'
        corpo += f'<path transform="translate({x + w1 + 9:.1f} {ly + 9.5})" fill="{TINTA_2}" d="{d2}"/>'
        lx += larg + 44

    alt = ly + 44 - y0
    corpo = folha(y0, alt, tema) + corpo + figurinha(f'atualizado em {hoje:%d/%m}', 954, y0 + 4)
    return svg(y0 + alt + 16, corpo)


# ---------- cobrinha ----------

NIVEIS = ['#ffe9a0', OURO, '#f5a623', '#eb6834']   # do dia mais fraco ao mais forte
VERDE = '#0ca30c'
GOMOS = 6
SEMANAS = 26    # 6 meses: com o ano inteiro os quadradinhos ficam miúdos demais pro traço da casa


def cobrinha(dados, tema, parado=None):
    """A cobrinha come os dias com contribuição, da esquerda pra direita, e some pela borda.
    parado = distância percorrida, pra tirar uma foto dela no meio do caminho."""
    semanas = dados['contributionsCollection']['contributionCalendar']['weeks'][-SEMANAS:]
    contagens = [dia['contributionCount'] for semana in semanas for dia in semana['contributionDays']]
    total, maior = sum(contagens), max(contagens + [1])
    y0 = 24
    passo = 888 / len(semanas)
    lado = passo - 5
    gx, gy = 56 + 2.5, y0 + 44
    alt = round(44 + 7 * passo - 5 + 38)
    raio = lado * .22

    def centro(col, lin):
        return gx + col * passo + lado / 2, gy + lin * passo + lado / 2

    alvos, cor_do_dia, vazios = {}, {}, ''
    for col, semana in enumerate(semanas):
        for dia in semana['contributionDays']:
            lin = dia['weekday']
            vazios += f'<rect x="{gx + col * passo:.1f}" y="{gy + lin * passo:.1f}" width="{lado:.1f}" height="{lado:.1f}" rx="{raio:.1f}"/>'
            if dia['contributionCount']:
                alvos.setdefault(col, []).append(lin)
                cor_do_dia[col, lin] = NIVEIS[math.ceil(4 * dia['contributionCount'] / maior) - 1]

    # caminho: entra pela esquerda, varre cada coluna que tem alvo e sai pela direita
    espaco = passo * .62
    lin = sorted(alvos[min(alvos)])[0] if alvos else 3
    pontos, chegada, andado = [(-40.0, centro(0, lin)[1])], {}, 0.0

    def ir(x, y):
        nonlocal andado
        ax, ay = pontos[-1]
        if (x, y) != (ax, ay):
            andado += abs(x - ax) + abs(y - ay)
            pontos.append((x, y))

    for col in sorted(alvos):
        linhas = sorted(alvos[col])
        if abs(lin - linhas[-1]) < abs(lin - linhas[0]):
            linhas.reverse()
        ir(*centro(col, lin))
        for lin in linhas:
            ir(*centro(col, lin))
            chegada[col, lin] = andado
    velocidade = 190
    ir(L + 40 + GOMOS * espaco + 2.2 * velocidade, pontos[-1][1])   # o trecho fora da tela é a pausa
    duracao = andado / velocidade
    if duracao > 40:
        duracao, velocidade = 40, andado / 40

    def ponto_em(dist):
        dist = max(0, min(dist, andado))
        for (ax, ay), (bx, by) in zip(pontos, pontos[1:]):
            trecho = abs(bx - ax) + abs(by - ay)
            if dist <= trecho:
                t = dist / trecho
                return ax + (bx - ax) * t, ay + (by - ay) * t, math.degrees(math.atan2(by - ay, bx - ax))
            dist -= trecho
        return pontos[-1] + (0,)

    cheios = ''
    for (col, lin), dist in chegada.items():
        if parado is not None and dist <= parado:
            continue
        f = dist / andado
        some = '' if parado is not None else (
            f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{f:.4f};{min(f + .003, 1):.4f};1" '
            f'dur="{duracao:.2f}s" repeatCount="indefinite"/>')
        cheios += (f'<rect x="{gx + col * passo:.1f}" y="{gy + lin * passo:.1f}" width="{lado:.1f}" height="{lado:.1f}" rx="{raio:.1f}" '
                   f'fill="{cor_do_dia[col, lin]}" stroke="{TINTA}" stroke-width="3">{some}</rect>')

    caminho = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pontos)
    bicho = ''
    for i in reversed(range(GOMOS)):
        r = lado * (.5 if i == 0 else .32 if i == GOMOS - 1 else .42)
        forma = f'<circle r="{r:.1f}" fill="{VERDE}" stroke="{TINTA}" stroke-width="3.2"/>'
        if i == 0:   # a cabeça olha pra direita: língua e olhos
            forma = (f'<path d="M{r - 2:.1f} 0h{r * .8:.1f}" stroke="{ROSA}" stroke-width="4.5" stroke-linecap="round"/>{forma}'
                     f'<g transform="scale({r / 8.6:.2f})"><circle cx="2.4" cy="-3.7" r="2.7" fill="#fff"/><circle cx="2.4" cy="3.7" r="2.7" fill="#fff"/>'
                     '<circle cx="3.3" cy="-3.7" r="1.4"/><circle cx="3.3" cy="3.7" r="1.4"/></g>')
        if parado is None:
            bicho += (f'<g>{forma}<animateMotion dur="{duracao:.2f}s" begin="{i * espaco / velocidade:.3f}s" '
                      f'repeatCount="indefinite" rotate="auto" path="{caminho}"/></g>')
        else:
            x, y, giro = ponto_em(parado - i * espaco)
            bicho += f'<g transform="translate({x:.1f} {y:.1f}) rotate({giro:.0f})">{forma}</g>'

    corpo = (folha(y0, alt, tema)
             + f'<g fill="#efebe1">{vazios}</g>{cheios}'
             + f'<clipPath id="dentro"><rect x="8" y="{y0 + 2}" width="{L - 26}" height="{alt - 4}" rx="22"/></clipPath>'
             + f'<g clip-path="url(#dentro)">{bicho}</g>'
             + figurinha(f'{milhar(total)} {plural(total, "contribuição", "contribuições")} em 6 meses', 954, y0 + 4))
    return svg(y0 + alt + 16, corpo)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--vivo':
        pasta = Path(sys.argv[2])
        pasta.mkdir(parents=True, exist_ok=True)
        dados = dados_do_github()
        hoje = datetime.now(timezone(timedelta(hours=-3)))   # horário de São Paulo
        for tema in SOMBRA:
            (pasta / f'numeros-{tema}.svg').write_text(numeros(dados, tema, hoje), encoding='utf-8')
            (pasta / f'cobrinha-{tema}.svg').write_text(cobrinha(dados, tema), encoding='utf-8')
    else:
        pasta = SAIDA
        pasta.mkdir(exist_ok=True)
        for tema in SOMBRA:
            (pasta / f'topo-{tema}.svg').write_text(topo(tema), encoding='utf-8')
            for arquivo, *resto in PROJETOS:
                (pasta / f'{arquivo}-{tema}.svg').write_text(cartao(tema, *resto), encoding='utf-8')
            for arquivo, *resto in REDES:
                (pasta / f'{arquivo}-{tema}.svg').write_text(rede(tema, *resto), encoding='utf-8')
    for f in sorted(pasta.glob('*.svg')):
        print(f'{f.name:28} {f.stat().st_size / 1024:5.1f} kB')


if __name__ == '__main__':
    main()
