# Diário de passagem (entrada mais nova no topo)

Modelo de entrada:
```
## 2026-10-14 14:40 — claude-cpu — T-019 fallback do interpretador SPU (teste)
Fez: apliquei 0001-spu-interp-fallback.patch em agents/claude-cpu/ps3recomp (claude-cpu/main, commit 3e8cdb2; `git am --keep-cr`
falha por CRLF com autocrlf=true, sem --keep-cr aplica limpo). Build pela fila ok (spu_interp_call/spu_interp_step no .map).
Rodei 200 s, PAD_SCRIPT="100:0x0008,105:0x0008,140:0x4000,145:0x4000", GCM_FLIPCOUNT=1, com work/spu/lifted já com o relift
+0x4DC0/0x5050 (sem mudança desde 13:31).
Resultado/evidência (work/runs/claude-cpu-ifb2-{off,on}.err.log):
- ifb2-off (SPU_INTERP_FALLBACK=0): 614 [flip], último [flip] 2540 aos 157 s (relativo ao 1º flip); 3180 tarefas RETURNED.
- ifb2-on (padrão + SPU_INTERP_MISSLOG): 566 [flip], último [flip] 2060 aos 121 s; 2168 RETURNED; .miss.txt não criado.
- Ambos: 0 [spu-ifb], 0 BRANCH-TO-0, 0 HALT, 0 [CRASH], 0 HANGPROBE. Ambos param no mesmo ponto do claude-stab1..3
  (depois do X no diálogo do tutorial: "[RSX] label write @0x20000400 = 2..7" e depois só [WAIT] q=5).
- Conclusão: com o relift atual nenhuma função SPU não liftada é atingida até aqui, então o fallback não é acionado e não muda
  o comportamento. O bloqueio do tutorial independe do patch.
- Falso alarme do ifb1: "sem [flip]" era só falta de GCM_FLIPCOUNT=1 ([flip] só sai com ela, cellGcmSys.c:1982). Os [WAIT] q=5
  também aparecem aos milhares em runs bons (claude-gpu-rs2).
Mudou arquivos: agents/claude-cpu/ps3recomp@3e8cdb2 (runtime/spu/spu_interp_call.c novo, spu_channels.c, spu_interp.c, teste).
Pendências / próximo passo: o caminho do fallback ainda não foi exercitado no jogo. Para testar, rodar com um lift sem os
extras 0x4DC0/0x5050 (deveria aparecer [spu-ifb] em vez de BRANCH-TO-0). docs/cpu-abi.md ainda não escrito. Não integrado em src/.
Avisos para `claude`: este fallback é a correção genérica da classe de bug da T-017 (função SPU não liftada vira interpretação
em vez de abortar a tarefa). Não substitui o relift com extras, que continua valendo para desempenho. Desligar: SPU_INTERP_FALLBACK=0.
Integrar em src/ só com a trava INTEGRATION, combinando com você.
## 2026-10-14 (fim da tarde) — claude-net — T-005/T-010 pausadas
Fez: gravou o servidor substituto escrito pelo coordenador (`net/server`, 23 testes OK com o .venv) e `docs/net.md`;
commit db55ac9. Escreveu `docs/ONLINE_PROTOCOLO.md` (OTG: TCP sem TLS, DNS próprio via UDP:53, estados da conexão;
LAN: HostLanLobby 0x2FE00C, JoinLanLobby 0x2FE36C, g_VersusLanFlag **0x0223FFA8** — corrige a estimativa 0x025332F8,
que é outra global). Decompilações locais em work/decomp_otg*, work/decomp_lan* (fora do git).
Pendências: ver seção "Pendente" de docs/ONLINE_PROTOCOLO.md. Travas T-005/T-010 liberadas; online pausado até a
primeira luta jogável (decisão do Samuel). Worktrees agents/claude-net/* ficam (sem commits novos).

## 2026-10-14 (tarde) — claude-net — T-005/T-010 (online, em andamento)
Fez: travou T-005/T-010; worktrees agents/claude-net/{ps3recomp,allstars-ps3} (branch claude-net/main, de claude/main).
Levantou HLE de rede (sys_net real em libs/network/sysNet.c existe mas NÃO está ligado; ppu_sysprx.cpp registra modelo offline,
connect/send/listen/accept sem HLE). Decompilou 792 funções (lib OTG 0x978000-0x9A0000 + rede do jogo) em work/decomp_otg
(fora do git; heavy_slot usado). OTG: TCP puro não bloqueante (SocketTcp 0x98E908), DNS próprio via UDP:53 para
cellNetCtlGetInfo(PRIMARY_DNS) (0x9930F8/0x9937F8), estados de ClientServerConnection 0x98A748 (jumptable 0x98A784).
LAN (Network Versus, pista CircleButton 1.12): por assinatura de código no 1.00 HostLanLobby=0x2FE00C (33/48 instr. iguais),
JoinLanLobby=0x2FE36C (48/48), g_VersusLanFlag provável=0x025332F8 (TOC r2-0x3398 -> slot 0xC813D0; não validado).
Xrefs em online/notes/xrefs_otg*.txt.
Pendências: validar a flag, quem a lê, socket tipo 6/porta 3658/beacon 45 71 29 no 1.00; porta+cabeçalho OTG; CryptManager.

## AAAA-MM-DD HH:MM — <agente> — <tarefa(s)>
Fez: ...
Resultado/evidência: comando(s) + o que saiu (logs em work/runs/<tag>.*)
Mudou arquivos: ...  (commits: repo@hash)
Pendências / próximo passo: ...
Avisos para outros agentes: ...
```

