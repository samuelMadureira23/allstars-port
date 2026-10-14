# All Star Port — PlayStation All-Stars Battle Royale (BCUS98472) → PC nativo

## O que já foi verificado (14/10/2026)

| Item | Resultado |
|---|---|
| Pasta do jogo | `Documents\[Downloadgameps3.com]PLUS\BCUS98472 - [...]` — dump em formato pasta (JB), não ISO Redump |
| `PS3_GAME\USRDIR\EBOOT.BIN` | 5,0 MB, cabeçalho `SCE\0` → **SELF criptografado** (precisa decriptar para ELF PPC64) |
| Assets | 48 arquivos `.psarc` (personagens, fases, shaders, core, global...) + `movies\attract.pam`, `music\`, `sound\stream` |
| Extras | `1-Update 1.04.pkg` (1,1 GB), `2-Pack Avatares PSN.pkg`, `3-Fix All DLC.pkg` |
| REA | v6.4.0, provider **Ghidra 12.1.4** disponível (instalado em `pes 13 descompilado\ferramentas\ghidra`) |
| Toolchain local | Python 3.11 ✅, Git ✅, Java 8 ✅ — **faltam**: Visual Studio 2022 (C++), LLVM/clang-cl, CMake, Ninja, RPCS3 |

## Ferramentas encontradas no GitHub

| Ferramenta | Para quê |
|---|---|
| [ColinGamez/allstars-ps3](https://github.com/ColinGamez/allstars-ps3) | **Port nativo deste mesmo jogo (BCUS98472)** via ps3recomp. Já compila (`MyGameRecomp.exe`, D3D12), boota até o FIOS e trava num `lwcond` inválido. Ponto de partida ideal. |
| [sp00nznet/ps3recomp](https://github.com/sp00nznet/ps3recomp) | Toolkit de recompilação estática PS3 → C/C++ (lifter PPU/SPU, ~93 módulos HLE, D3D12). Tem `sceNp*`/`sceNpMatching2` com servidor "psnr" — já roda online em Simpsons Arcade. |
| [RPCS3](https://github.com/RPCS3/rpcs3) | Decriptar o EBOOT (Utilities → Decrypt PS3 Binaries), referência de comportamento e para comparar execução. |
| [RipleyTom/rpcn](https://github.com/RipleyTom/rpcn) | Servidor que emula o matchmaking P2P da PSN (base para o modo online). |
| Ps3GhidraScripts (clienthax) | Scripts Ghidra: nomes de imports/exports por NID e syscalls PS3. |
| [PSArc-rs](https://github.com/Jacobboogiebear/PSArc-rs) | Extrair/reempacotar `.psarc`. |

## Estado do online hoje
- Servidores oficiais desligados em 25/10/2018.
- RPCS3 wiki: online **não funciona** (conexão, lobby, matchmaking = "No"); precisa de servidor customizado que não existe.

## Roadmap

### Fase 0 — Preparação
1. Instalar toolchain: VS 2022 (Desktop C++), LLVM (clang-cl), CMake ≥3.20, Ninja.
2. Clonar `ps3recomp` (commit `39e4f492...`) + `allstars-ps3` em `All star port\src\`.
3. Decriptar `EBOOT.BIN` → `EBOOT.BIN.elf` (RPCS3 ou scetool). Conferir: ~13,2 MB, PPC64 BE.
4. Montar VFS (`PS3_VFS_ROOT`) apontando para a pasta `PS3_GAME`.

### Fase 1 — Análise (REA + Ghidra)
- Abrir o ELF no REA/Ghidra, aplicar NIDs, mapear FIOS, loop principal, NP/rede.
- Usar RPCS3 como referência dinâmica para a sequência de boot.

### Fase 2 — Fazer o port bootar
- Resolver o bloqueio do FIOS (`[r31+0x178]` = contagem de workers = 0; fila do op em `0x48AB30`).
- `sceNp`/Voice/Http/Trophy → comportamento offline `NOT_CONNECTED` para passar dos menus.
- Pular cinematics (`cellSail`), registrar workloads SPU, chegar numa partida local.

### Fase 3 — Online
- Mapear o tráfego de rede do jogo (sceNpMatching2, sockets P2P, TUS/Score, HTTP).
- Ligar o HLE `sceNp` do ps3recomp a um servidor próprio (RPCN/psnr) e escrever o que faltar
  (lobby/matchmaking/ranking). Netcode P2P: provavelmente lockstep/rollback — investigar no código.

## Progresso

### 14/10/2026
- [x] `src/ps3recomp` (commit `39e4f49`) + `src/allstars-ps3` clonados
- [x] Patch do port convertido de UTF-16 → UTF-8 (`patches/ps3recomp-runtime-allstars.utf8.patch`) e aplicado
- [x] EBOOTs decriptados via RPCS3 → `work/eboot/EBOOT_1.00_disc.elf` (13.235.512 B) e `EBOOT_1.12_update.elf` (13.520.536 B)
- [x] `ppu_loader`: 376 imports / 25 libs (`docs/imports_1.00.md`, gerado por `scripts/list_imports.py`)
- [x] `ppu_lifter`: 25.544 funções → `work/recompiled_1.00/` (15 .cpp, 524 MB) + 1.098 handlers HLE
- [x] Achados do online: `docs/ONLINE_ACHADOS.md`
- [x] Ghidra headless (projeto em `work/ghidra_proj`, JSONs em `work/ghidra_1.00`, 3 min)
- [x] Toolchain: MSVC 14.51 + SDK 10.0.26100 (VS 2026 Build Tools) + LLVM/clang-cl 23.1.3 + CMake + Ninja
- [x] **Build:** `scripts\build.bat` → `build\MyGameRecomp.exe` (70 MB, Release). Rodar: `scripts\run.ps1 -Seconds 60 -Tag runN`
- [x] Reproduzido o travamento do upstream (`wait for invalid cond 'fios worker cond'`)
- [x] **CORRIGIDO:** `sys_lwcond_create` no HLE gravava o ponteiro do lwmutex como be64 (o PS3 usa be32) → FIOS lia
      `cond+0x10 == 0` e achava o cond inválido. Commit `f34e543` na branch `allstars-port` do ps3recomp
      (`patches/0001-...patch`). Resultado: o FIOS funciona, abre e lê `global.psarc` (PSAR/zlib), GCM e VideoOut configurados.
- [x] SPU: 3 imagens extraídas e recompiladas (`work/spu/lifted`): `Renderer_SPU` (task 1, polling a fila de render, OK),
      `spu_0002` (task 0, espera sinal), `spu_0001` (189 KB, ainda não despachada). Dispatch = HIT.
- [ ] **Próximo bloqueio:** depois de `SetDisplayBuffer`, a thread "BasicThread" (loader de recursos, `FUN_00079c38`)
      espera loads em voo e o main thread fica em `FUN_00509e44`/`FUN_00502ed8`. Investigar: descompressão zlib do psarc
      (PPU ou SPU?), sinal PPU→SPU da task 0, primeiro flip do GCM.
- [x] Diagnóstico `PORT_GSTACK="10,25,40"` (pilha guest de cada thread; runtime `ppu_debug_dump_guest_stacks`)
- [x] **Bloqueio identificado:** após ler 64 KB comprimidos de `global.psarc`, o FIOS chama
      `_cellSpursLFQueuePushBody` (NID 0x8A85674D) → **não implementado** → o pedido de descompressão nunca chega
      à task SPU 0 (`spu_0002`, LFQueue q=0x40089A00 size=32 depth=12 dir=3 ANY2ANY), e a `fios mediathread 5`
      fica em polling eterno (`FUN_004904bc`: vtable +0x10 isDone / +0x14 getResult).
      Opções: (a) implementar o push real do CellSyncLFQueue ANY2ANY (algoritmo do libsre/RPCS3 cellSync);
      (b) LLE do `libsre.sprx` do firmware do RPCS3 (docs/FIRMWARE_LLE.md do ps3recomp);
      (c) atalho: interceptar o decompressor do FIOS e descomprimir zlib no host.
- [x] **psarc criptografado decifrado:** cada bloco = u16 header + AES-256-CTR (chave/IV lidos da imagem SPU
      `spu_0002` em runtime: LS 0x114C0 key, 0x114B0 DEADBEEF, IV = DEADBEEF|len|0000|hdr|ctr) + raw deflate.
      Implementado em `src/allstars-ps3/stubs.cpp` como HLE de `_cellSpursLFQueuePushBody` (descomprime no host).
- [x] Corrigidos: `sceNpGetNpId` (ponteiro guest), getters PAMF sem init, use-after-free de ctx SPU (`spu_coh_forget`).
- [x] Job SPURS Edge Geometry (`0xB54C80`, 47904 B) recompilado → `work/spu/lifted/job_edgegeom` + `jobmods_register.c`.
- [x] Boot chega ao loop principal: threads Render, mixer de áudio, NpService, troféus, autosave; carrega
      `global/shaders/bootup/titlescreen.psarc`.
- [ ] **Próximos:** (1) PPU chama `0x40304` que não está na tabela de funções → adicionar como função extra e re-lift;
      (2) job Edge Geometry dá `HALT-ASSERT heqi pc=0x8DF8`; (3) cellSail (vídeo de abertura) só stub.
- [x] (09:00–12:00) T-001/T-002 resolvidas; FIFO `GCM_PARK_WAIT`; vídeo `SAIL_SKIP_MOVIES`; **NV4097_INLINE_ARRAY**;
      **SPURS `JC_RESUME`** → **TELA DE TÍTULO** ("PRESS START") e, com START, **MENU PRINCIPAL** + diálogo do tutorial
      (screenshots em `docs/marcos/`, fora do git). Integrado em `src/` (build\ chega ao título).

### Estado atual (2026-10-14 ~12:00)
- Boot: legal → (vídeo pulado) → título → START → Main Menu com diálogo "Would you like to go to the Tutorial?".
- **Bloqueio atual (T-011):** logo depois do menu o main espera um handle assíncrono chegar a 3 (`0x57544`);
  quem conclui é a tarefa SPURS da imagem `spu_0001` (entry 0xB71480, criada no START com arg {owner,0,handle,..}).
  A tarefa morre ao chamar métodos virtuais (vtables montadas em runtime) que o lifter não detectou
  (0x248C8, 0x4CE8, 0x30E8, ...). `scripts/spu_discover.sh` roda o jogo em loop, coleta os alvos não-liftados e
  re-lifta com `--extra-funcs` até zerar (lista em `work/spu/spu_0001_at_00B61480_extra.txt`).
- Cuidado: o runtime tem heurísticas do LittleBigPlanet para `image_id == 2` (wws-jobentry/wws-jobret);
  a nossa imagem 2 é a `spu_0001` por coincidência.
- Defeitos visuais conhecidos: texto do menu avermelhado/escuro (formato de textura/blend? investigar com `RSX_CAP`).
- Ferramentas de diagnóstico do port (main.cpp): `PORT_GSTACK`, `PORT_PEEK`, `PORT_FIFODUMP`, `PORT_WATCH`,
  `PORT_DRWATCH` (breakpoints de hardware), `PORT_HANGPROBE=<lr>`; runtime: `RSX_CAP`, `TCONST_FIFO`, `GCM_RECDBG`,
  `JC_TRACE`, `SPU_TASKARG`, `GCM_FLIPCOUNT`, `PAD_SCRIPT`/`PAD_FILE`.
- Diagnóstico: crash handler no main.cpp (`[CRASH]` + pilhas guest), `scripts/sym.py <rva>` (usa build/MyGameRecomp.map),
  `scripts/disasm.py` (capstone PPU).
- Ferramentas próprias: `scripts/xref_str.py` (xrefs via TOC, que o Ghidra não resolve), `scripts/decompile.py` (decompila por endereço)
- Python: usar `.venv` do projeto (`.venv\Scripts\python`); `set PYTHONUTF8=1`
- Ghidra: `pes 13 descompilado\ferramentas\ghidra\ghidra_12.1.4_PUBLIC` com `JAVA_HOME=...\ferramentas\jdk21`
- REA não suporta PowerPC → análise do PPU via Ghidra direto

## Regras do projeto
- Não versionar/distribuir EBOOT, ELF decriptado, `.psarc` nem chaves — o usuário fornece a própria cópia.
