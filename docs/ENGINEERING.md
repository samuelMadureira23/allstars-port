# Documentação de engenharia e histórico do projeto

Este arquivo guarda o histórico técnico que antes ficava no README da raiz. Ele é interno, para quem contribui com o port, e não faz parte da apresentação pública.

> **Agentes de IA: comecem por [AGENTS.md](../AGENTS.md)** (regras, áreas e coordenação), depois [coord/TASKS.md](../coord/TASKS.md), [coord/LOG.md](../coord/LOG.md) e [PLANO.md](../PLANO.md). Respeitem as travas, a fila de trabalho pesado e a regressão antes de integrar.

## Estado em 14/10/2026 (registro histórico)

Executável nativo Windows x64/D3D12 chega ao título e ao menu principal com diálogo do tutorial. Naquele momento, uma luta jogável ainda não havia sido validada. Na integração, o bloqueio após o tutorial envolvia o ciclo de descarregamento de áudio (T-024/T-029). Em seu worktree, Claude já relatou HUD e lógica do tutorial com um atalho de áudio; o passe principal da cena 3D ainda não aparecia. O estado compartilhado e os responsáveis ficam em [coord/TASKS.md](../coord/TASKS.md) e [coord/LOG.md](../coord/LOG.md).

O estado atual do port, com o que roda e o que ainda falta, está no [README](../README.md).

## Trabalho daquele período

- Foco: passar do tutorial e entrar numa batalha na versão 1.00.
- T-004: 48 PSARC verificados e nomes recuperados; extrator em [PSARC.md](PSARC.md).
- T-007/T-015: teste do C gerado encontrou omissão de XER.SO; correção no worktree astra passou em 67.584 casos isolados. Build completo e integração têm validação separada: [DIFFTEST.md](DIFFTEST.md).
- Áudio, controles e desempenho tinham alterações em diferentes worktrees; trabalho pronto numa branch não implica que esteja no executável da integração.
- Online: análise OTG/LAN e protótipo local existiam, mas jogo online não havia sido validado. Essa frente aguardava uma luta local: [ONLINE_PROTOCOLO.md](ONLINE_PROTOCOLO.md).
- Compilação e execução: [AGENTS.md](../AGENTS.md). Toolchain já instalada; use o Python `.venv` e `scripts/heavy_slot.py` para trabalho pesado.

## Evidência histórica: primeira prova nativa

Foi executada uma primeira função traduzida manualmente em uma DLL nativa x64. Os 10.015 casos comparados com o oráculo PPC64 passaram para r3, r5 e os campos selecionados de XER. Escopo e reprodução em [NATIVE_PROOF.md](NATIVE_PROOF.md).

| Observação estática | Versão 1.00 | Versão 1.12 |
| --- | ---: | ---: |
| Descritores OPD | 16.989 | 17.176 |
| Entradas de código distintas na OPD | 12.775 | 12.924 |
| Imports de firmware | 376 | 378 |
| Bibliotecas importadas | 25 | 26 |
| Imports nomeados por banco NID | 345 | 350 |
| Imagens SPU extraídas e estruturalmente validadas | 3 | 3 |

As duas versões têm dois contextos TOC. As entradas OPD foram conferidas contra bytes, alinhamento, seções executáveis e memória carregada. Não são uma contagem exaustiva de funções. Os endereços finais estimados pelo loader não são limites de função comprovados. Resultados em `reports/stage2.json` e `analysis/audit-*`.

Ferramenta de leitura: ps3recomp, commit `a2c20108af45174dbb7d3e2f87f6acaaef09c6b4`, preservado em `tools/ps3recomp`. As análises PPU ficam em `analysis/ppu-1.00` e `analysis/ppu-1.12`. Esse checkout foi usado na análise inicial. O port compilado atual usa os repositórios `src/ps3recomp` e `src/allstars-ps3`, com worktrees por agente.

## Resultados verificados

- Inventário do disco BCUS98472 1.00: 23.933 arquivos, 6.308.711.424 bytes.
- 48 PSARC, com 33.552 entradas de recursos. A tentativa inicial com zlib comum falhou; a T-004 depois verificou os manifests, nomes e 3.691.348.922 bytes de conteúdo usando o material AES lido do ELF em memória. Formatos internos ainda não são todos interpretados.
- Encontrada atualização BCUS98472 1.12 na instalação local do RPCS3.
- ELF das duas versões obtido usando RPCS3 isolado, sem executar o jogo. Hash dos EBOOT originais conferido antes e depois: arquivos preservados.
- REA registrado no Codex; `rea doctor --client codex --json` retornou healthy=true. Ghidra 12.1.4 e JDK 21 já estavam instalados e foram reutilizados.
- O REA instalado rejeitou SELF e depois ELF PowerPC. Isso é uma limitação do caminho de importação do REA, não evidência de que Ghidra não suporte PowerPC.
- Ghidra direto reconheceu 1.233 funções na cópia de análise 1.00 e exportou três amostras de pseudocódigo. Não é cobertura completa nem código pronto para compilar.
- Detectadas três imagens ELF32 big-endian, machine=23 (SPU), embutidas em cada ELF. Segmentos, limites de arquivo e local store foram validados; execução e cobertura completa de tarefas SPU ainda não verificadas.

