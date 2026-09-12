#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica traduções de work/translation/pt_MAP*.json ({idx: pt}) na Track01.
   Valida sequência de tokens ⟦...⟧ (pt deve ter os MESMOS tokens que en, na ordem).
   Reporta overflows (região cresceu) e mapas com token mismatch."""
import os, glob, json, re, sys, shutil
sys.path.insert(0, os.path.dirname(__file__))
import ao_twn, ao_codec, ao_iso

TRANS = r"X:\TRADUÇÂO\work\translation"
BIN_ORIG = r"X:\TRADUÇÂO\work\Albert Odyssey - Legend of Eldean (USA)\Albert Odyssey - Legend of Eldean (USA) (Track 01).bin"
TOKEN = re.compile(r'⟦[^⟧]*⟧')

def tokens(s): return TOKEN.findall(s)

def validate_map(mapname, ptmap):
    """Confere tokens pt vs en por unidade. Retorna lista de idx com mismatch."""
    j = json.load(open(os.path.join(TRANS, mapname.replace('.TWN','')+'.json'), encoding='utf-8'))
    bad=[]
    byidx={u['idx']:u for u in j['units']}
    for idx, pt in ptmap.items():
        idx=int(idx)
        if idx not in byidx: bad.append((idx,'idx inexistente')); continue
        en=byidx[idx]['en']
        if tokens(en)!=tokens(pt): bad.append((idx, f'tokens {tokens(en)} != {tokens(pt)}'))
    return bad

def apply(out_bin, verbose=True):
    shutil.copyfile(BIN_ORIG, out_bin)
    files = ao_iso.parse_iso(out_bin)
    stats={'ok':[], 'overflow':[], 'token_bad':[], 'units':0}
    ptfiles = sorted(glob.glob(os.path.join(TRANS, 'pt_MAP*.json')))
    for pf in ptfiles:
        mapname = os.path.basename(pf)[3:].replace('.json','')+'.TWN'
        ptmap = {int(k):v for k,v in json.load(open(pf,encoding='utf-8')).items()}
        bad = validate_map(mapname, ptmap)
        if bad:
            stats['token_bad'].append((mapname, bad[:5]))
            # aplica só as unidades com tokens corretos
            good_idx={u['idx'] for u in json.load(open(os.path.join(TRANS,mapname.replace('.TWN','')+'.json'),encoding='utf-8'))['units']
                      if tokens(next((v for k,v in ptmap.items() if int(k)==u['idx']),''))==tokens(u['en'])}
            ptmap={k:v for k,v in ptmap.items() if k in good_idx}
        iso_name=[k for k in files if k.split('/')[-1]==mapname]
        if not iso_name: continue
        iso_name=iso_name[0]; lba,size=files[iso_name]
        with open(out_bin,'rb') as f: orig=ao_iso.read_range(f,lba,size)
        tr={idx: ao_codec.fold_accents(pt) for idx,pt in ptmap.items()}
        try:
            new,info=ao_twn.rebuild(orig,tr)
        except Exception as e:
            stats['token_bad'].append((mapname, f'erro rebuild: {e}')); continue
        if not info.get('ok'):
            stats['overflow'].append((mapname, info['new_len']-info['region_cap']))
            continue
        ao_iso.patch_file(out_bin,out_bin,mapname,new,verbose=False)
        stats['ok'].append(mapname); stats['units']+=len(tr)
    if verbose:
        print(f"Mapas aplicados: {len(stats['ok'])} | unidades: {stats['units']}")
        if stats['overflow']:
            print(f"OVERFLOW ({len(stats['overflow'])}): "+', '.join(f'{m}(+{o})' for m,o in stats['overflow']))
        if stats['token_bad']:
            print(f"TOKEN MISMATCH ({len(stats['token_bad'])} mapas):")
            for m,b in stats['token_bad'][:10]: print(f"  {m}: {b}")
    return stats

if __name__=='__main__':
    out=sys.argv[1] if len(sys.argv)>1 else r"X:\TRADUÇÂO\work\build\Track01_pt.bin"
    os.makedirs(os.path.dirname(out),exist_ok=True)
    apply(out)
    print(f"\nISO: {out}")
