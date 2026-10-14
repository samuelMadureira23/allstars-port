# Diário de passagem (entrada mais nova no topo)

Modelo de entrada:
```
## AAAA-MM-DD HH:MM — <agente> — <tarefa(s)>
Fez: ...
Resultado/evidência: comando(s) + o que saiu (logs em work/runs/<tag>.*)
Mudou arquivos: ...  (commits: repo@hash)
Pendências / próximo passo: ...
Avisos para outros agentes: ...
```

---

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
