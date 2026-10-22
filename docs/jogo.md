# Jogo: inventário e fatos do binário (frente 1)

Atualizado em 14/10/2026 pelo agente `claude` (T-018). Dados brutos em `analysis/jogo/` (gitignored, só
metadados), gerados por `python scripts/jogo_inventory.py`. Arquitetura do port, correções e estado do boot
estão em `docs/CONTEXTO_COMPLETO.md` e `PLANO.md`; este arquivo só descreve o jogo e o executável.

Legenda: **observado** = lido do arquivo; *inferido* = dedução, não confirmada.

## 1. Identidade e dump

| Item | Valor |
|---|---|
| Título | PlayStation All-Stars Battle Royale (Superbot / SCE, 2012) |
| ID / região | **BCUS98472**, EUA (NTSC-U), disco Blu-ray (`CATEGORY=DG`) |
| Versão do disco | `APP_VER 01.00`, `VERSION 01.00`, firmware mínimo `PS3_SYSTEM_VER 04.25` |
| NP | `NP_COMMUNICATION_ID NPWR02621_00` (troféus em `TROPDIR/NPWR02621_00/TROPHY.TRP`) |
| Vídeo / áudio (SFO) | `RESOLUTION=55` (480/576/720 + 16:9), `SOUND_FORMAT=775` (LPCM 2/5.1/7.1, DD, DTS) |
| Formato do dump | **pasta JB** (`PS3_DISC.SFB` + `PS3_GAME/`), não ISO; 23.933 arquivos, 6,31 GB |
| Local | `C:\Games\BCUS98472` (somente leitura) |

Conteúdo de `PS3_GAME/` (observado): `PARAM.SFO`, ícones/fundos PNG, `SND0.AT3` (RIFF/ATRAC3), `PS3LOGO.DAT`,
`LICDIR/LIC.DAT` (`PS3LICDA`), `TROPDIR/`, `PKGDIR/PKG00/INSTALL.PKG` (manual digital, `NPUO70233`, 39,6 MB) e `USRDIR/`.

Duas pastas vazias dentro do dump (`game/BCUS98472/USRDIR` e `PSASBRCACHE`, criadas hoje às 08:11–08:14) foram
*provavelmente* criadas pelo VFS do port ao montar `/dev_hdd0` e o cache `/dev_hdd1`. Montagens graváveis deveriam
apontar para fora da pasta do jogo (anotado para a frente de runtime).

## 2. Updates e DLC presentes

| Fonte | O que é | Observado |
|---|---|---|
| `PLUS\1-Update 1.04.pkg` | update oficial | 1,18 GB, content ID `UP9000-BCUS98472_00-PSABATROYL000001`; versão só pelo nome do arquivo (o PARAM.SFO interno é criptografado) |
| `PLUS\3-Fix All DLC.pkg` | licenças das DLC | 107 KB, 80 itens, `UP9000-BCUS98472_00-PSASBR0ALLDLCFIX` |
| `PLUS\2-Pack Avatares PSN.pkg` | avatares do XMB | 392 KB, não afeta o jogo |
| RPCS3 `dev_hdd0/game/BCUS98472` | **update 1.12 instalado** | `APP_VER 01.12`; `USRDIR`: `EBOOT.BIN` (1.12), `patch.psarc` (593 MB), DLC `heavenlysword`, `medievil` (fases) e `sbe/sbi/sbk/sbz_char_setup` (*Emmett, Isaac, Kat, Zeus*), `entitlements/` |

O port usa **só o EBOOT 1.00 do disco**. O 1.12 (último update) está decriptado para comparação e é a T-008.

## 3. EBOOT

