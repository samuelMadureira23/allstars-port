# Contexto completo do projeto (para uma sessão nova do Claude)

Atualizado em 14/10/2026, fim da tarde, pelo agente `claude`. Complementa o `AGENTS.md` (regras), o
`PLANO.md` (histórico), o `coord/TASKS.md` (quadro) e o `coord/LOG.md` (diário). Se algo aqui
divergir do LOG, o LOG mais recente vale.

---

## 1. O que é o projeto

- **Jogo:** PlayStation All-Stars Battle Royale (PS3, BCUS98472, Superbot/SCE, 2012), cópia do usuário em
  `C:\Users\samue\Documents\[Downloadgameps3.com]PLUS\BCUS98472 - [Play Station All Stars Battle Royale]` (somente leitura).
- **Meta 1:** port nativo para Windows x64 por **recompilação estática** (não é emulador): o código PPU (PowerPC 64)
  vira C, o código SPU vira C, e as bibliotecas do sistema do PS3 são reimplementadas (HLE) no host.
- **Meta 2:** modo online funcional com servidor substituto local (os servidores da Sony fecharam em 2018).
- **Base usada:** `sp00nznet/ps3recomp` (runtime + lifters + HLE + backend D3D12) e `ColinGamez/allstars-ps3`
  (projeto do jogo em cima do ps3recomp). Ambos clonados e modificados localmente; **nada foi publicado**.
- **Dono:** Samuel (usuário). Fala português, deixa o PC ligado, quer trabalho autônomo e relatórios curtos.
  Usa também o GPT/Codex "Astra" como segundo agente (nome `astra`).

## 2. Layout da pasta `C:\Users\samue\Documents\All star port`

```
AGENTS.md / CLAUDE.md        regras comuns / notas do Claude (@AGENTS.md)
PLANO.md                     histórico técnico e estado
coord/TASKS.md, LOG.md       quadro de tarefas e diário (mais novo no topo)
coord/locks/                 travas (scripts/claim.py)
coord/PROMPT_ASTRA.md        prompt de entrada do Astra
coord/PROMPT_PROJETO.md      prompt de entrada desta sessão (modo Projetos)
docs/                        ONLINE_ACHADOS, PSARC, DIFFTEST, ROADMAP, NATIVE_PROOF, imports_1.00, este arquivo
docs/marcos/                 screenshots dos marcos (gitignored)
scripts/                     build.bat, run.ps1, claim.py, disasm.py, decompile.py, sym.py, xref_str.py,
                             bmp2png.py, list_imports.py, spu_discover.sh, spu_func_candidates.py, ghidra/
tools/                       psarc_extract.py (+testes), difftest/ (Astra), inventário inicial (Codex)
src/ps3recomp, src/allstars-ps3          INTEGRAÇÃO (branch allstars-port). Só recebe merges.
agents/claude/{ps3recomp,allstars-ps3}   worktrees do Claude (branch claude/main)
agents/astra/{ps3recomp,allstars-ps3}    worktrees do Astra (branch astra/main)
build/  build-claude/  build-astra/      builds (MyGameRecomp.exe + .map)
work/eboot/                  EBOOT_1.00_disc.elf e EBOOT_1.12_update.elf DECRIPTADOS (nunca versionar)
work/recompiled_1.00/        C++ gerado do PPU: 25.544 funções em ppu_recomp_000..014.cpp (~524 MB) + ppu_hle_nids.cpp
work/spu/images/             imagens SPU extraídas do EBOOT (.elf)
work/spu/lifted/             C gerado do SPU: spu_0000_at_00B5C280, spu_0001_at_00B61480, spu_0002_at_00B8F980,
                             job_edgegeom, jobmods_register.c, spu_workloads.c
work/spu/spu_0001_at_00B61480_extra.txt  ~226 entradas extras de funções SPU (vtables descobertas)
work/runs/                   logs de execução <tag>.out.log/.err.log, capturas capN/
work/ghidra_proj             projeto Ghidra com análise completa do 1.00
.venv/                       Python (capstone, pycryptodome, unicorn 2.1.4, construct, tqdm)
```