---

## 2026-10-14 15:05 — claude (thread "Investigação e testes no PC") — T-024: notas da parada dos ~135 s (sem perfil)
Fez: 1 execução de 200 s da integração (build\, PAD_SCRIPT START 100/105 s, SPU_TASKTIME=1, PORT_GSTACK=120,150,175).
Resultado/evidência (work/runs/claude-slow1.*): flips 2180 aos 110 s → 2320 aos 121 s → +10/10 s depois (≈1 fps).
- Tarefas SPURS da spu_0001 (image=2): ~5/10 s antes, ~8/s depois (≈8 por quadro). Cada uma é rápida:
  run mediano 2,4–4,2 ms, máx. 16 ms; fila (queued) ~3 ms. 666 tarefas image=2 na execução, todas retornam.
  Mesmo em série isso dá ~60 ms por quadro → não explica 1 fps sozinho.
- Pilhas guest: aos 120 s main em 0x57588 (espera handle==3 com usleep(5)); aos 150 s main em 0x66994/0x65B28 e
  Render dentro de cellSpursCreateTask (lr 0x34D910, r3=taskset 0x40018A00); aos 175 s main E Render ambos no mesmo
  wrapper 0x34D9xx → `bl 0xB0B288` = stub de cellSpursCreateTask (taskset 0x40018A00). CreateTask segura TASK_LOCK
  enquanto chama spu_workload_dispatch_task_async (cria uma thread do host por tarefa).
- Fora do caminho: sys_timer_usleep >= 1 ms usa CreateWaitableTimerW SEM HIGH_RESOLUTION → arredonda para ~15,6 ms
  (brbDriver/áudio usa 1000 us; 0xA94D54 e 0x79F74 usam 10 ms). Sub-ms é spin QPC + SwitchToThread.
- Log: ~200 linhas/s de "[WAIT] event_queue_receive" do _cellsurMixerMain (tid 15) — ruído, não causa.
Conclusão: não é a GPU nem a duração das tarefas SPU; o tempo está em código PPU (main/Render) entre as tarefas.
Precisa do perfil por amostragem (PORT_PROF da frente de CPU, T-019) para nomear a função.
Pendências: cruzar com o relatório PORT_PROF; testar CREATE_WAITABLE_TIMER_HIGH_RESOLUTION no usleep >= 1 ms.

## 2026-10-14 14:40 — claude (thread "Investigação e testes no PC") — integração de claude/main (T-011/T-017)
Fez: trava INTEGRATION → `git merge --no-ff claude/main` em src/ps3recomp (777cce0: tarefas SPURS por id + slots
liberados, cache de PSO por hash, SPU_ATOM_IMG) e src/allstars-ps3 (b16f056: PORT_HANGPROBE) → `scripts\build.bat Release`
pela heavy_slot (OK) → smoke 200 s com trava GPU e PAD_SCRIPT=START (100/105 s).
Resultado/evidência: work/runs/int3-smoke.err.log: título ~180 fps (sem relógio de quadros na integração), depois do
START ~30 fps até ~135 s (2690 flips), depois quase parado (2720 aos 187 s) — mesmo padrão das builds claude/claude-gpu
(bloqueio novo pós-diálogo do tutorial, ver entrada "noite, fim"). 0 [CRASH], 0 BRANCH-TO-0, 0 HANGPROBE, 0 NOMEM.
Antes, build\ (10:24) só chegava ao título. Sem regressão.
Mudou: src/ps3recomp@777cce0, src/allstars-ps3@b16f056 (merges locais, sem push); TASKS T-017 → concluída. INTEGRATION liberada.
Avisos: as branches claude-cpu/claude-rt/claude-gpu/claude-net partem de claude/main@5b3ce96 → já contêm tudo isso.

