# Quadro de tarefas

Status: `livre` · `em andamento` · `bloqueada` · `revisão` · `concluída`.
Antes de começar: trave com `scripts\claim.py claim <ID> <agente> --paths ...` (ver AGENTS.md §3).
"Sugerido" = recomendação do usuário/coordenação; qualquer agente pode pegar se estiver `livre`.
Novas tarefas: próximo ID livre, no fim da tabela da área.

## Área A — Boot / runtime do port (sugerido: claude)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-001 | Travamento "stuck calling 0x40304" (thread Render). Causa: HLE de `_cellSpursLFQueuePushBody` tratava a fila do Renderer_SPU como Edge e corrompia memória. Corrigido (push PPU2SPU real). | concluída | claude | — |
| T-002 | `HALT-ASSERT heqi pc=0x8DF8` no job Edge Geometry = checagem de pilha SPU (r1 word1). Corrigido em `spurs_job.c`. | concluída | claude | — |
| T-003 | `cellSail` (vídeos). Hoje: `SAIL_SKIP_MOVIES=1` encerra o vídeo no Start (o jogo segue). Falta: decodificar PAMF/AVC de verdade (GetFrame2) e áudio dos vídeos. | livre (contornada) | — | `agents/<a>/ps3recomp/libs/codec/cellSail.c` |
| T-011 | Passar da tela de título: apertar START (PAD_SCRIPT/PAD_FILE) e chegar aos menus; corrigir o que travar. | em andamento | claude | `agents/claude/*` |
| T-012 | Controle real: mapear XInput/teclado no `cellPad` do port (hoje só input scriptado). | em andamento | claude-rt | `agents/<a>/ps3recomp/libs/input/cellPad.c` |
| T-013 | Cores erradas no menu (texto avermelhado/escuro). Pista: cada draw usa um fragment program em endereço próprio (constantes de cor embutidas no microcódigo FP); verificar cache/patch de constantes FP no backend D3D12 (`libs/video/rsx_d3d12_backend.c`). Capturas: `RSX_CAP`. **Corrigida no worktree** (ps3recomp@79e0b36: constantes do FP por draw em b1); falta integrar. | feito (worktree) | claude-gpu | `agents/<a>/ps3recomp/libs/video/` |
| T-016 | Backend Vulkan (alternativa ao D3D12): mesmo contrato de `rsx_d3d12_backend.c`; permite Linux/Steam Deck e comparar desempenho. Depois que o jogo estiver jogável. | pausada (prioridade: jogo jogável) | claude-gpu | `agents/<a>/ps3recomp/libs/video/rsx_vulkan_backend.c` |
| T-017 | Travamento após START: era função SPU da spu_0001 chamada por vtable sem lift (0x4DC0, 0x5050) → tarefa abortava sem o 2º incremento do handle. Relift + extras; 3×230 s sem travar (claude-stab1..3). Integrado em allstars-port (ps3recomp 777cce0, allstars-ps3 b16f056). | concluída | claude | — |
| T-024 | Quase parada ~135 s após START (menu/diálogo do tutorial): fps cai para 1–2 com guest 100% e GPU ociosa; muitas tarefas spu_0001 por segundo. Achar a thread PPU / tarefa SPU que consome o tempo; combinar com T-019 (desempenho do código gerado). | em andamento | claude | `work/runs/claude-slow*` |
| T-021 | GPU/desempenho de vídeo (frente 4): present/vsync sem bloquear o drain do FIFO no relógio de quadros (suspeita do teto de ~30 fps), relógio de vblank com QPC, cache de shaders compilados em disco (sem stutter de 60–90 ms por PSO novo), resolução interna configurável; contrato em `docs/gpu.md`. Feito no worktree (ps3recomp@4a5b1f1+b5fe333, allstars-ps3@9f3b567); fps do título não mudou (limite é o guest); falta integrar e cache de PSO em disco. | feito (worktree) | claude-gpu | `agents/claude-gpu/*`, `build-claude-gpu/`, `docs/gpu.md` |
| T-019 | Recompilador: fallback do interpretador SPU completo para funções não liftadas + docs/cpu-abi.md (ABI PPU/SPU documentado). | em andamento | claude-cpu | `agents/claude-cpu/*`, `build-claude-cpu/`, `docs/cpu-abi.md` |
| T-020 | Áudio (jogo mudo): liftar o policy module WWS (EA 0xC24200, 12288 B) do workload SCREAM `Wws_Job`/`BrBDblBufWrkld` + jobs que ele carrega; cellAudio WASAPI (AUTOCONVERTPCM, mixer no relógio do dispositivo). | em andamento | claude-rt | `agents/claude-rt/*`, `work/spu/lifted_rt/`, `docs/audio.md` |
| T-008 | Suporte ao EBOOT 1.12 (update + DLCs): relift, novos endereços (imagem SPU, LFQueue), validar decriptação psarc. | bloqueada (depois do 1.00 chegar ao título) | — | — |
| T-028 | Menu de opções gráficas no port (resolução interna, fps, vsync...). Hoje são variáveis de ambiente: RSX_RES_SCALE, RSX_VSYNC, GCM_VBLANK_HZ, RSX_SHADER_CACHE, RSX_FXC_FAST (ver `docs/gpu.md`). Risco: fps acima de 60 (GCM_VBLANK_HZ maior) acelera a lógica do jogo se ela contar quadros em vez de tempo — investigar antes de oferecer fps desbloqueado. Nada de código por enquanto. | bloqueada (depois do jogo bem jogável) | — | — |

