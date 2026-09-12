#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai TODO o diálogo dos MAP*.TWN para arquivos JSON editáveis (EN -> PT).
   Cada unidade: idx, offset, speaker (se houver), en (com tokens ⟦..⟧), pt (vazio)."""
import os, glob, json, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_twn, ao_codec

OUT = r"X:\TRADUÇÂO\work\translation"
os.makedirs(OUT, exist_ok=True)

def split_speaker(text):
    """Nameplate = '_NOME⟦/NOME⟧⟦CORPO⟧corpo'. Retorna (speaker, body)."""
    m = re.match(r'^_([^⟦]*)⟦/NOME⟧⟦CORPO⟧(.*)$', text, re.S)
    if m:
        return m.group(1), m.group(2)
    return None, text

def main():
    files = sorted(glob.glob(r"X:\TRADUÇÂO\work\files\MAP*.TWN"))
    grand_units = 0
    grand_bytes = 0
    index = []
    for f in files:
        name = os.path.basename(f)
        b = open(f,'rb').read()
        # tenta tabela principal; se não achar, tenta min_len menor
        tables = ao_twn.find_tables(b)
        if not tables:
            tables = ao_twn.find_tables(b, min_len=2)
        if not tables:
            index.append({'map':name,'units':0,'note':'sem tabela de diálogo'})
            continue
        units = ao_twn.extract_units(b)
        entries = []
        for u in units:
            speaker, body = split_speaker(u['text'])
            entries.append({
                'idx': u['idx'],
                'off': f"{u['start']:#x}",
                'speaker': speaker,
                'en': u['text'],       # texto completo com tokens (para reinserção)
                'en_body': body,        # só o corpo, para facilitar tradução
                'pt': ''                # a preencher
            })
        grand_units += len(entries)
        grand_bytes += sum(len(ao_codec.encode(u['text'])) for u in units)
        out = {'map':name, 'n':len(entries), 'units':entries}
        with open(os.path.join(OUT, name.replace('.TWN','')+'.json'),'w',encoding='utf-8') as o:
            json.dump(out, o, ensure_ascii=False, indent=1)
        index.append({'map':name,'units':len(entries)})
    with open(os.path.join(OUT,'_index.json'),'w',encoding='utf-8') as o:
        json.dump({'total_units':grand_units,'total_bytes':grand_bytes,'maps':index}, o, ensure_ascii=False, indent=1)
    print(f"Extraído: {grand_units} unidades de diálogo, ~{grand_bytes} bytes, em {len([i for i in index if i.get('units')])} mapas.")
    print(f"Arquivos em {OUT}")
    nomap=[i['map'] for i in index if not i.get('units')]
    if nomap: print(f"Mapas sem diálogo detectado: {nomap}")

if __name__=='__main__':
    main()