## 2026-10-14 14:40 — claude-gpu — T-013 cores do menu: CORRIGIDA no worktree
Causa (observada no código): o cache de PSO é chaveado pelo hash do CÓDIGO do FP (sem as constantes inline,
para não recompilar a cada cópia do anel de programas), mas o backend compilava com `rsx_fp_decompile`, que embute
as constantes como literais. Resultado: todo draw com o mesmo código herdava as constantes (cores) da primeira cópia
compilada. O fp_k[] que o backend enviava em b1 por draw não era lido por shader nenhum (layout antigo
texscale/alphatest/fp_k, sobra de antes da troca de decompilador).
Correção (ps3recomp@79e0b36): compila com `rsx_fp_decompile_buffered_ex` (fp_constants[n] + fp_alpha em b1);
vp_record_cb preenche b1 na GRAVAÇÃO do draw a partir da própria cópia do ucode; VP_FPCB_STRIDE 4096 (até 255
constantes; acima disso volta a literais + hash de todos os bytes). `rsx_fp_extract_consts`/`rsx_fp_code_hash`
agora contam constantes como o decompilador (antes pulavam palavras de branch → índices deslocados).
FP_CONSTBUF=0 = modo antigo (literal) para A/B. Diagnóstico novo: [FPRING] compara o hash do programa na gravação
e no replay (o PSO é montado no replay a partir de fp_addr).
Evidência: claude-gpu-t013a (200 s, mesmos parâmetros, RSX_CAP=2640:2:120 → work/runs/claude-gpu-t013a/frame_01,
quadro 2760): texto do menu azul sobre painéis prateados, item selecionado vermelho, rodapé azul. Antes (rs2cap2,
mesmo quadro): texto vinho/escuro sobre bege. [FPRING] 0 divergências em 20000 draws (o anel não é problema).
Flips iguais (título 20–30/s), PSO MISS total 65 (vs0b: 78), sem erro D3D12. test_fp_decompiler 36/36.
Pendências: o miolo do diálogo do tutorial ficou dourado/bege (não sei se é o original); o alpha test não é
aplicado pelos shaders do decompilador novo (b1 antigo tinha rsx_alphatest; `rsx_fp_apply_alpha_test` existe e
não é chamada) — vale uma tarefa. Integrar via INTEGRATION.

## 2026-10-14 14:30 — claude-gpu — T-021 (present/vblank QPC, cache de shaders, resolução interna)
Fez: conferiu claude-gpu-vs1/vs0a/vs0b (já feitas pela frente de análise) e rodou claude-gpu-rs2 (RSX_RES_SCALE=2).
O exe do build1 (13:44) NÃO tinha RSX_RES_SCALE (backend/fp_decompiler editados às 13:45-13:46): rebuild (build2.log, rc=0)
e a 1ª tentativa de rs2 foi descartada (renomeada *-rs2-exeantigo*). Testes unitários: test_fp_decompiler 36/36, test_shader_cache OK.
Resultado/evidência (200 s, PAD_SCRIPT 100/105 s, PERF=1, GCM_FLIPCOUNT=1; flips/s por janela de 20 s):
- título (20-100 s): vs1 19.5/25.1/22.8/29.9/29.3; vs0b 20.0/24.6/22.5/28.8/23.8; antes (claude-perf2, código velho) 20.2/24.7/22.1/28.4/25.2
  → **sem ganho de fps**: o limite é o guest (PERF guest 99-100%, present 1-3%, gpuwait 0%). RSX_VSYNC não é o gargalo.
- boot: present de boot caiu de 180 fps (perf2) para ~52 (1 por vblank, como planejado).
- depois do Start (120 s+): 1.2-2.2 flips/s, guest 100% (9-17 s de guest por janela); vs0a entrou nisso já aos ~65 s
  (abriu todos os .psarc de personagens/fases nesse momento) — é carga do lado CPU/SPU, não GPU.
- cache de shaders: vs1 (cache vazio) shc miss 4 no boot; vs0a/vs0b shc hit 4 miss 0 no boot, ~41-104 hit / 0-4 miss no fim; fxc ≤0.03 s/janela.
- PSO: MISS ainda ocorre (vs0a: 15 MISS, pso 1.13 s = 44% numa janela) — PSO não vai para disco (pendência).
- rs2: 0 [D3D12] ERROR / STUCK / device removed; flips iguais ao 1x (título ~24-30/s, pós-Start 3.4-4.2/s).
  RSX_CAP (claude-gpu-rs2cap, rs2cap2): backbuffer 2560x1440 com título completo e menu principal completo
  (diálogo do tutorial), mesmas cores erradas do 1x (T-013). Capturas só em work/runs (não sair do PC).
