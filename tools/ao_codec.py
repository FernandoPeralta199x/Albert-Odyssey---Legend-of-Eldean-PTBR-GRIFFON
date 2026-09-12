#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ao_codec.py — Codec reversível do texto de Albert Odyssey (Saturn, USA).

Regra base COMPROVADA: ASCII = byte + 0x1F  (faixa de texto: bytes 0x01..0x5F).
Todo byte fora dessa faixa (controle/desconhecido) é representado como token ⟦XX⟧
(delimitadores Unicode U+27E6/U+27E7, que nunca colidem com texto do jogo nem com
letras acentuadas do português).

Para o português, caracteres acentuados são mapeados para bytes livres via ACCENTS
(preenchido no Passo 3, quando os glifos forem adicionados à fonte). Enquanto ACCENTS
estiver vazio, o codec é um inverso EXATO para o texto original em inglês:
    encode(decode(x)) == x   para qualquer x.

Tokens "bonitos" opcionais (PRETTY) tornam o dump legível para tradução; a codificação
aceita tanto ⟦XX⟧ quanto os tokens bonitos.
"""

LB, RB = '\u27e6', '\u27e7'   # ⟦ ⟧

# Mapeamento de acentos PT-BR -> byte no arquivo. VAZIO até o Passo 3 (fonte).
# Ex. futuro: 'á': 0x60, 'ç': 0x61, ...  (bytes livres 0x60..0xF4)
ACCENTS = {}
ACCENTS_REV = {}  # byte -> char, preenchido junto

# PROVISÓRIO (até a fonte ter glifos acentuados): dobra acentos para ASCII base.
# A tradução é escrita com acentos corretos; ao inserir, folda para caber na fonte atual.
FOLD = {
    'á':'a','à':'a','â':'a','ã':'a','ä':'a','Á':'A','À':'A','Â':'A','Ã':'A','Ä':'A',
    'é':'e','ê':'e','è':'e','ë':'e','É':'E','Ê':'E','È':'E','Ë':'E',
    'í':'i','î':'i','ì':'i','ï':'i','Í':'I','Î':'I','Ì':'I','Ï':'I',
    'ó':'o','ô':'o','õ':'o','ò':'o','ö':'o','Ó':'O','Ô':'O','Õ':'O','Ò':'O','Ö':'O',
    'ú':'u','û':'u','ù':'u','ü':'u','Ú':'U','Û':'U','Ù':'U','Ü':'U',
    'ç':'c','Ç':'C','ñ':'n','Ñ':'N',
    '“':'"','”':'"','‘':"'",'’':"'",'–':'-','—':'-','…':'...','º':'o','ª':'a',
}

def fold_accents(s):
    return ''.join(FOLD.get(c, c) for c in s)

# Tokens legíveis para códigos de controle conhecidos (bidirecional).
PRETTY = {
    0x00: '⟦FIM0⟧',      # terminador nulo
    0xF5: '⟦CORPO⟧',     # início do corpo (após o nome do falante)
    0xF6: '⟦PAGINA⟧',    # quebra de página / "pressione botão"
    0xF9: '⟦/NOME⟧',     # fim da tag de nome do falante
    0xFA: '⟦FIM⟧',       # fim da mensagem
    0xFD: '⟦FIM2⟧',      # fim (variante)
}
# 0x40 dentro do texto decodifica para '_' (abre tag de nome). Mantemos como '_' literal
# porque é reversível (byte 0x40 -> chr 0x5F '_'); não precisa de token.
PRETTY_REV = {v: k for k, v in PRETTY.items()}


def decode(bs, pretty=True):
    out = []
    for b in bs:
        if pretty and b in PRETTY:
            out.append(PRETTY[b])
        elif 0x01 <= b <= 0x5F:
            out.append(chr(b + 0x1F))
        elif b in ACCENTS_REV:
            out.append(ACCENTS_REV[b])
        else:
            out.append(f'{LB}{b:02X}{RB}')
    return ''.join(out)


def encode(s):
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == LB:
            j = s.index(RB, i)
            tok = s[i:j+1]
            if tok in PRETTY_REV:
                out.append(PRETTY_REV[tok])
            else:
                out.append(int(s[i+1:j], 16))
            i = j + 1
            continue
        o = ord(c)
        if c in ACCENTS:
            out.append(ACCENTS[c])
        elif 0x20 <= o <= 0x7E:
            out.append(o - 0x1F)
        else:
            raise ValueError(f'caractere sem mapeamento: {c!r} (U+{o:04X}) em pos {i}')
        i += 1
    return bytes(out)


if __name__ == '__main__':
    import glob, os, sys
    files = sorted(glob.glob(r"X:\TRADUÇÂO\work\files\MAP*.TWN"))
    total = 0
    fails = 0
    worst = None
    for f in files:
        data = open(f, 'rb').read()
        # testa reversibilidade com e sem tokens bonitos
        for pretty in (True, False):
            rt = encode(decode(data, pretty=pretty))
            if rt != data:
                fails += 1
                # acha primeiro byte divergente
                k = next((i for i in range(min(len(rt), len(data))) if rt[i] != data[i]), -1)
                if worst is None:
                    worst = (os.path.basename(f), pretty, k, len(data), len(rt))
        total += 1
    print(f"Codec round-trip: {total} arquivos .TWN testados (pretty=True e False cada).")
    if fails == 0:
        print("RESULTADO: PERFEITO — encode(decode(x)) == x em 100% dos casos.")
    else:
        print(f"RESULTADO: {fails} falhas. Primeira divergência: {worst}")
        sys.exit(1)