## Área B — Recursos / assets (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-004 | Extrator PSARC concluído: chave lida do ELF somente em memória; manifests/MD5 e conteúdos dos 48 pacotes verificados (33.552 entradas, 3.691.348.922 bytes, Adler-32 dos blocos comprimidos). `global.psarc`: manifest 2403 bytes/70 nomes; 70 arquivos extraídos e hashes conferidos. 16 testes passaram. Ver `docs/PSARC.md`. | concluída | astra | `tools/psarc_extract.py`, `tools/test_psarc_extract.py`, `docs/PSARC.md`, `reports/psarc-*`, `analysis/psarc-astra` |

## Área C — Online (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-005 | Engenharia reversa do protocolo OTG e do modo LAN "Network Versus". Feito: transporte TCP sem TLS, DNS próprio do OTG, HostLanLobby/JoinLanLobby/flag no 1.00 (ver docs/ONLINE_PROTOCOLO.md). Próximo: quem chama a vtable do lobby LAN, socket tipo 6/porta 3658/beacon no 1.00; porta/cabeçalho/CryptManager do OTG. | pausado (aguardando primeira luta jogável) | — | `docs/ONLINE_PROTOCOLO.md`, `online/notes/` |
| T-006 | Levantar o estado do All-Stars Matchmaker (playallstars.org), PsasPs3Hooks e RPCN para este jogo; planejar teste no RPCS3 (IP/Hosts switches). **Sem baixar/instalar nada sem o usuário aprovar.** | livre | — | `docs/ONLINE_ACHADOS.md` (seção nova) |
| T-010 | Servidor substituto: pronto em `net/server` (NPX, LAN virtual, DNS, STUN/TURN, HTTP, captura OTG; 23 testes), contrato em `docs/net.md`. Próximo: HLE sys_net real + DNS desviado + DGRAM_P2P + túnel no cliente; depois lobby OTG (depende de T-005). | pausado (aguardando primeira luta jogável) | — | `net/server/`, `docs/net.md` |