Mudou arquivos: ps3recomp@4a5b1f1 e allstars-ps3@9f3b567 (feitos pela frente de análise), ps3recomp@b5fe333
(rsx_fp_decompiler.c/.h + teste: WPOS / escala).
Pendências / próximo passo: T-013 (cores do menu); cache de PSO em disco; o ganho de fps no título depende do guest (CPU).
Avisos: screenshots da área de trabalho pegam a tela do Samuel (o jogo fica atrás) — use RSX_CAP + RSX_CAP_DIR.

## 2026-10-14 (noite, fim) — claude — T-017 corrigida; novo bloqueio no diálogo do tutorial
Fez: relift da spu_0001 com +0x4DC0,0x5050 (spu_discover3: 1 iteração, sem novos alvos). LIFT liberada.
Resultado/evidência: claude-stab1..3 (230 s cada): 0 HANGPROBE, 0 BRANCH-TO-0, 114–366 tarefas spu_0001 concluídas.
Menu principal desenhado completo (Solo Play, Tournament, Versus...) com o diálogo "Welcome... Tutorial? X YES / O NO".
Novo bloqueio (determinístico nas 3): depois de X (0x4000) no diálogo, os flips param entre 140 e 160 s; últimas linhas
do log são "[RSX] label write @0x20000400 = 2..7 (sync fence)". Provável início de carregamento (tutorial).
Próximo passo: PORT_GSTACK nos 150–170 s, ver onde main/Render esperam; testar O (0x2000) = NO em vez de X.
Texto do menu continua borrado/cores erradas (T-013).

## 2026-10-14 13:50 — claude (thread frente 1) — T-018 inventário do jogo; T-022 fila de trabalho pesado
Fez: (1) `scripts/jogo_inventory.py` (só leitura) → `analysis/jogo/{inventario,elf_1.00,elf_1.12}.json` e resumo em
`docs/jogo.md`: dump JB BCUS98472 1.00 (SDK 4.20, fw 4.25), update 1.12 no RPCS3 e pkgs 1.04/DLC fix, entry/TOC,
segmentos, seções (nomes zerados no ELF decriptado → inferidos), 376 imports/25 libs (250 com HLE hoje), 15 módulos
via cellSysmoduleLoadModule, 67 syscalls diretas, 3 ELFs SPU, formatos de dados, toolchain (falta só o Vulkan SDK).
(2) `scripts/heavy_slot.py`: fila FIFO de 2 vagas para build/lift/jogo (pedido do Samuel), documentada em AGENTS.md §3.8.
Testado com 3 jobs concorrentes (3º esperou e entrou), vaga de PID morto liberada, código de saída repassado.
(3) Worktrees `agents/claude-gpu/{ps3recomp,allstars-ps3}` (branch claude-gpu/main a partir de claude/main).
Resultado/evidência: `python scripts/jogo_inventory.py` → "1.00 imports 376 libs 25 syscalls 67 spu 3 mods 16".
Mudou arquivos: scripts/jogo_inventory.py, scripts/heavy_slot.py, docs/jogo.md, AGENTS.md.
Avisos: o VFS do port criou pastas vazias dentro do dump (`game/BCUS98472/USRDIR`, `PSASBRCACHE`); montagens
graváveis deveriam ficar fora da pasta do jogo. Use a fila para todo build/execução.

## 2026-10-14 13:38 — claude-cpu — T-019 (setup)
Fez: criei T-019 (área A) e travei; worktrees agents/claude-cpu/{ps3recomp,allstars-ps3} na branch claude-cpu/main
(a partir de claude/main: ps3recomp@5b3ce96, allstars-ps3@de1341b). Build baseline OK.
Resultado/evidência: `scripts\build.bat Release claude-cpu` → rc=0 em 112 s (work/runs/claude-cpu-build0.log),
build-claude-cpu/MyGameRecomp.exe 75,6 MB. Jogo não foi executado.
Fila de pesados: outra sessão já criou scripts/heavy_slot.py (2 vagas, FIFO); usei-a (vaga 0 durante o build) em vez
de criar outra. Não alterei scripts/build.bat.
Pendências / próximo passo: aguardando instruções da coordenação (fallback interpretador SPU + docs/cpu-abi.md).

---

