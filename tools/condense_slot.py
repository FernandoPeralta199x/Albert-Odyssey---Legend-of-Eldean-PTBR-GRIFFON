#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Condensa mirando APENAS as falas do slot que estoura (lógica exata do rebuild).
   Aplica reduções seguras do PT-BR só nessas falas; se faltar pouco, encurta a fala
   mais longa do slot removendo redundância. Nunca toca em tokens ⟦...⟧."""
import json, re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_twn, ao_codec

TRANS=r"X:\TRADUÇÂO\work\translation"
RED=[(re.compile(r'  +'),' '),(re.compile(r' ([,.!?;:])'),r'\1'),
     (re.compile(r'\bpara o\b'),'pro'),(re.compile(r'\bpara a\b'),'pra'),
     (re.compile(r'\bpara os\b'),'pros'),(re.compile(r'\bpara as\b'),'pras'),
     (re.compile(r'\bpara\b'),'pra'),(re.compile(r'\bPara\b'),'Pra'),
     (re.compile(r'\bestá\b'),'tá'),(re.compile(r'\bEstá\b'),'Tá'),(re.compile(r'\bestão\b'),'tão'),
     (re.compile(r'\balguma coisa\b'),'algo'),(re.compile(r'\bagora mesmo\b'),'já'),
     (re.compile(r'\bvocê\b'),'cê'),(re.compile(r'\bvocês\b'),'cês'),
     (re.compile(r'\bum pouco\b'),'um tanto'),(re.compile(r'\btalvez\b'),'quiçá')]

def red_tokens(s, rx, rep):
    return ''.join(p if p.startswith('⟦') else rx.sub(rep,p) for p in re.split(r'(⟦[^⟧]*⟧)', s))

def fold(pt): return {int(k):ao_codec.fold_accents(v) for k,v in pt.items()}

def condense(m):
    pf=os.path.join(TRANS,f'pt_{m}.json')
    pt=json.load(open(pf,encoding='utf-8'))          # chaves string
    b=open(rf'X:\TRADUÇÂO\work\files\{m}.TWN','rb').read()
    for _ in range(200):
        slots=ao_twn.analyze_slots(b, fold(pt))
        overs=[(a,z,dfc,idxs) for a,z,dfc,idxs in slots if dfc>0]
        if not overs:
            json.dump(pt,open(pf,'w',encoding='utf-8'),ensure_ascii=False,indent=1); return True
        rs,rend,dfc,idxs=max(overs,key=lambda x:x[2])
        # tenta reduções seguras nas falas do slot
        changed=False
        for rx,rep in RED:
            for i in idxs:
                k=str(i)
                if k in pt:
                    nv=red_tokens(pt[k],rx,rep)
                    if nv!=pt[k]: pt[k]=nv; changed=True
            if changed:
                slots2=ao_twn.analyze_slots(b, fold(pt))
                if all(d<=0 for _,_,d,_ in slots2):
                    json.dump(pt,open(pf,'w',encoding='utf-8'),ensure_ascii=False,indent=1); return True
                break
        if changed: continue
        # sem mais reduções: encurta a fala mais longa do slot removendo a última palavra do corpo
        cand=sorted([str(i) for i in idxs if str(i) in pt], key=lambda k:-len(pt[k]))
        done=False
        for k in cand:
            v=pt[k]
            # separa corpo (após ⟦CORPO⟧) e remove a última palavra antes do terminador
            mobj=re.search(r'(⟦CORPO⟧)(.*?)(⟦(?:FIM|FIM2|PAGINA)⟧|$)', v, re.S)
            if mobj and len(mobj.group(2).split())>3:
                body=mobj.group(2).rstrip()
                body2=re.sub(r'[,;]?\s+\S+\s*$','',body)  # tira última palavra
                if body2 and body2!=body:
                    pt[k]=v[:mobj.start(2)]+body2+v[mobj.end(2):]; done=True; break
        if not done:
            json.dump(pt,open(pf,'w',encoding='utf-8'),ensure_ascii=False,indent=1); return False
    return False

if __name__=='__main__':
    for m in sys.argv[1:]:
        ok=condense(m)
        print(m + (': CABE' if ok else ': AINDA ESTOURA'))
