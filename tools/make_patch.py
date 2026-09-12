#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera um patch compacto (só as diferenças) da Track 01 traduzida sobre a original.
   Formato próprio, aplicado por ao_patch_apply.py. Não distribui o jogo — só a tradução."""
import zlib, struct, os, hashlib

ORIG = r"X:\TRADUÇÂO\work\Albert Odyssey - Legend of Eldean (USA)\Albert Odyssey - Legend of Eldean (USA) (Track 01).bin"
NEW  = r"X:\TRADUÇÂO\work\build\Track01_full.bin"
OUT  = r"X:\TRADUÇÂO\work\build\AlbertOdyssey_PTBR.aopatch"

MAGIC = b'AOPT1\n'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def main():
    a=open(ORIG,'rb').read(); b=open(NEW,'rb').read()
    assert len(a)==len(b), f'tamanhos diferentes: {len(a)} vs {len(b)}'
    # coleta runs de bytes diferentes (mescla lacunas <= 16 p/ compactar)
    runs=[]; i=0; n=len(a); GAP=16
    while i<n:
        if a[i]!=b[i]:
            j=i+1; last=i
            while j<n:
                if a[j]!=b[j]: last=j; j+=1
                elif j-last<=GAP: j+=1
                else: break
            runs.append((i, b[i:last+1])); i=last+1
        else: i+=1
    # serializa: [MAGIC][sha_orig 32][filelen u64][nruns u32][ (off u64, len u32, bytes) ... ]
    body=bytearray()
    body+=struct.pack('>Q', n)
    body+=struct.pack('>I', len(runs))
    changed=0
    for off,data in runs:
        body+=struct.pack('>QI', off, len(data)); body+=data; changed+=len(data)
    comp=zlib.compress(bytes(body), 9)
    with open(OUT,'wb') as o:
        o.write(MAGIC)
        o.write(bytes.fromhex(sha(ORIG)))  # sha256 do ORIGINAL (p/ validar a cópia do usuário)
        o.write(bytes.fromhex(sha(NEW)))   # sha256 do RESULTADO esperado
        o.write(struct.pack('>I', len(comp)))
        o.write(comp)
    print(f'Patch gerado: {OUT}')
    print(f'  {len(runs)} blocos alterados, {changed} bytes ({changed/1e6:.1f} MB de diferença)')
    print(f'  tamanho do patch: {os.path.getsize(OUT)} bytes ({os.path.getsize(OUT)/1e6:.1f} MB)')
    print(f'  sha256 original : {sha(ORIG)[:16]}...')
    print(f'  sha256 traduzido: {sha(NEW)[:16]}...')

if __name__=='__main__':
    main()