O repositório git da raiz versiona coordenação, docs, scripts e tools. `ps3recomp` e `allstars-ps3` são
repositórios separados com worktrees. Commits sempre com
`git -c user.name=samuel -c user.email=samuel.madureira23@gmail.com commit ...` e a linha de coautoria do agente.

## 3. Como o port funciona (arquitetura)

1. **PPU lifter** (`ps3recomp/tools/ppu_lifter.py`): lê o ELF decriptado, acha funções (Ghidra + heurística) e
   gera uma função C++ por função PPU (`func_00XXXXXX(ppu_context*)`). Registradores ficam no `ctx`; memória guest é
   `vm_base + EA` (big-endian, acessos com swap). Chamadas indiretas passam por uma tabela de funções
   (`ppu_recomp_014.cpp`). Imports (stubs em ~0xB0xxxx) viram `ps3_hle_call(NID, ctx)`.
2. **HLE:** `ps3recomp/libs/*` (cellSpurs, cellGcmSys, cellFs, cellPad, cellSail, sceNp...) e
   `ps3recomp/runtime/syscalls/*` (lv2: threads, lwmutex, lwcond, event queue/flag, timer...). O jogo também tem
   HLEs próprios em `allstars-ps3/stubs.cpp` (ex.: `_cellSpursLFQueuePushBody`).
3. **SPU:** imagens SPU embutidas no EBOOT são extraídas e convertidas em C (`spu_lifter`). Em tempo de execução,
   `spu_workload.c` reconhece a imagem pelo fingerprint e roda a versão lifted numa thread do host
   (`spu_workload_dispatch_async`). DMA/MFC/atomics/canais em `runtime/spu/spu_dma.h`, `spu_channels.c`.
   SPURS tasks, taskset e job chains são emulados em `libs/spurs/cellSpurs.c`, `spurs_job.c`, `spurs_policy.c`,
   `spurs_taskset.c`.
4. **RSX/GCM:** o jogo escreve comandos NV4097 num FIFO; `cellGcmSys.c` caminha o FIFO, `rsx_commands.c` decodifica,
   e `rsx_d3d12_backend.c` desenha com D3D12. Fragment programs: `rsx_fp_decompiler.c` → HLSL; vertex programs:
   `rsx_vp_decompiler.c`. Há backends Metal e nulo (um backend Vulkan seria a T-016).
5. **Executável:** `allstars-ps3/main.cpp` carrega o ELF, configura VFS (`PS3_VFS_ROOT` = pasta do jogo),
   variáveis padrão, diagnósticos e o crash handler, e chama o entry point recompilado.

### Fatos de endereços (EBOOT 1.00 do disco)
- TOC (r2) = `0xC84768`; vaddr = offset do arquivo + `0x10000` no segmento de código.
- Imagem SPU do descompressor (spu_0002) em EA `0xB9F980`; LS 0x114C0 = chave AES; 0x114B0 = DEADBEEF.
- spu_0001 (189 KB, lógica do frontend/menus) entra em `0xB71480`; imagem 2 no registro (por coincidência o runtime
  tem hacks do LittleBigPlanet para `image_id == 2`: wws-jobentry/jobret — cuidado).
- Syscalls vistos: 0x8d (141) = sys_timer_usleep; 0x55 (85) = sys_event_flag_wait; 0x57 (87) = sys_event_flag_set.
- `0x57544` = espera `*(u32*)handle == valor` com lwarx + usleep(5). Chamadores `0x57EDC`/`0x57F48` esperam 3.
- `0x506E90` (thread Render) faz polling de `cellGcmGetFlipStatus` com usleep(300).
- `0x19C4C4` (main) espera um event flag que a Render sinaliza ao fim do quadro.

## 4. Linha do tempo das correções (o que já foi resolvido e por quê)