| | 1.00 (disco) | 1.12 (update) |
|---|---|---|
| `EBOOT.BIN` (SELF) | 5.030.216 B, `SCE\0`, criptografado (SELF de disco, não NPDRM) | 5.241.744 B, `SCE\0`, criptografado |
| ELF decriptado (RPCS3, firmware do usuário) | `work/eboot/EBOOT_1.00_disc.elf`, 13.235.512 B, sha256 `a9de806a…` | `EBOOT_1.12_update.elf`, 13.520.536 B, sha256 `59a2668a…` |
| Tipo | ELF64 big-endian, PowerPC64 (e_machine 21), `ET_EXEC`, endereços de 32 bits | igual |
| Entry (OPD) | `0xC5B490` → código `0x10230`, **TOC r2 = `0xC84768`** | `0xC7BD40` → `0x10230`, TOC `0xCA55F0` |
| SDK | `sys_process_param` sdk `0x420001` (**SDK 4.20**), prio 64, pilha principal 512 KB, malloc page 1 MB | igual |
| TLS | `0xC8FE4C`, 8 B iniciados / 420 B | `0xCB1254` |

Os ELFs decriptados e os SELFs **nunca** saem desta máquina (AGENTS.md §8).

### Segmentos (1.00, observado)
| Tipo | vaddr | Tam. arquivo | Tam. memória | Flags |
|---|---|---|---|---|
| LOAD | `0x10000` | 12.677.736 | 12.677.736 | R-X (código + rodata) |
| LOAD | `0xC30000` | 503.520 | 30.821.752 | RW- (data, OPD, TOC, **BSS de 29,4 MB**) |
| TLS | `0xC8FE4C` | 8 | 420 | |
| PROC_PARAM | `0xC27200` | 40 | | `sys_process_param` |
| PRX_PARAM | `0xC27228` | 64 | | `sys_proc_prx_param` (libstub `0xB0E08C..0xB0E4D8`) |

Regra: no segmento de código, **vaddr = offset no arquivo + 0x10000**.

### Seções (1.00)
O ELF decriptado não traz os nomes (`.shstrtab` zerado). Papéis *inferidos* pelo layout padrão do SDK:
`.init 0x10200`, **`.text 0x10230` (11,5 MB)**, `.fini 0xB0A8BC`, `.sceStub.text 0xB0AA08` (12.032 B = 376 stubs
de 32 B), `.lib.ent*`/`.lib.stub*` `0xB0E080..0xB0E4D8`, `.rodata 0xB4A380` (905 KB), `.sys_proc_param 0xC27200`,
`.data 0xC30000..`, **`.opd 0xC5B480`** (135.912 B = 16.989 descritores de 8 B), **`.toc 0xC7C768`**, `.tbss 0xC8FE4C`,
`.bss 0xCAAF00` (30,3 MB). Lista completa com endereços em `analysis/jogo/elf_1.00.json`.

## 4. Imports (firmware) e módulos

- **1.00: 376 funções em 25 bibliotecas, 0 variáveis importadas; 344 com nome conhecido, 250 com HLE no
  ps3recomp hoje** (`src/ps3recomp`). 1.12: 378 em 26 (+`sceNpCommerce2` com 2 funções, loja de DLC; +3 em `sceNp`).
- Exports: nenhum além do módulo principal (sem PRX próprios).
- **PRX do jogo: nenhum.** Não há `.sprx`/`.self` no disco; tudo que é de firmware vem por `cellSysmoduleLoadModule`.

| Biblioteca | Funções | Com nome | Com HLE |
|---|---:|---:|---:|
| sceNp | 53 | 48 | 20 |
| cellSpurs | 39 | 39 | 37 |
| cellSail (vídeo) | 36 | 29 | 19 |
| sysPrxForUser | 33 | 33 | 21 |
| cellGcmSys | 28 | 28 | 26 |
| sys_net | 24 | 21 | **2** |
| sys_fs | 23 | 23 | 13 |
| cellSysutil | 19 | 19 | 19 |
| cellVoice | 15 | 11 | 11 |
| cellSpursJq | 14 | 14 | 10 |
| cellHttp | 14 | 8 | 8 |
| sceNpTus | 13 | 9 | 3 |
| cellAudio | 11 | 11 | 11 |
| cellNetCtl / sys_io | 10 / 10 | 10 / 10 | 10 / 10 |
| sceNpTrophy | 9 | 9 | 9 |
| cellGame | 8 | 8 | 7 |
| cellPamf / cellSysmodule / cellRtc | 4 / 4 / 3 | 3 / 4 / 3 | 3 / 4 / 3 |
| cellSysutilNpEula | 2 | 0 | 0 |
| cellUserInfo, cellSysutilMisc, cellHttpUtil, cellSync | 1 cada | 1 | 1 |

