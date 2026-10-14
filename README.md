# All star port

> **Agentes de IA: comecem por [AGENTS.md](AGENTS.md)** (regras, áreas e coordenação),
> depois `coord/TASKS.md`, `coord/LOG.md` e `PLANO.md`. O texto abaixo descreve a etapa
> inicial (manhã de 14/10/2026); desde então o port recompilado já compila e o boot chega ao
> loop principal do jogo — estado atual em `PLANO.md`.

Projeto iniciado em 14/10/2026 para investigar um port nativo de PlayStation
All-Stars Battle Royale para PC, seguido de modo online.

**Estado: engenharia reversa inicial. Não existe port jogável nesta pasta.**

## Avanço da segunda etapa

Foi executada uma primeira função traduzida manualmente em uma DLL nativa x64.
Os 10.015 casos comparados com o oráculo PPC64 passaram para r3, r5 e os campos
selecionados de XER. Escopo e reprodução em [docs/NATIVE_PROOF.md](docs/NATIVE_PROOF.md).

| Observação estática | Versão 1.00 | Versão 1.12 |
| --- | ---: | ---: |
| Descritores OPD | 16.989 | 17.176 |
| Entradas de código distintas na OPD | 12.775 | 12.924 |
| Imports de firmware | 376 | 378 |
| Bibliotecas importadas | 25 | 26 |
| Imports nomeados por banco NID | 345 | 350 |
| Imagens SPU extraídas e estruturalmente validadas | 3 | 3 |

As duas versões têm dois contextos TOC. As entradas OPD foram conferidas contra
bytes, alinhamento, seções executáveis e memória carregada. Não são uma contagem
exaustiva de funções. Os endereços finais estimados pelo loader não são limites
de função comprovados. Resultados em `reports/stage2.json` e `analysis/audit-*`.

Ferramenta de leitura: ps3recomp, commit
`a2c20108af45174dbb7d3e2f87f6acaaef09c6b4`, preservado em `tools/ps3recomp`.
As análises PPU ficam em `analysis/ppu-1.00` e `analysis/ppu-1.12`.
O runtime completo dessa ferramenta ainda não foi compilado ou validado.

## Resultados verificados

- Inventário do disco BCUS98472 1.00: 23.933 arquivos, 6.308.711.424 bytes.
- 48 PSARC, com 33.552 entradas de recursos nas tabelas. Os manifests não foram
  decodificados pelo perfil zlib comum; nomes e conteúdos permanecem desconhecidos.
- Encontrada atualização BCUS98472 1.12 na instalação local do RPCS3.
- ELF das duas versões obtido usando RPCS3 isolado, sem executar o jogo.
  Hash dos EBOOT originais conferido antes/depois: arquivos preservados.
- REA registrado no Codex; `rea doctor --client codex --json` retornou healthy=true.
  Ghidra 12.1.4 e JDK 21 já estavam instalados e foram reutilizados.
- O REA instalado rejeitou SELF e depois ELF PowerPC. Isso é uma limitação do
  caminho de importação do REA, não evidência de que Ghidra não suporte PowerPC.
- Ghidra direto reconheceu 1.233 funções na cópia de análise 1.00 e exportou três
  amostras de pseudocódigo. Não é cobertura completa nem código pronto para compilar.
- Detectadas três imagens ELF32 big-endian, machine=23 (SPU), embutidas em cada
  ELF. Segmentos, limites de arquivo e local store foram validados; execução e
  cobertura completa de tarefas SPU ainda não verificadas.

## Arquivos principais

| Caminho relativo | Conteúdo |
| --- | --- |
| `docs/ROADMAP.md` | Critérios de avanço, fontes e limites |
| `reports/inventory.json` | Inventário e PARAM.SFO do disco |
| `reports/psarc-index.json` | Tabelas de recursos e falhas de leitura do manifest |
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

## Importação no Ghidra

A saída ELF do RPCS3 contém tabela de nomes de seções zerada. A primeira importação
genérica ficou na criação de segmentos e foi interrompida. Para a análise válida,
foi criada uma cópia com somente os campos de seção do cabeçalho ELF zerados,
preservando os segmentos. A transformação e os hashes estão em
`EBOOT.analysis.provenance.json`. A cópia serve para análise, não para execução.

O Ghidra foi explicitamente configurado como `PowerPC:BE:64:default`; ABI, TOC,
descritores de função e imports do PS3 ainda precisam de validação. Os resultados
estão em `reports/ghidra-ppu-console.txt` e `ghidra-summary.txt`.

## Ferramentas reexecutáveis

Os scripts de inventário usam somente a biblioteca padrão. A prova nativa usa
Unicorn 2.1.4, instalado no ambiente `.venv` do projeto, e MSVC já existente.
Execute a partir desta pasta:

```powershell
python tools/inventory.py '<pasta do jogo com PS3_GAME>' reports/inventory.json
python tools/psarc_index.py '<pasta USRDIR>' reports/psarc-index.json
python tools/prepare_elf.py '<EBOOT.BIN>' 'tools/rpcs3-analysis/rpcs3.exe' 'analysis/nova-versao'
python tools/elf_report.py 'analysis/nova-versao/EBOOT.elf' reports/nova-versao.json
python tools/normalize_elf.py 'analysis/nova-versao/EBOOT.elf' 'analysis/nova-versao/EBOOT.analysis.elf'
python tools/audit_ps3.py reports/elf-base-1.00.json analysis/audit-1.00
python tools/stage2_report.py
python -m unittest discover -s tools -p 'test_*.py'
```

`prepare_elf.py` exige diretório novo e só executa o comando de descriptografia.
O RPCS3 utilizado é uma cópia local isolada de exe/DLLs, sem seus saves ou contas.
A primeira tentativa na instalação em uso expirou após 90 segundos; a cópia
isolada resolveu. `analysis/base-1.00` conserva apenas essa tentativa inicial.

O registro do REA está em `C:\Users\samue\.codex\config.toml`, com backup
`C:\Users\samue\.codex\config.toml.rea.backup`. Reiniciar/reconectar o Codex
podia ser necessário para que os novos tools MCP aparecessem; eles ficaram
disponíveis na continuação desta sessão. A limitação PowerPC
continuará exigindo o caminho direto do Ghidra até haver suporte no REA.

## Próximo marco

Enriquecer o Ghidra com OPD/imports e testar uma função com memória e TOC,
seguida da geração automática de código. Depois avaliar runtime PPU/SPU, RSX,
áudio e entrada antes de perseguir menu e combate local. Online é uma etapa
posterior; há também o projeto comunitário All-Stars Matchmaker, ainda anunciado
como Coming Soon na consulta realizada. Fontes no ROADMAP.