| # | Sintoma | Causa | Correção |
|---|---|---|---|
| 1 | `wait for invalid cond 'fios worker cond'` | `sys_lwcond_create` gravava ponteiro do lwmutex como be64 | be32 (`ppu_sysprx.cpp`) |
| 2 | FIOS lê psarc e para | `_cellSpursLFQueuePushBody` não implementado | HLE em `stubs.cpp`: AES-256-CTR (chave lida da memória do SPU) + raw deflate no host |
| 3 | Crash em sceNp/PAMF | ponteiros guest sem tradução, getters sem init | `GUEST_PTR`, guards |
| 4 | Use-after-free de ctx SPU | `spu_coh_notify_write` guardava ctx de pilha | `spu_coh_forget` em spurs_job/policy/spu_lifted_job.h |
| 5 | `HALT-ASSERT heqi pc=0x8DF8` no Edge Geometry | checagem de pilha SPU: r1 word1 = espaço disponível | `ctx.gpr[1]._u32[1] = size_stk - 16` (spurs_job.c) |
| 6 | "stuck calling 0x40304" (Render) | HLE do LFQueue tratava a fila do Renderer_SPU como Edge → corrompia memória (achado com breakpoints de hardware) | roteia por tamanho do elemento (32 = Edge); senão push PPU2SPU real do SDK |
| 7 | FIFO pulava segmentos | resync ignorava JUMP-para-si (SPU ainda preenchendo) | `GCM_PARK_WAIT=1` |
| 8 | Quadros pretos | NV4097_INLINE_ARRAY (0x1818) não implementado | `rsx_inline_array_push/flush` |
| 9 | Travava após ~1300 quadros | job chain reiniciava do início e contava conclusões em dobro | `JC_RESUME=1` (PC persistente) |
| 10 | Vídeo de abertura travava | cellSail sem decoder | `SAIL_SKIP_MOVIES=1` emite PLAYER_STATE_CHANGED |
| 11 | spu_0001 morria em métodos virtuais | vtables montadas em runtime, lifter não via | `spu_discover.sh` iterativo + `spu_func_candidates.py` (pós-return) → 226 extras, relift |
| 12 | Menu travava em `0x57588` | (a) corrida: CreateTask passava id/taskset por globais e duas threads PPU criam tarefas → task 5 rodava args da 6; (b) slots nunca liberados → NOMEM na 129ª | `spu_workload_dispatch_task_async` com id explícito, `TASK_LOCK`, `cellSpurs_task_exited` libera slot e bits (ps3recomp@bb13c0a) |
| 13 | ~1 fps depois do START | cache de PSO chaveado por endereço do FP; o jogo copia cada FP para um ring buffer por draw | chave = hash do código (constantes já vão por b1/fp_k) → 0 MISS, RSX ~30 fps |

Também do Astra: extrator psarc completo (T-004), teste diferencial PPU vs Unicorn (T-007) que achou bug de
CR.SO nas comparações inteiras do lifter, e a correção no lifter (T-015, validada, falta integrar: exige relift
completo do PPU com a trava LIFT e rebuild — e depois rodar 60 s sem regressão).

## 5. Estado atual e investigação em andamento

**Funciona:** boot → aviso legal → título "PRESS START" → START → menu principal com diálogo do tutorial
("Would you like to go to the Tutorial?"). Sem áudio audível, input só scriptado, cores do texto do menu erradas.

**Bloqueio atual — T-017 (intermitente):** a tarefa SPURS da spu_0001 (entry 0xB71480) é criada aos pares pelo
PPU com argumento `{owner, cmd, handle, x}` (cmd 0/4/5/6...; `handle` = palavra de estado; o PPU espera ela chegar a 3).
- Execuções boas: centenas de tarefas, todas retornam, aparecem comandos novos (cmd=6 com 1.0f) = o menu avança.
- Execuções ruins: uma tarefa retorna mas o handle fica em 1 (claude-long1: só 3 tarefas, para aos 97 s), ou 2
  tarefas concorrentes nunca retornam (claude-perf2, para aos 117 s).
- O que a tarefa faz no fim (func SPU 0x2CC60): lê `handle+8` (= ponteiro 0x4001D518), faz **incremento atômico**
  nessa palavra (helper 0x2FC58/0x2FCB0: GETLLAR 0xD0 + PUTLLC 0xB4 em loop) e uma **leitura atômica** de `handle+4`
  (helper 0x2FD18). A linha 0x4001D500 tem contadores que crescem 1 por tarefa (+0x00, +0x10, +0x18 = contador-2,
  +0x30 = 2) — parece fila/ticket consumido pelo PPU. **Ainda não se sabe quem escreve o estado 3**: hipótese A, um
  consumidor PPU (thread Render?) lê essa fila e marca 3; hipótese B, a própria tarefa por PUTLLC na linha do handle.
