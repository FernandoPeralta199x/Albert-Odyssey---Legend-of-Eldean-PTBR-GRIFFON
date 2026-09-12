#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline do texto de sistema (menus/itens/magias/status): extrai as strings
   traduzíveis do catálogo de recon com offset e ESPAÇO máximo exatos, e faz
   reinserção in-place (tradução <= espaço, null-terminada, preservando padding/metadados)."""
import os, csv, json, re, sys, struct
sys.path.insert(0, os.path.dirname(__file__))
import ao_iso, ao_codec

FILES = r"X:\TRADUÇÂO\work\files"
CATALOG = r"X:\TRADUÇÂO\work\analysis\ascii_strings.csv"
OUT = r"X:\TRADUÇÂO\work\translation\system"
os.makedirs(OUT, exist_ok=True)

# nomes próprios a MANTER (não traduzir)
KEEP = {'PIKE','CIRRUS','LEOS','AMON','EKA','LAIA','FOLTE','GRYZZ','KIA','GUY','AINE',
        'VARETTA','BELNARD','RADORIA','CERAMIS','ALBERT','ARCUS','CALIBOS','NOVIA','GIGARL',
        'DECIMUS','KRISYUNA','BALAN','KORAS','SOPHIA','VLAG','ESTAN'}

def max_space(data, off, s_len):
    """espaço utilizável = comprimento + padding (0x00/0xFF) até o próximo byte de dados."""
    k=off+s_len
    while k<len(data) and data[k] in (0x00,0xff): k+=1
    return (k-off)  # inclui o texto + padding disponível

def extract():
    rows=[r for r in csv.DictReader(open(CATALOG,encoding='utf-8')) if r.get('traduzivel')=='sim']
    by_file={}
    for r in rows:
        fn=r['arquivo']; off=int(r['offset_hex'],16)
        p=os.path.join(FILES,fn)
        if not os.path.exists(p): continue
        data=open(p,'rb').read()
        # relê a string exata do arquivo no offset (pode ter byte de controle antes)
        # o offset do catálogo aponta p/ o início do texto imprimível
        j=off
        while j<len(data) and 0x20<=data[j]<0x7f: j+=1
        raw=data[off:j]
        try: en=raw.decode('ascii')
        except: continue
        if len(en)<1: continue
        sp=max_space(data, off, len(en))
        keep = en.strip() in KEEP or (len(en.strip())<=1)
        by_file.setdefault(fn,[]).append({
            'off':f'{off:#x}','en':en,'len':len(en),'space':sp,
            'keep':keep,'cat':r['categoria_provavel'],'pt':''
        })
    for fn,items in by_file.items():
        # dedup por offset
        seen=set(); uniq=[]
        for it in items:
            if it['off'] in seen: continue
            seen.add(it['off']); uniq.append(it)
        json.dump({'file':fn,'n':len(uniq),'items':uniq},
                  open(os.path.join(OUT,fn.replace('.','_')+'.json'),'w',encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print("Extraído texto de sistema:")
    for fn,items in by_file.items():
        tr=sum(1 for i in items if not i['keep'])
        print(f"  {fn}: {len(items)} strings ({tr} a traduzir)")
    return by_file

def patch(out_bin):
    """aplica as traduções pt_* dos system/*.json na ISO (in-place, <= space)."""
    import shutil, glob
    BIN=r"X:\TRADUÇÂO\work\Albert Odyssey - Legend of Eldean (USA)\Albert Odyssey - Legend of Eldean (USA) (Track 01).bin"
    if not os.path.exists(out_bin):
        shutil.copyfile(BIN, out_bin)
    files=ao_iso.parse_iso(out_bin)
    applied=0; toolong=[]
    for jf in glob.glob(os.path.join(OUT,'*.json')):
        d=json.load(open(jf,encoding='utf-8')); fn=d['file']
        items=d.get('items')
        if not items: continue
        iso=[k for k in files if k.split('/')[-1]==fn]
        if not iso: continue
        lba,size=files[iso[0]]
        with open(out_bin,'rb') as f: data=bytearray(ao_iso.read_range(f,lba,size))
        changed=False
        for it in items:
            pt=it.get('pt','').strip()
            if not pt or it['keep']: continue
            off=int(it['off'],16); sp=it['space']
            enc=ao_codec.fold_accents(pt).encode('ascii','replace')
            if len(enc)>sp-1:  # -1 p/ o null
                toolong.append((fn,it['off'],it['en'],pt,len(enc),sp)); enc=enc[:sp-1]
            # escreve pt + null + preserva resto do padding
            for i in range(sp): data[off+i]=0
            data[off:off+len(enc)]=enc
            changed=True
        if changed:
            ao_iso.patch_file(out_bin,out_bin,fn,bytes(data),verbose=False); applied+=1
    print(f"Arquivos de sistema patchados: {applied}")
    if toolong:
        print(f"AVISO: {len(toolong)} traduções cortadas (não coubiam):")
        for fn,o,en,pt,l,sp in toolong[:10]: print(f'  {fn}@{o}: {en!r}->{pt!r} ({l}>{sp-1})')

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='patch':
        patch(sys.argv[2] if len(sys.argv)>2 else r"X:\TRADUÇÂO\work\build\Track01_pt_fixed.bin")
    else:
        extract()
