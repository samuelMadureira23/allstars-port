# AGENTS.md — manual comum para agentes de IA neste projeto

Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele vale para todos os
agentes (Claude, GPT/Codex, outros). O dono do projeto é o usuário (Samuel); ele
decide prioridades e aprova ações externas.

## 1. Objetivo
Port nativo para PC (Windows x64) de **PlayStation All-Stars Battle Royale**
(PS3, BCUS98472, EBOOT 1.00 do disco) via recompilação estática (ps3recomp), e depois
**modo online funcional** (os servidores da Sony fecharam em 2018).

## 2. Leitura obrigatória, nesta ordem
1. `coord/TASKS.md` — quadro de tarefas (quem faz o quê).
2. `coord/LOG.md` — diário de passagem (o que cada agente fez, último primeiro).
3. `PLANO.md` — estado técnico detalhado do port (boot, bloqueios, correções).
4. `docs/ONLINE_ACHADOS.md` — tudo que se sabe sobre o online.
5. `docs/ROADMAP.md` e `docs/NATIVE_PROOF.md` — etapa inicial (inventário, prova nativa com Unicorn).
6. `python scripts/claim.py list` — travas ativas agora.

## 3. Protocolo de coordenação (obrigatório)
1. **Escolha uma tarefa** em `coord/TASKS.md` com status `livre` (ou atribuída a você).
2. **Trave-a antes de começar**, declarando os caminhos que vai alterar:
   `.\.venv\Scripts\python.exe scripts\claim.py claim T-00X <seu-nome> --paths <caminhos> --note "<resumo>"`
   Se falhar (já travada / conflito de caminho), escolha outra. Nunca apague trava alheia.
3. Atualize a linha da tarefa em `coord/TASKS.md` (status `em andamento`, dono = você).
4. **Trabalhe só na sua área** (seção 4). Não altere caminhos travados por outro agente
   (`scripts\claim.py check <caminho>`).
5. Ao parar (concluído, bloqueado ou fim de sessão):
   - escreva uma entrada **no topo** de `coord/LOG.md` (modelo no próprio arquivo);
   - atualize `coord/TASKS.md` e, se mudou o estado do port, `PLANO.md`;
   - `scripts\claim.py release T-00X <seu-nome>` (ou `renew` se continua depois).
6. Travas sem renovação há mais de 24 h podem ser liberadas **pelo usuário** (`--force`).
7. Achou algo fora da sua tarefa? Não conserte por conta própria: crie uma tarefa nova
   em `coord/TASKS.md` (status `livre`) e registre no LOG.
8. **Trabalho pesado entra na fila de 2 vagas** (pedido do Samuel, para o PC não pesar):
   build, lift/relift, rodar o jogo, Ghidra headless e testes longos. Ler/editar código não entra.
   Forma simples (pega a vaga, roda, devolve mesmo se falhar):
   `.\.venv\Scripts\python.exe scripts\heavy_slot.py run <seu-nome> --what "build" -- scripts\build.bat Release <seu-nome>`
   `.\.venv\Scripts\python.exe scripts\heavy_slot.py run <seu-nome> --what "jogo 200s" -- powershell -ExecutionPolicy Bypass -File scripts\run.ps1 -Agent <seu-nome> -Seconds 200 -Tag <seu-nome>-x`
   Ver quem está usando e quem espera: `heavy_slot.py status`. Para trabalho longo fora do `run`:
   `heavy_slot.py acquire <nome> --what "..." --ttl-min 120`, `renew <nome>`, `release <nome>`.
   A fila é por ordem de chegada; vaga de processo morto ou sem renovação expira sozinha.
   Rodar o jogo continua exigindo também a trava `GPU` (só uma janela do jogo por vez).

## 4. Áreas de trabalho (quem escreve onde)
| Caminho | Uso | Quem escreve |
|---|---|---|
| `agents/<nome>/ps3recomp`, `agents/<nome>/allstars-ps3` | **seu** git worktree (branch `<nome>/main` ou `<nome>/<tarefa>`) | só o dono |
| `build-<nome>/` | seu build (`scripts\build.bat Release <nome>`) | só o dono |
| `src/ps3recomp`, `src/allstars-ps3` | **integração** (branch `allstars-port`); só recebe merges | quem tiver a trava `INTEGRATION` |
| `build/` | build da integração | quem tiver `INTEGRATION` |
| `work/recompiled_1.00`, `work/spu/lifted` | código gerado pelos lifters (compartilhado, 500+ MB) | só com a trava `LIFT` |
| `work/eboot/` | EBOOTs decriptados (somente leitura) | ninguém |
| `work/runs/` | logs de execução: use `-Tag <nome>-<algo>` | todos (arquivos próprios) |
| `online/` | servidor substituto e ferramentas de protocolo (a criar) | dono da tarefa de online |
| `tools/`, `analysis/`, `reports/` | etapa inicial (Codex): inventário, auditoria, prova nativa | o autor ou com trava |
| `scripts/`, `docs/`, `coord/`, `PLANO.md`, `AGENTS.md` | compartilhados | com trava do caminho; `coord/LOG.md` e `coord/TASKS.md` podem ser editados por todos (edições curtas, sem apagar texto alheio) |