Lista por NID: `docs/imports_1.00.md` (gerada antes; 242 HLE na época) e `analysis/jogo/elf_1.00.json` (atual).
Os maiores buracos para o online são **sys_net (22 sem HLE)**, **sceNp (33)** e **sceNpTus (10)**.

Módulos pedidos a `cellSysmoduleLoadModule` (observado: `li r3,ID` antes do `bl` ao stub; 4 chamadas com ID
dinâmico não resolvidas): NET 0x00, HTTP 0x01, HTTP_UTIL 0x02, HTTPS 0x04, RTC 0x09, SPURS 0x0A, PAMF 0x12,
SYSUTIL_NP 0x16, SAIL 0x1D, SYSUTIL_USERINFO 0x32, SYSUTIL_GAME 0x3E, SYSUTIL_NP_TUS 0x45, VOICE 0x46,
SYSUTIL_LICENSEAREA 0x49, SPURS_JQ 0x50 (+ SYSUTIL_NP_COMMERCE2 0x44 no 1.12).

## 5. Syscalls diretas (instrução `sc` no EBOOT)

67 números distintos (`li r11,N` antes do `sc`; 17 `sc` sem número resolvível estaticamente). Iguais em 1.00 e 1.12.
Mais usados: `sys_mutex_lock/unlock` (102/104), `sys_timer_usleep` (141), `sys_ppu_thread_join` (44),
`sys_spu_thread_read_ls` (182), `sys_tty_write` (403). Famílias: ppu_thread (43, 44, 48), timer (70–76, 141),
event_flag (82, 83, 85, 87), mutex (100–104), cond (105–109), rwlock (120–127), event queue/port (128–138),
time (144–147), SPU raw/thread (156, 169, 181, 182, 190–192, 251, 252, 260), memory (348–352), tty (402, 403),
fs (801–804, 818). Números sem nome na tabela do ps3recomp: 144, 252, 260, 633, 634, 872, 988
(*pela numeração pública: 144 sys_time_get_timezone, 252 sys_spu_thread_group_disconnect_event_all_threads,
260 sys_spu_image_open_by_fd; 633/634/872/988 a confirmar*). Lista com endereços em `analysis/jogo/elf_*.json`.

## 6. Código SPU embutido

Três **ELFs SPU** dentro do EBOOT (e_machine 23, observado):

| Imagem (nome no port) | vaddr (1.00) | Tamanho | Entry LS | Papel (do port) |
|---|---|---|---|---|
| `spu_0000_at_00B5C280` | `0xB6C280` | 20.948 | `0x3050` | Renderer_SPU (fila de render) |
| `spu_0001_at_00B61480` | `0xB71480` | 189.668 | `0x3070` | lógica do frontend/menus (tarefa SPURS) |
| `spu_0002_at_00B8F980` | `0xB9F980` | 69.588 | `0x3050` | descompressor/AES dos `.psarc` (chave em LS `0x114C0`, lida em runtime) |

No 1.12 as mesmas três mudam de lugar (`0xB88A00`, `0xB8DC00` com 200.292 B, `0xBBEA80`). Além dos ELFs há
**jobs SPURS crus** (não-ELF): Edge Geometry em `0xB54C80` (47.904 B, já liftado) e o policy module WWS do áudio
em EA `0xC24200` (T-020). Novas telas podem trazer jobs novos (física, animação, partículas).

## 7. Dados (`USRDIR`)

| Tipo | Qtde | Tamanho | Formato |
|---|---:|---:|---|
| `.psarc` | 48 | 1,73 GB | PSAR 1.4 zlib, blocos 64 KB, **cada bloco AES-256-CTR + raw deflate + Adler-32**; extrator em `tools/psarc_extract.py` (`docs/PSARC.md`) |
| `sound/stream/**/*.xvag` | 23.824 | 4,15 GB | XVAG (Sony; vozes por personagem e idioma de/en/es/fr/it/ja…) |
| `music/**/*.mid` | 43 | 5 KB | MIDI (marcadores/sequências de música por fase) |
| `movies/attract.pam` | 1 | 380 MB | PAMF (vídeo de abertura; hoje pulado por `SAIL_SKIP_MOVIES=1`, T-003) |

