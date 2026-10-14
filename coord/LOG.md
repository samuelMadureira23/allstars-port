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
