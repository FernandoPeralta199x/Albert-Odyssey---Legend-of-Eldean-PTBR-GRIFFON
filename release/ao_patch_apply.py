#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicador do patch de tradução PT-BR de Albert Odyssey: Legend of Eldean (Saturn).
Aplica o patch sobre a SUA cópia original da Track 01, gerando a versão traduzida.

USO:
    python ao_patch_apply.py "Albert Odyssey ... (Track 01).bin"  [saida.bin]

Não contém o jogo — só a tradução. Você precisa da sua própria cópia original.
"""
import sys, os, zlib, struct, hashlib

MAGIC = b'AOPT1\n'
PATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AlbertOdyssey_PTBR.aopatch')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    if not os.path.exists(PATCH):
        print(f'ERRO: patch nao encontrado: {PATCH}'); sys.exit(1)
    pd = open(PATCH, 'rb').read()
    if pd[:len(MAGIC)] != MAGIC:
        print('ERRO: arquivo de patch invalido'); sys.exit(1)
    off = len(MAGIC)
    sha_orig = pd[off:off+32].hex(); off += 32
    sha_new  = pd[off:off+32].hex(); off += 32
    clen = struct.unpack('>I', pd[off:off+4])[0]; off += 4
    body = zlib.decompress(pd[off:off+clen])

    data = bytearray(open(src, 'rb').read())
    cur = sha(bytes(data))
    if cur != sha_orig:
        print('AVISO: a Track 01 fornecida NAO bate com a original esperada.')
        print(f'  esperado: {sha_orig[:24]}...')
        print(f'  o seu   : {cur[:24]}...')
        print('  Verifique se e a versao USA correta (Track 01, MODE1/2352).')
        r = input('  Aplicar mesmo assim? (s/N) ').strip().lower()
        if r != 's': sys.exit(1)

    p = 0
    flen = struct.unpack('>Q', body[p:p+8])[0]; p += 8
    if len(data) != flen:
        print(f'ERRO: tamanho da Track 01 diferente ({len(data)} != {flen})'); sys.exit(1)
    nruns = struct.unpack('>I', body[p:p+4])[0]; p += 4
    for _ in range(nruns):
        o, l = struct.unpack('>QI', body[p:p+12]); p += 12
        data[o:o+l] = body[p:p+l]; p += l

    result = bytes(data)
    if sha(result) != sha_new:
        print('ERRO: resultado nao confere com o esperado (patch corrompido?)'); sys.exit(1)

    if not dst:
        dst = src  # sobrescreve a Track 01 no lugar (a build ja usa esse nome)
    with open(dst, 'wb') as f:
        f.write(result)
    print('OK! Traducao PT-BR aplicada com sucesso.')
    print(f'  Arquivo: {dst}')
    print('  Agora e so abrir o .cue no emulador (Ymir, Mednafen...) com a BIOS do Saturn.')

if __name__ == '__main__':
    main()