- Próximo passo planejado: rodar com `SPU_ATOMTRACE=3000 SPU_ATOM_IMG=2` (filtro por imagem, adicionado agora,
  ainda não commitado) + `SPU_DMATRACE_ALL=1 YDKJ_DMA_IMG=2` e comparar uma execução boa com uma ruim; depois
  `PORT_DRWATCH` no handle (o endereço muda por execução; pode exigir armar o watch dinamicamente a partir do
  CreateTask). Suspeitas de causa: corrida entre tarefas concorrentes (antes eram serializadas pela lentidão),
  semântica de reserva/PUTLLC com duas threads SPU do host, ou a ordem create→dispatch (no PS3 real a tarefa só
  roda quando o PM a seleciona; aqui roda imediatamente na CreateTask, talvez antes do PPU terminar de preencher o owner).
  Uma opção de teste rápido: `LBP_SPU_SERIAL=1` (serializa as tarefas SPU) — se o travamento sumir, é concorrência.

**Depois da T-017:** navegar pelo menu (X/O, setas), seleção de personagem, carregamento da fase 3D, combate.
Cada tela nova deve trazer: imagens SPU novas (jobs de animação/física/partículas → extrair, liftar, registrar),
HLEs faltando, shaders novos.

## 6. Receitas de depuração (o que funcionou)

- **Rodar:** `powershell -ExecutionPolicy Bypass -File scripts\run.ps1 -Agent claude -Seconds 200 -Tag claude-x`.
  No PowerShell, defina `$env:VAR` no MESMO comando (cada chamada é um processo novo). O menu aparece ~100 s após o boot.
- **Input:** `PAD_SCRIPT="t:mask,..."` (máx 32 eventos). mask: byte baixo = digital1 (SELECT 0x01, L3 0x02, R3 0x04,
  START 0x08, UP 0x10, RIGHT 0x20, DOWN 0x40, LEFT 0x80); byte alto = digital2 (L2 0x01, R2 0x02, L1 0x04, R1 0x08,
  TRIANGLE 0x10, CIRCLE 0x20, CROSS 0x40, SQUARE 0x80) → X = 0x4000. Também `PAD_FILE`.
- **Travou?** `PORT_GSTACK="130,170"` (pilha guest de todas as threads), depois `scripts\disasm.py` no `lr`.
  `PORT_HANGPROBE=<lr>` despeja registradores/objetos quando a main fica parada nesse lr por 3 s.