## Área D — Verificação (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-007 | Teste diferencial concluído: 18 funções C geradas, 18.432 casos; 17.924 equivalentes e 508 divergências em CR7.SO de `0x0047E550`. Demais 17 funções sem divergências na amostra. Quatro testes do oráculo e controles negativos passaram. Ver `docs/DIFFTEST.md`; correção em T-015. | concluída | astra | `tools/difftest/`, `reports/difftest-1.00.json`, `reports/difftest-tests.txt`, `analysis/difftest-astra/`, `docs/DIFFTEST.md` |
| T-015 | Corrigir cópia de XER.SO nos campos CR das comparações inteiras do lifter. Confirmado em `cmplwi`/`func_0047E550` pela T-007; inspecionar/testar demais famílias e CR0–CR7. Coordenar relift com Claude; obter LIFT/INTEGRATION antes de alterar gerados/integrar. Impacto no boot ainda desconhecido. | em andamento | astra | `agents/<a>/ps3recomp/tools/ppu_lifter.py`, testes; gerados somente com LIFT |
| T-027 | Teste de regressão automático antes de cada integração: comando único (`scripts
egress.ps1`) que roda o build com PAD_SCRIPT fixo, captura quadros com RSX_CAP em pontos fixos (título, menu, diálogo), compara com referências em `work
egress
ef\` (fora do git) com tolerância, falha em crash/[CRASH]/BRANCH-TO-0/device removed/queda de flips; `--update-ref`; aceita referências do RPCS3. | em andamento | claude-gpu | `scripts/regress.ps1`, `scripts/regress.py`, `work/regress/`, `docs/gpu.md`, AGENTS.md (seção integração) |

## Área E — Organização / publicação
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-009 | Enviar correções upstream (ps3recomp: lwcond layout, sceNp, PAMF, spu_coh_forget; allstars-ps3) — patches em `patches/`. | bloqueada (precisa aprovação do usuário para publicar) | — | `patches/` |
| T-014 | Consolidar documentação histórica: início do PLANO e ROADMAP ainda descrevem ferramentas ausentes/boot não iniciado; preservar evidência histórica e distinguir estado atual, sem afirmar que gameplay/online foram validados. | livre | — | `PLANO.md`, `docs/ROADMAP.md`, `README.md` |
| T-018 | Inventário do jogo (frente 1): dump, versões, EBOOT, imports/NIDs, syscalls, SPU, dados, toolchain → `docs/jogo.md`, `analysis/jogo/`, `scripts/jogo_inventory.py`. | concluída | claude | `docs/jogo.md`, `analysis/jogo` |
| T-022 | Fila de trabalho pesado (2 vagas, FIFO) para build/lift/rodar o jogo: `scripts/heavy_slot.py`, AGENTS.md §3.8. | concluída | claude | `scripts/heavy_slot.py` |
| T-023 | Alpha test no decompilador buffered: desde a troca de decompilador nenhum shader aplica o alpha test (rsx_alphatest antigo em b1 não é lido). Aplicar com função/ref por constante (fp_alpha) e só o bit ligado na chave do PSO. Validar com captura do menu e FP_CONSTBUF=0 como controle. | revisão (commit 8737462 fora da integração: com o alpha test o menu muda de azul para dourado/vermelho; falta referência do original) | — | `agents/claude-gpu/ps3recomp/libs/video/` |

## Meta final (definida pelo Samuel em 14/10/2026)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-026 | **Instalador do port**: o usuário aponta a pasta do próprio jogo → confere 1.00/1.12 pelo SHA-256 do EBOOT → usa o EBOOT que ele mesmo decriptou (ex.: RPCS3 com o firmware dele; nenhuma chave distribuída) → roda os lifters e compila localmente com toolchain empacotado → monta o executável. Nada do jogo nem código derivado sai do repositório. Não é para agora; até lá, todo passo do processo deve continuar scriptável: sem passos manuais escondidos, sem caminhos fixos desta máquina (ex.: pasta do jogo em `scripts/run.ps1`, caminho do VS em `scripts/build.bat`), sem depender de arquivos que não venham do jogo do usuário. O integrador cobra isso nos merges. | livre (meta final) | — | `installer/` (a criar), `scripts/` |