Dentro dos 48 `.psarc` (33.552 arquivos, 3,69 GB descomprimidos; extensões próprias do motor Bluepoint/Superbot,
interpretação *inferida* pelo nome): `.ctxr` texturas (9.887, 2,7 GB), `.cani` animações, `.cmdl` modelos,
`.cskn` skins, `.bnk` bancos de som, `.cgpr`(+`.stream`) programas/shaders, `.cesm`, `.cbws`, `.bcsv` tabelas,
`.ccin` cinemáticas, `.csmo`, `.ccol` colisão, `.cfx` efeitos, `.cmap`, `.cfbt`, `.cadi`. Formatos internos ainda
não documentados. Pacotes: 20 personagens (`*_char_setup`), 14 fases, `global`, `core`, `shaders`, `bootup`,
`titlescreen`, `loadscreen*`, `cinematics`, `bosslevel`, `items`, `minions`, `gamemodes`, `practice`,
`charactercostumeportraits`.

## 8. Toolchain desta máquina (verificado 14/10/2026)

| Ferramenta | Estado |
|---|---|
| VS 2026 Build Tools 18.10 (MSVC 14.51) + Windows SDK 10.0.26100 | ok (`scripts\build.bat` chama `vcvars64`) |
| LLVM clang-cl 23.1.3 | ok (`C:\Program Files\LLVM`, fora do PATH; o build.bat adiciona) |
| CMake 4.4.4, Ninja 1.13.2, Git 2.55 | ok |
| Python 3.11 + `.venv` (capstone, pycryptodome, unicorn, construct, tqdm) | ok |
| Ghidra 12.1.4 + JDK 21 (em `pes 13 descompilado\ferramentas`) | ok |
| RPCS3 0.0.43 (decriptação, referência) | ok |
| Direct3D 12 | ok (backend atual) |
| Vulkan runtime | ok: loader 1.4.341, driver NVIDIA 1.4.351 |
| **Vulkan SDK** (headers, glslang/glslc, spirv-cross, validation layers) | **falta** (`VULKAN_SDK` vazio). Necessário para a T-016; instalar só com aprovação do Samuel |
| dxc | fora do PATH (vem com o Windows SDK; o backend D3D12 atual não depende) |

Hardware: Ryzen 7 7700 (8c/16t), 31 GB RAM, RTX 5070 (+ iGPU AMD), 408 GB livres em C:. Builds e execuções
do jogo passam pela fila de 2 vagas (`scripts\heavy_slot.py`, AGENTS.md §3 item 8).

## 9. O que cada frente precisa saber

- **Recompilador (CPU):** alvo é o ELF 1.00; 25.544 funções PPU já liftadas em `work/recompiled_1.00`; OPD/TOC
  acima; 3 ELFs SPU + jobs crus. Funções SPU chamadas só por vtable não são achadas pelo lifter (causa dos
  travamentos T-011/T-017); `scripts/spu_discover.sh` + `spu_func_candidates.py` resolvem por iteração.
- **Runtime/HLE:** 126 imports sem HLE (lista no JSON); os de rede e `sys_fs` são os próximos a aparecer.
  O VFS cria pastas dentro do dump (seção 1).
- **Gráficos:** o jogo usa `cellGcmSys` (28 funções) e FIFO NV4097; desenha a UI com `INLINE_ARRAY`; fragment
  programs são copiados por draw para um ring buffer (cache tem de ser por hash). Vulkan SDK não instalado.
- **Online:** NP `NPWR02621_00`; bibliotecas sys_net/sceNp/sceNpTus/cellHttp(S)/cellVoice; a 1.12 acrescenta
  `sceNpCommerce2`. Servidores e protocolo em `docs/ONLINE_ACHADOS.md`. Partidas online reais exigem decidir
  1.00 vs 1.12 (jogadores da comunidade usam 1.12; o port roda 1.00).
