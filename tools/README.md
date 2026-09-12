# Ferramentas de tradução — Albert Odyssey (Saturn, USA)

Pipeline de reinserção **provado byte-a-byte** (Passo 1). Rodar com `PYTHONIOENCODING=utf-8`.

## Módulos
- **`ao_codec.py`** — codec reversível do texto. `ASCII = byte + 0x1F`; bytes de controle viram tokens `⟦..⟧`. `decode(bytes)→str`, `encode(str)→bytes`. Provado `encode(decode(x))==x` em 58/58 .TWN. `ACCENTS` (vazio) será preenchido no Passo 3 (fonte) para mapear á/ç/ã/… em bytes livres.
- **`ao_twn.py`** — diálogo dos `MAP*.TWN`. `extract_units(bytes)` lista mensagens da tabela principal; `rebuild(bytes, {idx: texto_pt})` reescreve a região e **recalcula todos os ponteiros** (u32 BE, base `0x260DFFF8`). Round-trip de identidade: 53/53 mapas byte-perfeito. Segmentos 'copy' preservam lacunas.
- **`ao_iso.py`** — imagem Saturn Track01 MODE1/2352. Regenera **EDC/ECC** (Corlett/ECM) — validado idêntico ao disco em 1069 setores. `parse_iso(bin)` lista arquivos; `patch_file(bin_in, bin_out, nome, novos_bytes)` faz patch in-place (novos_bytes ≤ tamanho original).

## Testes (todos passam)
- `ao_codec.py` — reversibilidade do codec
- `ao_twn.py` — round-trip de identidade do rebuild
- `ao_iso.py` — validação EDC/ECC contra o disco
- `test_roundtrip.py` — patch de identidade + modificação real + isolamento de setores
- `test_translate_e2e.py` — tradução com mudança de tamanho → rebuild → patch → releitura

## Pendências conhecidas
- **Crescimento de região**: PT é mais longo; quando a região de diálogo excede o original, `rebuild` retorna `ok=False` (`grew`). Estratégia de expansão (realocar região p/ fim do arquivo + ajustar `loaded_len` no header) fica para o Passo 4.
- **5 mapas sem tabela** detectada (min_len=6) — revisar (podem ter poucas/nenhuma fala).
- **Acentos** — dependem do Passo 3 (glifos na fonte + preencher `ACCENTS`).
- **Texto de menu/sistema** (exe `0`, BATTLE.BIN, etc.) é ASCII puro em tabelas de tamanho fixo — pipeline próprio a construir (mais simples).
