#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Condensação local DIRECIONADA e segura: aplica reduções naturais do PT-BR (na ordem
   da mais segura para a mais informal) apenas o necessário para o mapa caber.
   Nunca toca em tokens ⟦...⟧. Para em cada mapa assim que ele couber."""
import json, glob, re, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_twn, ao_codec

TRANS=r"X:\TRADUÇÂO\work\translation"
TOKEN=re.compile(r'⟦[^⟧]*⟧')

# reduções seguras/naturais do brasileiro, da mais neutra p/ a mais informal
REDUCTIONS = [
    (re.compile(r'  +'), ' '),
    (re.compile(r' ([,.!?;:])'), r'\1'),
    (re.compile(r'\bpara o\b'), 'pro'), (re.compile(r'\bpara a\b'), 'pra'),
    (re.compile(r'\bpara os\b'), 'pros'), (re.compile(r'\bpara as\b'), 'pras'),
    (re.compile(r'\bPara o\b'), 'Pro'), (re.compile(r'\bPara a\b'), 'Pra'),
    (re.compile(r'\bpara\b'), 'pra'), (re.compile(r'\bPara\b'), 'Pra'),
    (re.compile(r'\bestá\b'), 'tá'), (re.compile(r'\bEstá\b'), 'Tá'),
    (re.compile(r'\bestão\b'), 'tão'), (re.compile(r'\bestou\b'), 'tô'),
    # sinônimos curtos (neutros)
    (re.compile(r'\balguma coisa\b'), 'algo'), (re.compile(r'\bnenhuma coisa\b'), 'nada'),
    (re.compile(r'\bpor causa d'), 'por conta d'),
    (re.compile(r'\bagora mesmo\b'), 'já'), (re.compile(r'\bneste momento\b'), 'agora'),
    (re.compile(r'\bde verdade\b'), 'mesmo'),
    # último recurso: informal (registro casual de NPC)
    (re.compile(r'\bvocê\b'), 'cê'), (re.compile(r'\bvocês\b'), 'cês'),
]

def apply_seg(pt, rx, rep):
    """aplica uma redução preservando tokens."""
    out={}
    for k,v in pt.items():
        parts=re.split(r'(⟦[^⟧]*⟧)', v)
        parts=[p if p.startswith('⟦') else rx.sub(rep,p) for p in parts]
        out[k]=''.join(parts)
    return out

def fits(m, pt):
    b=open(rf'X:\TRADUÇÂO\work\files\{m}.TWN','rb').read()
    new,info=ao_twn.rebuild(b, {int(k):ao_codec.fold_accents(v) for k,v in pt.items()})
    return info['ok'], info.get('overflow',0)

def condense_map(m):
    pf=os.path.join(TRANS, f'pt_{m}.json')
    pt=json.load(open(pf,encoding='utf-8'))
    ok,_=fits(m,pt)
    if ok: return True, 0
    for rx,rep in REDUCTIONS:
        pt=apply_seg(pt, rx, rep)
        ok,ov=fits(m,pt)
        if ok:
            json.dump(pt, open(pf,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
            return True, 0
    # não coube nem com todas as reduções
    json.dump(pt, open(pf,'w',encoding='utf-8'), ensure_ascii=False, indent=1)  # salva o que reduziu
    return False, ov

if __name__=='__main__':
    maps=sys.argv[1:] or [os.path.basename(f)[3:-5] for f in glob.glob(os.path.join(TRANS,'pt_MAP*.json'))]
    still=[]
    for m in maps:
        ok,ov=condense_map(m)
        if not ok: still.append((m,ov))
        else: print(f'{m}: CABE agora ✓')
    if still:
        print('AINDA ESTOURAM (precisam de agente):', ', '.join(f'{m}(+{o})' for m,o in still))
        json.dump([{'map':m,'cut':o*2+80} for m,o in still], open(os.path.join(TRANS,'_fit_residual.json'),'w'))
    else:
        print('TODOS CABEM ✓')
