#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ao_iso.py — Remontagem/patch da imagem Sega Saturn (Track 01, MODE1/2352).

- Regenera EDC + ECC (P/Q) de setores Mode1 (algoritmo Neill Corlett / ECM).
- Faz patch IN-PLACE de arquivos dentro do .bin (2352/setor), preservando todo
  o resto byte-a-byte e recomputando a correção de erro só nos setores tocados.
- Parser ISO9660 para achar LBA/tamanho de cada arquivo.

Layout do setor Mode1 (2352 bytes):
  0x000..0x00B (12) sync
  0x00C..0x00F (4)  header (MSF em BCD + modo=01)
  0x010..0x80F (2048) dados de usuário
  0x810..0x813 (4)  EDC (little-endian)  [cobre 0x000..0x80F]
  0x814..0x81B (8)  zeros (intermediate)
  0x81C..0x8C7 (172) ECC P
  0x8C8..0x92F (104) ECC Q
"""
import struct, os, sys

RAW, USER, HDR = 2352, 2048, 16

# ---------- EDC / ECC (Corlett) ----------
_ecc_f = [0]*256
_ecc_b = [0]*256
_edc_lut = [0]*256

def _init():
    for i in range(256):
        j = (i << 1) ^ (0x11D if (i & 0x80) else 0)
        j &= 0xFF
        _ecc_f[i] = j
        _ecc_b[i ^ j] = i
        edc = i
        for _ in range(8):
            edc = (edc >> 1) ^ (0xD8018001 if (edc & 1) else 0)
        _edc_lut[i] = edc & 0xFFFFFFFF
_init()

def edc_compute(data):
    edc = 0
    for b in data:
        edc = (edc >> 8) ^ _edc_lut[(edc ^ b) & 0xFF]
    return edc & 0xFFFFFFFF

def _ecc_block(src, major_count, minor_count, major_mult, minor_inc, dest, doff):
    size = major_count * minor_count
    for major in range(major_count):
        idx = (major >> 1) * major_mult + (major & 1)
        ecc_a = 0; ecc_b = 0
        for _ in range(minor_count):
            temp = src[idx]
            idx += minor_inc
            if idx >= size: idx -= size
            ecc_a ^= temp; ecc_b ^= temp
            ecc_a = _ecc_f[ecc_a]
        ecc_a = _ecc_b[_ecc_f[ecc_a] ^ ecc_b]
        dest[doff + major] = ecc_a
        dest[doff + major + major_count] = (ecc_a ^ ecc_b) & 0xFF

def reconstruct_sector(sector, zeroaddress=False):
    """Recebe bytearray de 2352 com sync+header+dados corretos; regenera EDC+ECC."""
    s = sector
    # EDC sobre 0x000..0x80F
    edc = edc_compute(bytes(s[0:0x810]))
    struct.pack_into('<I', s, 0x810, edc)
    # intermediate zeros
    for k in range(0x814, 0x81C): s[k] = 0
    addr = bytes(s[12:16])
    if zeroaddress:
        for k in range(12, 16): s[k] = 0
    # P e Q operam sobre src = s[0x0C:]. IMPORTANTE: Q cobre a região que inclui a
    # paridade P, então usamos uma VIEW AO VIVO de s — assim, ao calcular Q, a P já
    # escrita em s é enxergada por src (senão Q fica errado em setores modificados).
    src = memoryview(s)[0x0C:]
    _ecc_block(src, 86, 24, 2, 86, s, 0x81C)   # P -> s[0x81C..]
    _ecc_block(src, 52, 43, 86, 88, s, 0x8C8)  # Q lê P atualizado via a view
    if zeroaddress:
        s[12:16] = addr
    return s

# ---------- Verificação contra o disco real ----------
def verify_ecc(bin_path, sample_step=97):
    """Confirma que reconstruct_sector reproduz EDC/ECC originais em setores Mode1."""
    size = os.path.getsize(bin_path)
    nsect = size // RAW
    ok = bad = skipped = 0
    firstbad = None
    with open(bin_path, 'rb') as f:
        for si in range(0, nsect, 1):
            if si % sample_step: continue  # amostra
            f.seek(si * RAW)
            raw = f.read(RAW)
            if len(raw) < RAW: break
            # só setores Mode1 (byte 0x0F == 0x01) com sync válido
            if raw[0x0F] != 0x01 or raw[1] != 0xFF:
                skipped += 1; continue
            orig = bytes(raw[0x810:0x930])  # EDC+inter+ECC
            rebuilt = reconstruct_sector(bytearray(raw))
            got = bytes(rebuilt[0x810:0x930])
            if got == orig:
                ok += 1
            else:
                bad += 1
                if firstbad is None:
                    firstbad = (si, orig[:8].hex(), got[:8].hex())
    return ok, bad, skipped, firstbad

# ---------- Parser ISO9660 (na imagem 2352) ----------
def _u32le(b): return struct.unpack('<I', b[:4])[0]

def read_user_sector(f, lba):
    f.seek(lba * RAW + HDR)
    return f.read(USER)

def read_range(f, lba, length):
    """Lê `length` bytes de dados de usuário a partir do LBA (atravessa setores)."""
    out = bytearray()
    need = length
    s = lba
    while need > 0:
        chunk = read_user_sector(f, s)
        take = min(USER, need)
        out += chunk[:take]
        need -= take
        s += 1
    return bytes(out)

def parse_iso(bin_path):
    """Retorna dict nome->(lba,size) lendo a imagem 2352 diretamente."""
    files = {}
    with open(bin_path, 'rb') as f:
        pvd = read_user_sector(f, 16)
        root = pvd[156:156+34]
        rlba = _u32le(root[2:10]); rsize = _u32le(root[10:18])
        seen = set()
        def walk(lba, size, path):
            if lba in seen: return
            seen.add(lba)
            data = read_range(f, lba, size)
            off = 0
            ents = []
            while off < len(data):
                rl = data[off]
                if rl == 0:
                    nx = ((off // USER) + 1) * USER
                    if nx >= len(data): break
                    off = nx; continue
                rec = data[off:off+rl]
                clba = _u32le(rec[2:10]); csize = _u32le(rec[10:18])
                flags = rec[25]; nl = rec[32]; nm = rec[33:33+nl]
                if nl == 1 and nm in (b'\x00', b'\x01'):
                    name = None
                else:
                    name = nm.decode('ascii', 'replace').split(';')[0]
                ents.append((name, clba, csize, bool(flags & 0x02)))
                off += rl
            for name, clba, csize, isdir in ents:
                if name is None: continue
                full = path + '/' + name
                if isdir: walk(clba, csize, full)
                else: files[full.lstrip('/')] = (clba, csize)
        walk(rlba, rsize, '')
    return files

def sectors_for(size):
    return (size + USER - 1) // USER

def patch_file(bin_in, bin_out, iso_name, new_data, verbose=True):
    """Escreve new_data no lugar de iso_name dentro do .bin, regenerando EDC/ECC.
       Exige len(new_data) <= tamanho original (modo in-place, sem realocação)."""
    files = parse_iso(bin_in)
    if iso_name not in files:
        # tenta match por basename
        cand = [k for k in files if k.split('/')[-1] == iso_name]
        if not cand: raise KeyError(f'{iso_name} não encontrado na ISO')
        iso_name = cand[0]
    lba, size = files[iso_name]
    if len(new_data) > size:
        raise ValueError(f'{iso_name}: novo tamanho {len(new_data)} > original {size} (precisa realocar)')
    padded = new_data + b'\x00' * (size - len(new_data))
    nsec = sectors_for(size)
    # copia o .bin e sobrescreve os setores do arquivo
    with open(bin_in, 'rb') as f:
        buf = bytearray(f.read())
    for k in range(nsec):
        si = lba + k
        base = si * RAW
        user = padded[k*USER:(k+1)*USER]
        if len(user) < USER: user = user + b'\x00'*(USER-len(user))
        buf[base+HDR:base+HDR+USER] = user
        reconstruct_sector(memoryview(buf)[base:base+RAW] if False else _slice_sector(buf, base))
    with open(bin_out, 'wb') as f:
        f.write(buf)
    if verbose:
        print(f'patch: {iso_name} lba={lba} size={size} -> {len(new_data)} bytes em {nsec} setores')
    return lba, size, nsec

def _slice_sector(buf, base):
    # reconstruct_sector precisa mutar buf; fazemos via bytearray view manual
    sec = bytearray(buf[base:base+RAW])
    reconstruct_sector(sec)
    buf[base:base+RAW] = sec
    return sec

if __name__ == '__main__':
    BIN = r"X:\TRADUÇÂO\work\Albert Odyssey - Legend of Eldean (USA)\Albert Odyssey - Legend of Eldean (USA) (Track 01).bin"
    print("=== Verificando implementação EDC/ECC contra o disco real (amostra) ===")
    ok, bad, skipped, firstbad = verify_ecc(BIN, sample_step=101)
    print(f"setores Mode1 OK: {ok} | divergentes: {bad} | pulados(non-mode1): {skipped}")
    if bad == 0 and ok > 0:
        print("RESULTADO: EDC/ECC CORRETO — regeneração idêntica ao disco original.")
    else:
        print(f"RESULTADO: FALHA. primeira divergência: {firstbad}")
        sys.exit(1)
