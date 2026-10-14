# Quadro de tarefas

Status: `livre` · `em andamento` · `bloqueada` · `revisão` · `concluída`.
Antes de começar: trave com `scripts\claim.py claim <ID> <agente> --paths ...` (ver AGENTS.md §3).
"Sugerido" = recomendação do usuário/coordenação; qualquer agente pode pegar se estiver `livre`.
Novas tarefas: próximo ID livre, no fim da tabela da área.

## Área A — Boot / runtime do port (sugerido: claude)
| ID | Tarefa | Status | Dono | Caminhos principais |
|---|---|---|---|---|
| T-001 | Thread **Render** (tid 22) faz chamada indireta para `0x00040304` (runtime aborta: "stuck calling ... 2000 times"). **Não é função faltando:** `0x00040304` é um comando RSX (método 0x304, 1 arg) — o "objeto" lido aponta para dentro do buffer de comandos. Antes houve `bctr to NULL` em `func_0097FA18+0x150` (OPD `0x44000028` → `0x00FF0000`). `0x97FB40` é o `gcmReserve` inline: `ctx{begin@0,end@4,current@8,callback@C}`; buffer cheio → `callback`. Hipóteses: contexto GCM da thread Render corrompido/não inicializado, ou callback próprio do jogo não suportado pelo HLE (ver heurística "recycled the title's own ring", ctx=0x0F800000, ring 0x45C00000–0x46000000, em `libs/video/cellGcmSys.c` ~l.1742). Pode estar ligado a T-002. | em andamento | claude | `work/recompiled_1.00` (trava LIFT), `agents/<a>/ps3recomp/tools` |
| T-002 | Job SPURS Edge Geometry (img 10) dá `HALT-ASSERT heqi pc=0x08DF8`: descobrir qual assert (entrada do job? DMA list? lift?) e corrigir. | livre | — | `agents/<a>/ps3recomp/runtime/spu`, `work/spu/lifted/job_edgegeom` |
| T-003 | `cellSail`: vídeo de abertura (`movies/attract.pam`). Hoje é stub; `DescriptorCreateDatabase` não preenche o leitor PAMF. Meta mínima: o jogo pular o vídeo sem travar; depois tocar de verdade. | livre | — | `agents/<a>/ps3recomp/libs/codec/cellSail.c` |
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