- **Memória corrompida?** `PORT_DRWATCH=<ea>` (breakpoint de hardware de escrita; achou o bug #6),
  `PORT_WATCH` (proteção de página), `PORT_PEEK`.
- **Lento?** `PERF=1` (tempo do RSX: tex, vtx, PSO, guest), `SPU_TASKTIME=1` (fila vs execução de tarefa SPU),
  `GCM_FLIPCOUNT=1` (linha [flip] a cada 10 flips com timestamp).
- **SPU:** `SPU_TASKARG=1` (r3 da tarefa), `SPU_DMATRACE_ALL=1 YDKJ_DMA_IMG=<img>` (cada GET/PUT),
  `SPU_ATOM_EA=<hex> SPU_ATOM_FULL=1` (atomics numa linha, com conteúdo), `SPU_ATOMTRACE=N SPU_ATOM_IMG=<img>`,
  `SPU_DUMP_MISS=<dir>` + `scripts/spu_discover.sh` (alvos SPU não liftados), `SPU_LS_DUMP=<prefixo>`.
- **SPURS:** `JC_TRACE`, `SPURS_TASKSET_TRACE`.
- **Imagem:** `RSX_CAP=inicio:qtd:passo RSX_CAP_DIR=<dir>` (backbuffer + render targets por quadro;
  `scripts\bmp2png.py in.bmp out.png`), `FP_LIST=1`, `FP_PICK=<fp>`, `PSOMISSDBG=1`, `HASHDBG=1`.
- **Crash:** `[CRASH]` no err.log com RVA → `python scripts\sym.py --build build-claude 0xRVA`.
- **Análise estática PPU:** Ghidra headless (`scripts\decompile.py 0xADDR`), `scripts\xref_str.py` (xrefs de string via
  TOC), código gerado em `work/recompiled_1.00/*.cpp` (grep `func_00XXXXXX(`).
- **Análise SPU:** o C lifted em `work/spu/lifted/<img>/spu_recomp.c` é legível (cada instrução vira uma linha).

## 7. Armadilhas conhecidas

- Heredoc no Git Bash + Python: `\n` dentro de strings C pode virar quebra de linha real (já quebrou o build 2 vezes).
  Prefira o Edit tool ou strings raw (`r"""..."""`).
- `Remove-Item -Recurse` costuma ser bloqueado; crie diretórios novos em vez de apagar.
- O build do worktree (`scripts\build.bat Release claude`) recompila só o que mudou (~2 min); mexer em
  `work/recompiled_1.00` recompila tudo (~15+ min).
- Os logs ficam grandes (50–70 mil linhas); use grep/awk com padrões, não leia inteiro.
- O endereço dos objetos do heap muda entre execuções (timing); não fixe EAs de heap entre runs.
- Execuções são **não determinísticas** (threads do host). Repita antes de concluir algo.
- Os hacks LBP/YDKJ no runtime (variáveis `LBP_*`, `YDKJ_*`) vêm de outros jogos portados com o ps3recomp;
  alguns ficam ativos por padrão para `image_id` específicos.

## 8. Online (resumo; detalhes em docs/ONLINE_ACHADOS.md)

- Servidores OTG: `battleroyale-final.ps3.online.scea.com`, turn1/turn2 (TURN/relay), telemetria, ipmapping.
- Código: `sceotClientServerConnect`, `otg::CryptManager`; partidas com MatchStyle server/client; seletor de host em `0x3008e0`.
- A comunidade tem o "All-Stars Matchmaker" (playallstars.org) e PsasPs3Hooks para RPCS3 — referência, não baixar
  nada sem o Samuel aprovar.
- Plano: T-005 (RE do protocolo, estático) → T-010 (servidor local em `online/server/`) → testar com 2 instâncias.

## 9. Coordenação multiagente e subagentes

- Protocolo completo no AGENTS.md §3. Resumo: `claim.py claim T-xxx <nome> --paths ...`, atualizar TASKS, trabalhar
  só nos caminhos travados, escrever no LOG ao parar, `claim.py release`.
- Travas especiais: `INTEGRATION` (merge em `src/`), `LIFT` (regenerar `work/recompiled_1.00` ou `work/spu/lifted`),
  e recomendado `GPU` (só uma execução do jogo por vez).
- Subagentes: um worktree + build por subagente (`git worktree add ../../agents/<nome>/ps3recomp -b <nome>/main claude/main`
  dentro de `src/ps3recomp`, idem allstars-ps3; `scripts\build.bat Release <nome>`; `run.ps1 -Agent <nome>`).
  Máx. 2 builds simultâneos (CPU/RAM). O orquestrador revisa e integra.
- Tarefas boas para paralelizar: T-005 (online, estático), T-013 (cores do menu: analisar FP/blend com RSX_CAP/FP_PICK),
  T-012 (XInput/teclado em `libs/input/cellPad.c`), T-016 (Vulkan), auditoria de HLE faltando (`docs/imports_1.00.md`:
  376 imports, 242 com HLE).

## 10. Estimativas comunicadas ao usuário

- ~33% do projeto total (com online), ~40% do port offline.
- Prazo honesto: primeira luta jogável em semanas, jogo offline completo em 1–3 meses, online +1–3 meses;
  o usuário é otimista e espera mais rápido. Relate progresso por marcos (tela nova = marco; salve screenshot em docs/marcos/).

## 11. Limites (repetidos de propósito)

Nunca versionar/publicar/enviar: EBOOT/ELF decriptado, .psarc, assets, firmware, chaves. Sem push/PR/download/
instalação sem pedido explícito. Não alterar configurações/saves do RPCS3. Servidores online só locais.
