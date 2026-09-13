#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reinsere in-place as mensagens traduzidas do TWN.BIN (codificação byte+0x1F).
   Cada tradução é codificada, dobra acentos, e escrita no offset original (<= tamanho),
   com padding 0x00 após o terminador. Não move nada -> ponteiros permanecem válidos."""
import os, json, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_codec, ao_iso

JSON = r"X:\TRADUÇÂO\work\translation\system\TWN_BIN_dialogo.json"

def patch_twn_bytes():
    """Retorna os bytes do TWN.BIN com as traduções aplicadas in-place (ou None se nada)."""
    d = json.load(open(JSON, encoding='utf-8'))
    b = bytearray(open(r"X:\TRADUÇÂO\work\files\TWN.BIN", 'rb').read())
    applied=0; toolong=[]
    for it in d['items']:
        pt = it.get('pt','').strip()
        if not pt: continue
        off=int(it['off'],16); ln=it['len']
        try:
            enc = ao_codec.encode(ao_codec.fold_accents(pt))
        except Exception as e:
            toolong.append((it['off'], it['en'][:30], f'erro encode: {e}')); continue
        if len(enc) > ln:
            toolong.append((it['off'], it['en'][:30], f'{len(enc)}>{ln}')); continue
        b[off:off+len(enc)] = enc
        for k in range(off+len(enc), off+ln): b[k]=0   # padding
        applied+=1
    return bytes(b), applied, toolong

def apply_to_build(out_bin):
    new_twn, applied, toolong = patch_twn_bytes()
    ao_iso.patch_file(out_bin, out_bin, 'TWN.BIN', new_twn, verbose=False)
    print(f'TWN.BIN: {applied} mensagens reinseridas in-place')
    if toolong:
        print(f'  {len(toolong)} não couberam/erro:')
        for o,en,r in toolong[:12]: print(f'    @{o} {en!r}: {r}')
    return applied, toolong

if __name__=='__main__':
    out = sys.argv[1] if len(sys.argv)>1 else r"X:\TRADUÇÂO\work\build\Track01_full.bin"
    apply_to_build(out)