## Arquivos principais

| Caminho relativo | Conteúdo |
| --- | --- |
| `docs/ROADMAP.md` | Critérios de avanço, fontes e limites |
| `reports/inventory.json` | Inventário e PARAM.SFO do disco |
| `reports/psarc-index.json` | Índice atual de recursos com nomes recuperados pela T-004 |
| `reports/psarc-validation.json` | Verificação de conteúdo dos 48 PSARC |
| `docs/DIFFTEST.md` | Testes diferenciais do C gerado e correção XER.SO |
| `reports/elf-base-1.00.json` | Segmentos, seções e candidatos ELF embutidos |
| `reports/elf-update-1.12.json` | Relatório separado da atualização |
| `reports/rea-doctor-after.json` | Diagnóstico após configuração |
| `reports/rea-elf-overview.json` | Rejeição de arquitetura pelo REA |
| `analysis/base-1.00-isolated/EBOOT.elf` | ELF original obtido pelo RPCS3 |
| `analysis/update-1.12/EBOOT.elf` | ELF da atualização local |
| `analysis/base-1.00-isolated/provenance.json` | Origem e preservação do EBOOT |
| `analysis/base-1.00-isolated/EBOOT.analysis.elf` | Derivado somente para análise |
| `analysis/base-1.00-isolated/functions.tsv` | Funções reconhecidas pelo Ghidra |
| `analysis/base-1.00-isolated/sample-pseudocode.c` | Três amostras, não compiláveis como port |
| `analysis/allstars-ppu-100.gpr` | Projeto Ghidra persistido |

## Histórico da primeira importação no Ghidra

A saída ELF do RPCS3 contém tabela de nomes de seções zerada. A primeira importação genérica ficou na criação de segmentos e foi interrompida. Para a análise válida, foi criada uma cópia com somente os campos de seção do cabeçalho ELF zerados, preservando os segmentos. A transformação e os hashes estão em `EBOOT.analysis.provenance.json`. A cópia serve para análise, não para execução.

Naquela importação o Ghidra foi configurado como `PowerPC:BE:64:default`; os resultados iniciais estão em `reports/ghidra-ppu-console.txt` e `ghidra-summary.txt`. As análises posteriores de OPD/TOC/imports e o projeto compartilhado `work/ghidra_proj` têm escopo maior; ver [jogo.md](jogo.md).

## Ferramentas reexecutáveis

Os scripts de inventário usam somente a biblioteca padrão. A prova nativa usa Unicorn 2.1.4, instalado no ambiente `.venv` do projeto, e MSVC já existente. Execute a partir da pasta do projeto:

```powershell
python tools/inventory.py '<pasta do jogo com PS3_GAME>' reports/inventory.json
python tools/psarc_index.py '<pasta USRDIR>' reports/psarc-legacy-index.json
python tools/prepare_elf.py '<EBOOT.BIN>' 'tools/rpcs3-analysis/rpcs3.exe' 'analysis/nova-versao'
python tools/elf_report.py 'analysis/nova-versao/EBOOT.elf' reports/nova-versao.json
python tools/normalize_elf.py 'analysis/nova-versao/EBOOT.elf' 'analysis/nova-versao/EBOOT.analysis.elf'
python tools/audit_ps3.py reports/elf-base-1.00.json analysis/audit-1.00
python tools/stage2_report.py
python -m unittest discover -s tools -p 'test_*.py'
```

`prepare_elf.py` exige diretório novo e só executa o comando de descriptografia. O RPCS3 utilizado é uma cópia local isolada de exe/DLLs, sem seus saves ou contas. A primeira tentativa na instalação em uso expirou após 90 segundos; a cópia isolada resolveu. `analysis/base-1.00` conserva apenas essa tentativa inicial.

O registro do REA fica em `%USERPROFILE%\.codex\config.toml`, com backup em `%USERPROFILE%\.codex\config.toml.rea.backup`. Reiniciar ou reconectar o Codex podia ser necessário para que os novos tools MCP aparecessem; eles ficaram disponíveis na continuação daquela sessão. A limitação PowerPC continuará exigindo o caminho direto do Ghidra até haver suporte no REA.

## Próximo marco (registro de 14/10)

Concluir a integração dos avanços do tutorial, estabilizar o áudio e fazer o passe principal da cena 3D aparecer. Confirmar combate, controles e som antes de retomar o online. Referências externas no ROADMAP são consultas históricas, não comprovação do estado atual de serviços comunitários.