## 2026-10-14 (noite) — claude-rt — T-020 (áudio) / T-012 (teclado), parcial
Fez: worktrees agents/claude-rt/* (branch claude-rt/main, a partir de claude/main), build-claude-rt.
(1) PM WWS do SCREAM (EA 0xC24200, 12288 B, fp 0xB10194F68CD38498) extraído em work/spu/jobs_rt/ e liftado em
work/spu/lifted_rt/pm_wwsjob_C24200 (base LS 0xA00, extra 0xA2C,0x3258, force-indirect 0x2E74 = mesmo job manager do
LBP), registrado como image 20 em work/spu/lifted_rt/rt_register.c. Hacks LBP `image_id==2` do runtime agora usam
g_spu_wwsjob_image/g_spu_wwsjob_fallback_image (LBP 2/1; All-Stars 20/0) → não disparam mais para a spu_0001.
(2) cellAudio: AUTOCONVERTPCM+SRC_DEFAULT_QUALITY, mixer segue o relógio do WASAPI (1 bloco = 1 evento), fallback por QPC.
(3) cellPad: mapa de teclado de luta configurável (keymap.ini ao lado do exe / PAD_KEYMAP_FILE / PAD_KEYMAP).
Resultado/evidência: claude-rt-audio1 (120 s, AUDIO_PEAK=1): "WASAPI up: event, buffer=1920, period=480, fill
target=1248"; ~21000 blocos em ~112 s (187,5/s); "wid=0 PM resolved (image=20)" e o PM é despachado. MAS o SCREAM
ainda falha: "snd_StartSoundSystemEx returned -4" ANTES do 1º despacho do PM → a falha não é (só) o PM.
snd_StartSoundSystemEx = 0xA71658 (decomp em work/decomp/00a71658_*.c): -4 vem de FUN_00a8ede8, FUN_00a87800 ou
FUN_00a8d3b8 (provável init síncrono que espera o SPU/workload ou HLE faltando). Pico do mix = 0 (sem PCM nos ports).
Mudou arquivos: ps3recomp@fdffa4a, allstars-ps3@d613b80 (branch claude-rt/main); work/spu/{jobs_rt,lifted_rt}.
Pendências: decompilar 0xA8EDE8/0xA87800/0xA8D3B8 e achar o -4; depois jobs SPU do SCREAM ([spu-ovl]/dispatch MISS);
_cellsurMixerMain; testar teclado no jogo; docs/audio.md. Não integrado.
Avisos: build do claude-rt pega work/spu/lifted_rt automaticamente (SPU_EXTRA_DIRS).

## 2026-10-14 (noite) — claude — T-017: causa encontrada (função SPU não liftada)
Fez: repeti execuções curtas com SPU_ATOMTRACE=3000 SPU_ATOM_IMG=2 (filtro novo em spu_channels.c) até travar.
Resultado/evidência: claude-rep3: handle preso em 2. A tarefa spu_0001 fez o 1º incremento atômico do handle
(lr 0x2CB34) e chamou método virtual 0x4DC0 (não liftado) → [wws-jobentry] + BRANCH-TO-0 unresolved → abortou sem o
2º incremento (lr 0x2CCDC). Também falta 0x5050 (claude-perf2). Não era corrida/concorrência.
Mudou arquivos: extras +0x4DC0,0x5050; spu_channels.c (SPU_ATOM_IMG, ainda não commitado); docs/CONTEXTO_COMPLETO.md.
Pendências / próximo passo: spu_discover.sh rodando (work/runs/spu_discover3.log, trava LIFT); depois rodar 3x sem
travar e commitar; integrar em src/.
Avisos: antes de suspeitar de corrida, grep "BRANCH-TO-0 unresolved\|wws-jobentry] pc" no err.log.

## 2026-10-14 (tarde) — claude — T-011: menu destravado + desempenho
Fez: (1) cellSpursCreateTask tinha corrida: o id/taskset ia para a thread SPU via globais e duas
threads PPU criam tarefas ao mesmo tempo (task 5 rodou com args da 6; a 5 nunca rodou). Agora o id vai
explícito (spu_workload_dispatch_task_async) e a criação é serializada (TASK_LOCK). (2) Slots de tarefa
nunca eram liberados: a 129ª CreateTask dava NOMEM e o menu travava em 0x57588 (espera handle==3).
Agora cellSpurs_task_exited libera o slot e os bits do taskset quando o programa SPU retorna.
(3) Depois do START o jogo ia a ~1 fps: PERF=1 mostrou 99% do quadro criando PSO. O cache de FP era
chaveado pelo endereço, e o jogo copia cada FP para um ring buffer por draw. Agora a chave é o hash do código
(constantes já vão por b1/fp_k). Resultado: 0 MISS, RSX ~30 fps.
Resultado/evidência: claude-taskfix1 (715 tarefas, sem NOMEM/travamento), claude-perf1 vs claude-perf2
(pso 99% -> 0%), claude-lock1 (340 tarefas, aparecem comandos novos cmd=6).
Mudou arquivos: ps3recomp@bb13c0a (cellSpurs.c, spu_workload.c/.h, rsx_d3d12_backend.c, spu_lifted_job.h,
sys_ppu_thread.c), allstars-ps3@de1341b (PORT_HANGPROBE).
Pendências / próximo passo: numa execução (claude-perf2) 2 de 20 tarefas spu_0001 nunca retornaram e o jogo
parou aos 117 s. Suspeita: duas tarefas concorrentes no lock em 0x4001D500 (ticket lock via GETLLAR/PUTLLC,
SPU_ATOM_EA=4001D500). Intermitente. Integrar na branch allstars-port depois de validar.
Avisos para outros agentes: SPU_TASKTIME=1 e PERF=1 são os primeiros a usar para lentidão.

## 2026-10-14 11:36 — astra — T-007 concluída; achado T-015
Fez: harness offline extrai corpos/helpers intactos do C gerado 1.00, compila DLL x64
com clang-cl e compara contra bytes do ELF no Unicorn PPC64. Adaptador de memória limitado,
32 GPRs/CR/XER/LR/CTR + 8192 bytes comparados; inputs reproduzíveis e hashes no relatório.
Resultado/evidência:
- `.\.venv\Scripts\python.exe tools\difftest\run.py --cases 1024`: 18 funções,
  18.432 casos, 17.924 equivalentes e 508 divergentes (exit 1 intencional por divergência).
- Todos os 508 são `func_0047E550`, CR xor 1, com XER.SO=1. SO=0 passou 516/516.
  C gerado de `cmplwi` não copia SO para CR7. Outras 17 funções passaram 1024/1024.
- `.\.venv\Scripts\python.exe -m unittest discover -s tools\difftest -p 'test_*.py' -v`:
  4 testes OK (flags arquiteturais, CR/unsigned/SO, store big-endian e comparador).
  Controles negativos de saída adulterada e memória fora dos limites também detectados.
- Relatório `reports/difftest-1.00.json`, saída `reports/difftest-tests.txt`, snapshots/build
  em `analysis/difftest-astra/` (ignorados). Hashes dos fontes de origem conferidos após teste.
Mudou arquivos: tools/difftest/{run.py,bridge.cpp,test_oracle.py}, docs/DIFFTEST.md;
commit local raiz `67012ff`; coord/TASKS.md atualizado. Nenhum runtime/gerado compartilhado alterado.
Pendências / próximo passo: T-015 livre para corrigir o lifter e ampliar regressão a outras
comparações/campos CR. Inspeção sugere omissão semelhante nas demais comparações inteiras;
confirmado dinamicamente apenas cmplwi nesta amostra.
Avisos para outros agentes: Claude, evidência/reprodução em docs/DIFFTEST.md. Não há evidência
de que SO explique o bloqueio do menu/SPU; não mudou estado de boot, não rodei o jogo.
T-007 será liberada. Integração/relift exigem suas respectivas travas.

## 2026-10-14 11:23 — astra — T-004 concluída (extrator PSARC)
Fez: implementou index/verify/extract em `tools/psarc_extract.py`, usando o perfil do ELF 1.00 e
material AES lido em memória pelos segmentos PPU/SPU. Nenhuma chave gravada ou impressa.
Resultado/evidência:
- `tools/psarc_extract.py index <USRDIR> --elf work/eboot/EBOOT_1.00_disc.elf --report reports/psarc-index.json`:
  48 manifests decodificados, 33.552 nomes; MD5 de todos os nomes confere com a TOC.
- `tools/psarc_extract.py verify <USRDIR> --elf work/eboot/EBOOT_1.00_disc.elf --report reports/psarc-validation.json`:
  48/48 pacotes, 3.691.348.922 bytes, zero erros; SHA-256 por recurso. 82.455 blocos comprimidos e 25 crus,
  sem contar manifests. **Achado adicional:** trailer Adler-32 de 4 bytes após o raw deflate, validado em todos.
- `extract .../global.psarc --output analysis/psarc-astra/global --report analysis/psarc-astra/global-extraction.json`:
  manifest 2403 bytes; 70 arquivos/25.610.876 bytes extraídos, tamanhos e SHA-256 conferidos após escrita.
- `.\.venv\Scripts\python.exe -m unittest discover -s tools -p 'test_psarc*.py' -v`: 16 testes OK;
  cobertura inclui múltiplos blocos, dados crus, arquivo vazio, corrupção, limites, paths e não sobrescrita.
  Log em `reports/psarc-tests.txt`; comandos completos em `docs/PSARC.md`.
Mudou arquivos: tools/psarc_extract.py, tools/test_psarc_extract.py, docs/PSARC.md (commit raiz `a83dbb8`);
reports/psarc-*, analysis/psarc-astra/ (ignorados); PLANO.md e coord/TASKS.md atualizados.
Worktrees astra atualizados por fast-forward para integração daf6f90 / 0405f5c. Runtime e dados fonte intactos.
Pendências: perfis 1.12 e interpretação de formatos internos não cobertos. T-014 criada para consolidar
textos históricos desatualizados, fora do escopo da T-004.
Avisos para Claude: extrator e nomes disponíveis; não foi necessário alterar src/, código lifted ou seu build.
A primeira validação estrita rejeitou o trailer; após identificá-lo como Adler-32, foi validado explicitamente.
T-004 e ASTRA-PSARC-DOC liberadas ao encerrar. Sem download/instalação/rede/publicação nesta tarefa.

## 2026-10-14 11:25 — claude — TELA DE TÍTULO (INLINE_ARRAY, JC_RESUME) + integração
Resultado: **o port nativo chega à tela de título "PRESS START"** (logo texturizado correto) e continua
fazendo flips estável (1750 flips em 172 s, sem travar). Primeiro a tela legal de copyright, depois o título.
Correções (ps3recomp `claude/main`):
- `rsx: NV4097_INLINE_ARRAY (0x1818)` — vértices embutidos no FIFO eram ignorados (UI 2D inteira sumia).
- `spurs: JC_RESUME` — job chain recomeçava do início a cada Run e reexecutava jobs antigos → contadores
  de conclusão duplicados → pool de pacotes de render (128 blocos, func 0x560FC) nunca reciclava →
  travava após ~1300 frames. Agora retoma do END onde parou (default no port).
Integração: trava INTEGRATION → merge `claude/main` em `src/ps3recomp` (daf6f90) e `src/allstars-ps3`
(0405f5c) → build `build\` → smoke 170 s chega ao título (`work/runs/cap-int2`) → trava liberada.
Defaults do port (main.cpp): SAIL_SKIP_MOVIES=1, GCM_PARK_WAIT=1, JC_RESUME=1.
Capturas: `RSX_CAP=<frame>:<n>:<passo> RSX_CAP_DIR=<pasta>` + `scripts/bmp2png.py` (screenshots ficam em
`docs/marcos/`, fora do git).
Próximo (T-011): apertar START e chegar aos menus.

## 2026-10-14 10:40 — claude — T-001 (resolvida), T-002 (resolvida), T-003 (contornada)
Fez / resultado (branches `claude/main` em agents/claude/ps3recomp e agents/claude/allstars-ps3):
- **T-001 causa raiz:** o meu HLE de `_cellSpursLFQueuePushBody` tratava TODO push como pedido Edge;
  a fila do `Renderer_SPU` (1024 B/elem) passava pelo mesmo NID e fazia memcpy em endereços aleatórios
  (sobrescrevia `gCellGcmCurrentContext`) → "stuck calling 0x40304". Achado com breakpoints de hardware
  (`PORT_DRWATCH`, DR0–DR3). Correção: roteia por tamanho de elemento; push PPU2SPU real do SDK
  (CellSyncLFQueue, GetPushPointer/CompletePushPointer) + override de `_cellSpursLFQueueInitialize`.
- **T-002:** `HALT-ASSERT heqi pc=0x8DF8` era checagem de estouro de pilha do SPU (r1 word1 = espaço livre);
  `spurs_job.c` agora preenche r1 word1.
- **FIFO:** heurísticas "jump-park"/"stuck-get" pulavam segmentos preenchidos pelo SPU (labels perdidos).
  `GCM_PARK_WAIT=1` (default no port) espera o park ser corrigido como o RSX real.
- **T-003:** vídeo de abertura: sem decoder, o jogo esperava o fim do stream. `SAIL_SKIP_MOVIES=1`
  (default no port) emite PLAYER_STATE_CHANGED→OPENED logo após Start; o handler do jogo (0x16F05C) encerra o vídeo.
- **Estado agora:** o jogo passa do vídeo, monta TODOS os .psarc (personagens/fases/bosslevel/cinematics),
  e entra no loop do frontend **fazendo flips a ~20 fps**. Tela ainda preta: capturas (`RSX_CAP`) mostram só
  clear + quad de pós-processo por frame.
- **Próximo:** histograma do FIFO (`TCONST_FIFO=1`) mostra que o conteúdo é desenhado com
  **NV4097_INLINE_ARRAY (0x1818, ~2,7 M dwords) + BEGIN_END (0x1808)** — o backend D3D12 só registra
  DRAW_INDEX_ARRAY. Implementar INLINE_ARRAY no backend é o próximo passo para aparecer imagem.
Ferramentas novas: `PORT_PEEK`, `PORT_WATCH`, `PORT_DRWATCH`, `PORT_FIFODUMP`, `scripts/bmp2png.py`, `sym.py --build`.
Commits: agents/claude/ps3recomp `claude/main`, agents/claude/allstars-ps3 `claude/main` (ainda não integrados em src/).

## 2026-10-14 09:10 — claude — T-001 (em andamento, trava renovada)
Fez: investigou o abort "stuck calling 0x00040304" do run14 (`work/run14.err.log` l.15805–16204).
Resultado: chamada indireta da thread Render (lr `0x0050736C`, `func_00507330` → `bl 0x9BA208` →
stub TOC → `func_0097F068`). `0x00040304` é palavra de comando RSX, não código; antes houve
`bctr to NULL` em `func_0097FA18+0x150` com OPD `0x44000028`. `0x97FB40..` = gcmReserve inline
(`lwz current,8(ctx)`, `lwz end,4(ctx)`, estouro → `callback` em +0xC). Conclusão provisória
(inferência): o contexto GCM usado pela thread Render não é válido quando o buffer enche.
Próximo passo: descobrir de onde vem o ctx de `func_0097FA18`/`0x97FB40` (r3) — instrumentar
`hle_gcm_callback`/`cellGcm_fifo_recycle` e logar ctx/callback de cada contexto que o jogo cria;
comparar com o fluxo no RPCS3.
Commits: nenhum código novo nesta etapa.

## 2026-10-14 08:55 — claude — coordenação
Fez: criou `AGENTS.md`, `CLAUDE.md`, `coord/TASKS.md`, este LOG, `scripts/claim.py` (travas atômicas),
worktrees `agents/claude/*` e `agents/astra/*` (branches `<agente>/main` a partir de `allstars-port`);
`scripts/build.bat` e `scripts/run.ps1` aceitam agente (build-<agente>/, logs em work/runs/).
Avisos: `src/` agora é integração — não editar direto. `.venv` é compartilhado (o `python -m venv` do
claude rodou sobre o venv do codex às 07:56; unicorn 2.1.4 continua instalado).

## 2026-10-14 07:50–08:50 — claude — boot do port (resumo da sessão)
Fez (detalhes em `PLANO.md`):
- Clonou ps3recomp@39e4f49 + allstars-ps3; patch do autor estava em UTF-16 → convertido e aplicado.
- Lift 1.00: 25.544 funções PPU, 1.098 handlers HLE; build `MyGameRecomp.exe` (clang-cl 23).
- Corrigiu o travamento do FIOS: `sys_lwcond_t` é {be32 lwmutex, be32 id}; o HLE gravava be64.
- Achou o descompressor: FIOS envia pedidos Edge zlib via `_cellSpursLFQueuePushBody` (não implementado).
  Blocos `.psarc` são **AES-256-CTR** (chave/IV na imagem SPU `spu_0002`) + raw deflate → HLE no host.
- Corrigiu `sceNpGetNpId`, PAMF sem init, use-after-free em `spu_coh_notify_write`; liftou o job Edge Geometry.
Resultado: boot chega ao loop principal (threads Render, áudio, PSN, troféus), carrega
global/shaders/bootup/titlescreen.psarc; sem imagem ainda. Run de referência: `work/run14.*` (90 s,
termina por `0x40304` → T-001).
Commits: ps3recomp@5203765 (branch allstars-port), allstars-ps3@4e0dec9 (allstars-port).
Próximo: T-001, T-002.

## 2026-10-14 06:08–06:26 — codex (GPT) — etapas 1–2 (resumo reconstruído do README/ROADMAP)
Fez: inventário do disco (`reports/inventory.json`), índice PSARC (`reports/psarc-index.json`,
manifests não decodificados — explicado depois: AES), ELFs 1.00/1.12 via RPCS3 isolado
(`analysis/*`), auditoria OPD/TOC/imports/SPU (`analysis/audit-*`), projeto Ghidra
`analysis/allstars-ppu-100.gpr`, prova nativa: função `0x004A70D4` traduzida à mão, 10.015 casos OK
contra Unicorn (`docs/NATIVE_PROOF.md`). Registrou REA no Codex (`~/.codex/config.toml`).
Ferramentas: `tools/*.py`, cópia ps3recomp@a2c2010 em `tools/ps3recomp`.
