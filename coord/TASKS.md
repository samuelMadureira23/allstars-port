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
| T-012 | Controle real: mapear XInput/teclado no `cellPad` do port (hoje só input scriptado). | livre | — | `agents/<a>/ps3recomp/libs/input/cellPad.c` |
| T-013 | Cores erradas no menu (texto avermelhado/escuro). Pista: cada draw usa um fragment program em endereço próprio (constantes de cor embutidas no microcódigo FP); verificar cache/patch de constantes FP no backend D3D12 (`libs/video/rsx_d3d12_backend.c`). Capturas: `RSX_CAP`. | livre | — | `agents/<a>/ps3recomp/libs/video/` |
| T-008 | Suporte ao EBOOT 1.12 (update + DLCs): relift, novos endereços (imagem SPU, LFQueue), validar decriptação psarc. | bloqueada (depois do 1.00 chegar ao título) | — | — |

## Área B — Recursos / assets (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-004 | Extrator de `.psarc` (`tools/psarc_extract.py`): blocos = u16 header + AES-256-CTR + raw deflate (algoritmo em `PLANO.md` e `src/allstars-ps3/stubs.cpp`). **A chave deve ser lida do ELF em tempo de execução** (imagem SPU em vaddr `0xB9F980`, LS `0x114C0`), nunca gravada. Validar: manifest do `global.psarc` bloco 0 → 2403 bytes. Atualizar `reports/psarc-index` com nomes. | livre | — | `tools/psarc_extract.py`, `docs/PSARC.md` |

## Área C — Online (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-005 | Engenharia reversa do protocolo OTG (`sceotClientServerConnect`, `otg::CryptManager`, mensagens TCP com `battleroyale-final.ps3.online.scea.com`): handshake, criptografia, formato das mensagens, fluxo de lobby/matchmaking. Só análise estática (Ghidra) por enquanto. | livre | — | `docs/ONLINE_PROTOCOLO.md`, `online/notes/` |
| T-006 | Levantar o estado do All-Stars Matchmaker (playallstars.org), PsasPs3Hooks e RPCN para este jogo; planejar teste no RPCS3 (IP/Hosts switches). **Sem baixar/instalar nada sem o usuário aprovar.** | livre | — | `docs/ONLINE_ACHADOS.md` (seção nova) |
| T-010 | Servidor substituto (protótipo local) a partir de T-005. | bloqueada (T-005) | — | `online/server/` |

## Área D — Verificação (sugerido: astra)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-007 | Teste diferencial: executar funções **lifted** (C gerado em `work/recompiled_1.00`) contra o oráculo Unicorn de `tools/prove_native.py` para N funções folha/com memória; reportar divergências de lifter. | livre | — | `tools/difftest/`, `reports/difftest-*.json` |

## Área E — Organização / publicação
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-009 | Enviar correções upstream (ps3recomp: lwcond layout, sceNp, PAMF, spu_coh_forget; allstars-ps3) — patches em `patches/`. | bloqueada (precisa aprovação do usuário para publicar) | — | `patches/` |
