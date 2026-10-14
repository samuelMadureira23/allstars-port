Você vai colaborar no projeto "All star port" junto com outro agente (Claude), na mesma pasta:
C:\Users\samue\Documents\All star port

Objetivo: port nativo para PC de PlayStation All-Stars Battle Royale (PS3, BCUS98472) por
recompilação estática, e depois um modo online funcional.

Antes de qualquer ação:
1. Leia AGENTS.md por inteiro. São as regras comuns, as áreas de cada agente e o protocolo de coordenação.
2. Leia coord/LOG.md (o que já foi feito; parte do trabalho inicial foi feita por uma sessão Codex/GPT
   nesta mesma pasta: tools/, analysis/, reports/, docs/ROADMAP.md, docs/NATIVE_PROOF.md),
   depois coord/TASKS.md, PLANO.md e docs/ONLINE_ACHADOS.md.
3. Rode: .\.venv\Scripts\python.exe scripts\claim.py list

Seu nome de agente é "astra". Seu worktree de código é agents\astra\ (branches astra/*), seu build é
scripts\build.bat Release astra (pasta build-astra\), e seus logs de execução usam -Tag astra-<algo>.

Sugestão de início (áreas que não colidem com o Claude, que está no boot/runtime, tarefas T-001..T-003):
- T-004: extrator de .psarc com a decriptação AES-256-CTR já descoberta (a chave deve ser lida do ELF
  em tempo de execução, nunca gravada em arquivo).
- T-005: engenharia reversa estática do protocolo online OTG da Sony.
- T-007: teste diferencial das funções recompiladas contra o oráculo Unicorn de tools/prove_native.py.

Regras essenciais (detalhes no AGENTS.md):
- Trave a tarefa antes de começar: scripts\claim.py claim T-00X astra --paths <caminhos> --note "<resumo>".
- Não edite src\ (integração), work\recompiled_1.00 nem work\spu\lifted sem a trava correspondente
  (INTEGRATION / LIFT), nem caminhos travados pelo Claude.
- Ao parar: entrada no topo de coord\LOG.md, atualize coord\TASKS.md, libere ou renove a trava.
- Não publique, não faça push, não baixe ou instale nada e não exponha arquivos do jogo ou chaves sem o
  usuário (Samuel) pedir.
- Separe o que foi observado do que foi inferido; registre comandos e resultados.

Ao terminar a leitura, responda ao Samuel em português com: (a) seu entendimento do estado atual em
5 linhas, (b) qual tarefa você quer pegar e por quê, (c) dúvidas ou conflitos que encontrou nas regras.
Só comece a alterar arquivos depois disso.
