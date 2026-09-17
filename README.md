<div align="center">

![Albert Odyssey: Legend of Eldean — Tradução PT-BR GRIFFON BR](https://github.com/FernandoPeralta199x/Albert-Odyssey---Legend-of-Eldean-PTBR-GRIFFON/blob/main/assets/albert-odyssey-cover.jpg?raw=true)

# 🐉 ALBERT ODYSSEY: LEGEND OF ELDEAN
### Tradução PT-BR • por **GRIFFON BR**

![Plataforma](https://img.shields.io/badge/Plataforma-Sega%20Saturn-2038a6?style=for-the-badge)
![Idioma](https://img.shields.io/badge/Idioma-Portugu%C3%AAs%20BR-009c3b?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Jog%C3%A1vel-ffcc29?style=for-the-badge)
![Versão](https://img.shields.io/badge/Vers%C3%A3o-v1.1-lightgrey?style=for-the-badge)

*RPG de Sega Saturn (1997) traduzido do inglês para o português do Brasil —*
*todo o texto visível do jogo: diálogos, menus, itens, magias, loja e batalha.*

</div>

---

> Este repositório **não contém o jogo**. Distribui apenas a tradução como um **patch** que você aplica sobre a sua própria cópia original.

## ✅ O que está traduzido

Todo o **texto visível** do jogo está em português:

- **Diálogos** — 52 mapas, ~3.260 falas (abertura, cidades, NPCs, cenas, personagens) + falas de ação/loja + falas "órfãs" (nascentes de cura, poços, portas, menus "Beber/Deixar", intro).
- **Texto de sistema / UI** — menus, itens, armas, consumíveis, magias, status, mensagens de batalha, diálogo de loja (compra/venda) e telas de sistema.
- **Verificado**: varredura de completude não encontra texto de história em inglês; integridade EDC/ECC do disco confere (0 divergências).

Nomes próprios são mantidos no original de propósito (praxe de localização): lugares e katanas/armas japonesas icônicas (MURASAME, KOTETU, IZAYOI…).

## 📦 Como aplicar (release)

Baixe o `.zip` da [**última release**](../../releases/latest) (ou use a pasta [`release/`](release/)):

1. Tenha sua cópia original em BIN/CUE (versão USA) e **Python 3** instalado.
2. Rode:
   ```
   python ao_patch_apply.py "CAMINHO/Albert Odyssey - Legend of Eldean (USA) (Track 01).bin" "Track 01 PT-BR.bin"
   ```
   O aplicador valida sua cópia por checksum, aplica o patch e confere o resultado. Só a Track 01 muda — o áudio e o `.cue` continuam os originais.
3. Aponte o `.cue` para o `.bin` traduzido e abra no emulador de Saturn (Ymir, Mednafen…) com a **BIOS do Saturn** configurada.

Detalhes em [`release/LEIA-ME.txt`](release/LEIA-ME.txt).

### Checksums (SHA-256 · Track 01)
- Original esperado: `109dfbe626021f7a…`
- Resultado traduzido (v1.1): `d5aa8d0afb08e40f…`

## 🗂️ Estrutura

| Pasta | Conteúdo |
|---|---|
| `release/` | Patch distribuível (`.aopatch`) + aplicador em Python + instruções |
| `tools/` | Ferramentas de engenharia reversa e reinserção (Python) usadas no projeto |
| `translation/` | Traduções PT-BR (só o texto em português) |

## 🔧 Como funciona (resumo técnico)

- **Codificação do diálogo**: cifra de substituição simples — `ASCII = byte + 0x1F` — com códigos de controle ≥ `0xF5`. Ver [`tools/ao_codec.py`](tools/ao_codec.py).
- **Reinserção in-place**: cada fala é reescrita no **offset exato** da original (≤ tamanho, padding após o terminador); nada se move e nenhum ponteiro é alterado — imune a desalinhamento. Ver [`tools/apply_inplace.py`](tools/apply_inplace.py) e [`tools/ao_twn.py`](tools/ao_twn.py).
- **Falas órfãs**: mensagens lidas por script/sequencialmente (fora das tabelas de ponteiro) são reinseridas por offset. Ver [`tools/apply_orphans.py`](tools/apply_orphans.py).
- **Texto de sistema**: reinserção in-place respeitando o tamanho de cada campo. Ver [`tools/sys_pipeline.py`](tools/sys_pipeline.py).
- **Imagem do disco**: patch in-place na Track 01 (MODE1/2352) com regeneração de EDC/ECC. Ver [`tools/ao_iso.py`](tools/ao_iso.py).

## 🕓 Histórico de versões

- **v1.1** — CIRRUS reescrito com um tom mais **sério e solene** de mentor (menos deboche, mais dignidade); pequenos ajustes de texto.
- **v1.0** — Tradução completa do texto visível: diálogos, falas órfãs, e todo o texto de sistema/UI (menus, itens, loja, batalha).

## ⚠️ Limitações conhecidas

- **Acentos**: a fonte do jogo não tem glifos acentuados, então os acentos aparecem "chapados" (`voce` em vez de `você`). O texto já está escrito com acentos; uma **v2** pretende editar a fonte para exibi-los.
- **Tela de título**: o logo e o crédito do rodapé são gráficos embutidos (não texto) e permanecem no original.
- Alguns textos foram condensados para caber no espaço original, preservando o sentido.

## 📜 Créditos

- Jogo original © 1996 **Sunsoft / Sun Corporation**
- Localização em inglês © 1997 **Working Designs**
- Tradução PT-BR: **GRIFFON BR**

*Projeto de fã, sem fins lucrativos. Marcas e conteúdo do jogo pertencem aos seus respectivos donos.*
