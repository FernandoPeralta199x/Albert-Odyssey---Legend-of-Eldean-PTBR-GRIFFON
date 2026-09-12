#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ao_twn.py — Extração e reinserção de diálogo dos arquivos MAP*.TWN.

Modelo (COMPROVADO): ponteiros u32 big-endian absolutos; file_offset = ptr - 0x260DFFF8.
Mensagens da tabela principal são contíguas (52/53 mapas). Reinserção reescreve a
região de diálogo inteira e recalcula TODOS os ponteiros (todas as tabelas) via mapa
de offsets antigo->novo, cobrindo também ponteiros que caem no meio de uma mensagem.
"""
import struct, os, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
import ao_codec

BASE = 0x260DFFF8
LOAD = 0x260E0000
TERMS = (0xFA, 0xFD)

def find_tables(b, min_len=6):
    starts = set(i+1 for i,c in enumerate(b) if c in TERMS)
    hdr_len = struct.unpack('>I', b[4:8])[0]
    def is_ptr(v):
        o=v-BASE
        return (LOAD<=v<LOAD+hdr_len) and (0<o<len(b)) and (o in starts)
    tables=[]; k=0
    while k<len(b)-4:
        if b[k]==0x26 and is_ptr(struct.unpack('>I',b[k:k+4])[0]):
            j=k; prev=-1; ptrs=[]
            while j<len(b)-4:
                v=struct.unpack('>I',b[j:j+4])[0]; o=v-BASE
                ok=(b[j]==0x26 and v>prev and LOAD<=v<LOAD+hdr_len and 0<o<len(b) and (o in starts or not ptrs))
                if not ok: break
                ptrs.append((j,v)); prev=v; j+=4
            if len(ptrs)>=min_len:
                tables.append((k,ptrs)); k=j; continue
            k+=4
        else:
            k+=4
    return tables  # [(table_off, [(ptr_pos, ptr_val), ...])]

def msg_end(b, off):
    e=off
    while e<len(b) and b[e] not in TERMS: e+=1
    return e  # posição do terminador (exclusivo)

def main_table(tables):
    return max(tables, key=lambda t: len(t[1])) if tables else None

def all_targets(b):
    """Todos os offsets de destino (message starts) de TODAS as tabelas de diálogo."""
    tables=find_tables(b)
    tgts=set()
    for _,ptrs in tables:
        for ppos,pval in ptrs:
            o=pval-BASE
            if 0<=o<len(b): tgts.add(o)
    return tables, sorted(tgts)

def layout_messages(b):
    """Mensagens top-level NÃO-sobrepostas (união de todas as tabelas).
       Ponteiros que caem no meio de uma mensagem (substring) são tratados por map_off.
       Retorna (offs_layout, R0, R1)."""
    tables, tgts = all_targets(b)
    if not tgts: return [], None, None
    R0=tgts[0]; layout=[]; cur=R0
    for o in tgts:
        if o < cur:      # dentro de uma mensagem já incluída -> substring
            continue
        layout.append(o)
        cur = msg_end(b,o)+1
    return layout, R0, cur   # cur = fim da última mensagem = R1

def extract_units(b):
    """Unidades de tradução (união de todas as tabelas): (idx, start, end_incl, text)."""
    layout, R0, R1 = layout_messages(b)
    units=[]
    for i,off in enumerate(layout):
        end_incl = msg_end(b, off)+1
        text = ao_codec.decode(b[off:end_incl], pretty=True)
        units.append({'idx':i, 'start':off, 'end':end_incl, 'text':text})
    return units

def analyze_slots(b, translations=None):
    """Retorna [(rs, re, deficit, [idx_das_msgs_no_slot])] usando a MESMA lógica do rebuild.
       deficit>0 = slot estoura. Considera gaps entre mensagens (como o rebuild)."""
    if translations is None: translations={}
    b=bytearray(b)
    tables=find_tables(b)
    if not tables: return []
    layout,R0,R1=layout_messages(b)
    fixed=sorted((ptrs[0][0], ptrs[-1][0]+4) for toff,ptrs in tables)
    A0=min(R0,fixed[0][0]); A1=max(R1,fixed[-1][1])
    slots=[]; cur=A0
    for t0,t1 in fixed:
        if t0>cur: slots.append((cur,t0))
        cur=max(cur,t1)
    if cur<A1: slots.append((cur,A1))
    def slot_of(o):
        for s in slots:
            if s[0]<=o<s[1]: return s
        return None
    off2idx={off:i for i,off in enumerate(layout)}
    msg_by_slot={s:[] for s in slots}
    for off in layout:
        s=slot_of(off)
        if s is not None: msg_by_slot[s].append(off)
    out=[]
    for s in slots:
        rs,re=s; used=0; cur=rs; idxs=[]
        for off in sorted(msg_by_slot[s]):
            if off>cur: used+=off-cur           # gap
            end=msg_end(b,off)+1; idx=off2idx[off]
            enc=ao_codec.encode(translations[idx]) if idx in translations else bytes(b[off:end])
            used+=len(enc); cur=end; idxs.append(idx)
        if cur<re: used+=re-cur                  # cauda
        out.append((rs,re,used-(re-rs),idxs))
    return out

def rebuild(b, translations=None):
    """Reescreve o diálogo traduzido e corrige ponteiros. idx = posição em layout_messages.
       MODELO CORRETO: as TABELAS ficam em posições FIXAS (o código do jogo as acessa por
       endereço absoluto). As mensagens são re-organizadas apenas DENTRO de cada 'slot'
       (espaço entre tabelas fixas). Cada slot deve caber no seu tamanho original."""
    if translations is None: translations={}
    orig=b
    b=bytearray(b)
    tables=find_tables(b)
    if not tables:
        return bytes(b), {'ok':False, 'reason':'sem tabela'}
    layout, R0, R1 = layout_messages(b)

    # spans FIXOS = as tabelas (não podem se mover)
    fixed = sorted((ptrs[0][0], ptrs[-1][0]+4) for toff,ptrs in tables)
    A0 = min(R0, fixed[0][0]); A1 = max(R1, fixed[-1][1])

    # slots = trechos de [A0,A1] NÃO ocupados por tabelas
    slots=[]; cur=A0
    for (t0,t1) in fixed:
        if t0>cur: slots.append((cur,t0))
        cur=max(cur,t1)
    if cur<A1: slots.append((cur,A1))

    def slot_of(o):
        for s in slots:
            if s[0]<=o<s[1]: return s
        return None

    off2idx={off:i for i,off in enumerate(layout)}
    msg_by_slot={s:[] for s in slots}
    for off in layout:
        s=slot_of(off)
        if s is not None: msg_by_slot[s].append(off)

    newb=bytearray(b)  # parte de cópia; sobrescreve os slots
    slot_local={}      # slot -> lista (old_start, old_end, new_start, new_len) das MENSAGENS
    overflow=0; worst=None
    for s in slots:
        rs,re=s; buf=bytearray(); local=[]; cur=rs
        for off in sorted(msg_by_slot[s]):
            if off>cur:                       # gap antes da mensagem -> copia verbatim
                buf+=bytes(b[cur:off])
            end=msg_end(b,off)+1
            idx=off2idx[off]
            enc = ao_codec.encode(translations[idx]) if idx in translations else bytes(b[off:end])
            local.append((off,end,rs+len(buf),len(enc)))
            buf+=enc
            cur=end
        if cur<re:                            # cauda do slot (até a próxima tabela) -> verbatim
            buf+=bytes(b[cur:re])
        slot_local[s]=local
        cap=re-rs
        if len(buf)>cap:
            over=len(buf)-cap; overflow+=over
            if worst is None or over>worst[1]: worst=(f'{rs:#x}',over)
            continue
        newb[rs:rs+len(buf)]=buf
        for k in range(rs+len(buf), re): newb[k]=0

    info={'A0':A0,'A1':A1,'n_slots':len(slots),'n_units':len(layout),
          'n_tables':len(tables),'overflow':overflow,'worst_slot':worst}
    if overflow>0:
        info['ok']=False; info['reason']=f'slot estourou (+{overflow} bytes)'
        # p/ medição estilo antigo:
        info['new_len']=0; info['region_cap']=0
        return bytes(orig), info

    def map_off(old):
        s=slot_of(old)
        if s is None: return old   # tabela/fora de slot -> posição fixa
        for (os_,oe,ns,nl) in slot_local[s]:
            if os_<=old<oe:
                return ns+min(old-os_, max(0,nl-1))
        return old

    fixed_ct=0
    for toff,ptrs in tables:
        for ppos,pval in ptrs:
            tgt=pval-BASE
            nt=map_off(tgt)
            struct.pack_into('>I', newb, ppos, nt+BASE)  # tabela fixa -> ppos inalterado
            fixed_ct+=1
    info['ok']=True; info['ptrs_fixed']=fixed_ct
    return bytes(newb), info

# ---------------- round-trip de identidade ----------------
if __name__=='__main__':
    files=sorted(glob.glob(r"X:\TRADUÇÂO\work\files\MAP*.TWN"))
    tot=0; ident=0; notable=0; fail=[]
    for f in files:
        b=open(f,'rb').read()
        tables=find_tables(b)
        if not tables:
            notable+=1; continue
        tot+=1
        out, info = rebuild(b, {})  # sem traduções -> deve ser idêntico
        if out==b:
            ident+=1
        else:
            # acha 1a divergência
            k=next((i for i in range(min(len(out),len(b))) if out[i]!=b[i]),-1)
            fail.append((os.path.basename(f), k, info))
    print(f"Round-trip identidade (rebuild sem traduções):")
    print(f"  mapas com tabela: {tot} | idênticos: {ident} | sem tabela: {notable}")
    if fail:
        print(f"  FALHAS: {len(fail)}")
        for nm,k,info in fail[:10]:
            print(f"    {nm}: 1a divergência @ {k:#x} | info={info}")
    else:
        print("  RESULTADO: PERFEITO — rebuild reproduz 100% dos mapas byte-a-byte.")