### Fluxo de código
`agents/<nome>/<repo>` (branch própria) → build e teste em `build-<nome>/` → trave
`INTEGRATION` → em `src/<repo>`: `git merge --no-ff <nome>/main` → `scripts\build.bat Release`
→ rode 60 s sem regressão → registre no LOG → libere `INTEGRATION`.
Antes de começar uma tarefa, atualize seu worktree: `git merge allstars-port`.
Commits: mensagem clara + linha de coautoria do seu agente. **Nunca** `push` para o GitHub
nem abra PR sem pedido explícito do usuário.

## 5. Ambiente (Windows 10, máquina do usuário)
- Python: `.\.venv\Scripts\python.exe` (capstone, pycryptodome, unicorn 2.1.4, construct, tqdm). `set PYTHONUTF8=1` para as ferramentas do ps3recomp.
- Compilação: VS 2026 Build Tools (MSVC 14.51, SDK 10.0.26100) + LLVM clang-cl 23 + CMake + Ninja.
- Ghidra 12.1.4: `C:\Users\samue\Documents\pes 13 descompilado\ferramentas\ghidra\ghidra_12.1.4_PUBLIC`,
  `JAVA_HOME=...\ferramentas\jdk21`. Projetos: `work/ghidra_proj` (Claude, com análise completa) e
  `analysis/allstars-ppu-100.gpr` (Codex). Linguagem: `PowerPC:BE:64:64-32addr`.
- RPCS3 0.0.43: `C:\Users\samue\Documents\rpcs3-v0.0.28-15372-38a5313e_win64` — tem o update 1.12
  instalado em `dev_hdd0/game/BCUS98472`. Não altere configurações/saves dele sem pedir.
- Jogo (somente leitura): `C:\Users\samue\Documents\[Downloadgameps3.com]PLUS\BCUS98472 - [Play Station All Stars Battle Royale]`
- REA (MCP) não aceita PowerPC → use Ghidra direto.

## 6. Comandos
```
scripts\build.bat Release <nome>                       # build do seu worktree -> build-<nome>\
powershell -ExecutionPolicy Bypass -File scripts\run.ps1 -Agent <nome> -Seconds 60 -Tag <nome>-x
  # PORT_GSTACK="20,40" -> pilhas guest de todas as threads nesses segundos
python scripts\decompile.py 0xADDR [...]               # Ghidra headless -> work\decomp\
python scripts\disasm.py 0xINI 0xFIM                   # assembly PPU (capstone)
python scripts\xref_str.py <elf> <functions.json> "texto"   # xrefs via TOC (Ghidra não resolve)
python scripts\sym.py 0xRVA                            # símbolo de um [CRASH] (usa build*\MyGameRecomp.map)
python scripts\list_imports.py <imports.json> --md out.md
```
Fatos úteis: TOC r2 = `0xC84768`; vaddr = offset do arquivo + `0x10000` no segmento de código;
imagem SPU do descompressor em `0xB9F980`; ver `PLANO.md` para todos os endereços.

## 7. Regras de evidência (herdadas do ROADMAP)
- Separe 1.00 e 1.12; nunca transfira endereços entre versões sem validar bytes.
- **Código novo não fixa endereço do 1.00** (para a migração futura ao 1.12 ser barata): identifique
  funções/dados do jogo por **assinatura de código** (sequência de instruções com máscara de operandos) ou
  pelo fingerprint da imagem SPU, como `spu_workload` já faz. Onde um endereço for inevitável, ponha-o numa
  **tabela de endereços por versão** (chave = SHA-256 do ELF), nunca solto no código. O integrador cobra isso
  antes de cada merge em `allstars-port`.
- Pseudocódigo do Ghidra é inferência, não código original. Diga o que foi observado,
  o que foi inferido e o que é desconhecido. Resultado negativo também vai para o LOG.
- Registre comando + resultado de cada teste que justificar uma conclusão.

## 8. Limites legais e de segurança
- **Não versione, não publique e não envie** para fora desta máquina: EBOOT/ELF decriptado,
  `.psarc`, áudio/vídeo/texturas do jogo, firmware, nem **chaves**. A chave AES dos `.psarc` é lida da
  memória do EBOOT em tempo de execução — mantenha assim (nunca escreva a chave em arquivo).
- Downloads, instalações, `push`, PRs, posts e qualquer coisa enviada a serviços externos: só com
  pedido explícito do usuário.
- Servidores do online: rode local (127.0.0.1/LAN) até o usuário decidir hospedar.
