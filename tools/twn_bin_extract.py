#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai as mensagens de ação (diálogo byte+0x1F) do TWN.BIN para tradução in-place.
   Cada mensagem: offset, texto decodificado, e comprimento MÁXIMO (até o terminador)."""
import os, json, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_codec

FILE = r"X:\TRADUÇÂO\work\files\TWN.BIN"
OUT  = r"X:\TRADUÇÂO\work\translation\system\TWN_BIN_dialogo.json"

def scan(b, minlen=8):
    """Acha mensagens: run de texto+controle terminada por 0xFA/0xFD."""
    msgs=[]; i=0; n=len(b)
    while i<n:
        if 0x01<=b[i]<=0x5F or b[i] in (0x40,0xF5,0xF9):
            j=i; real=0
            while j<n and (0x01<=b[j]<=0x5F or b[j] in (0x40,0xF5,0xF6,0xF9,0xFB,0xFC,0xFE)):
                if 0x22<=b[j]<=0x5B: real+=1
                j+=1
            if j<n and b[j] in (0xFA,0xFD) and real>=minlen:
                msgs.append((i, j+1))  # inclui terminador
                i=j+1; continue
            i=max(j,i+1)
        else: i+=1
    return msgs

def main():
    b=open(FILE,'rb').read()
    msgs=scan(b)
    items=[]
    for s,e in msgs:
        text=ao_codec.decode(b[s:e], pretty=True)
        items.append({'off':f'{s:#x}','len':e-s,'en':text,'pt':''})
    json.dump({'file':'TWN.BIN','n':len(items),'items':items},
              open(OUT,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Extraídas {len(items)} mensagens de ação do TWN.BIN -> {OUT}')
    for it in items[:12]:
        print('  @' + it['off'] + ' (max ' + str(it['len']) + 'B): ' + it['en'][:70])

if __name__=='__main__':
    main()
