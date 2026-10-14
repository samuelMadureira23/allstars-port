# Teste diferencial PPU — EBOOT 1.00 (T-007)

Execução de 14/10/2026, agente astra. Foram comparadas **18 funções do C gerado**
com suas instruções PowerPC originais executadas pelo Unicorn 2.1.4.

**Resultado observado:** 18.432 casos, 17.924 equivalentes e 508 divergentes.
As divergências estão todas em `func_0047E550`, no bit SO de CR7. As outras
17 funções passaram nos 1.024 casos de cada uma. Isso mede esta amostra;
não mede progresso do port nem comprova gameplay, SPU, gráficos ou online.

## Reprodução

Na raiz `C:\Users\samue\Documents\All star port`:

```powershell
.\.venv\Scripts\python.exe tools\difftest\run.py --cases 1024
.\.venv\Scripts\python.exe -m unittest discover -s tools\difftest -p 'test_*.py' -v
```

O primeiro comando retorna **1 enquanto houver divergências**; isso é esperado
no estado atual. O segundo passou nos quatro testes. Não instala dependências.
Usa clang-cl 23.1.3 e o VS Build Tools já instalados, com `/O2 /EHsc /std:c++17`.

Saídas locais:

- `reports/difftest-1.00.json`: identidade das entradas, hashes do código/headers/
  helpers/DLL, compilador, contagens, índices dos casos divergentes e quatro
  exemplos completos de registradores por função divergente.
- `reports/difftest-tests.txt`: saída da bateria e dos quatro testes do oráculo.
- `analysis/difftest-astra/`: fontes extraídas, DLL e `build.log`. Esses arquivos
  são ignorados pelo Git; contêm material derivado do jogo e ficam nesta máquina.

Cada entrada é reproduzível pelo trio endereço, índice do caso e seed (98472).
`inputs(address, index, seed)` gera os registradores e a memória correspondentes.
Os primeiros 21 casos incluem zero, limites de sinal/largura e valores pequenos;
os demais usam um gerador determinístico com operandos independentes. Ponteiros
são ajustados para objetos válidos nas funções que acessam memória.

## Método e verificações do próprio teste

- ELF permitido: `work/eboot/EBOOT_1.00_disc.elf`, SHA-256
  `a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5`.
  Outra identidade é rejeitada antes de usar os endereços. Nenhum endereço 1.12.
- `run.py` extrai os corpos completos e os helpers originais dos arquivos
  `work/recompiled_1.00/ppu_recomp_*.cpp`; não retraduz nem corrige esses corpos.
  O header original também é copiado. Todos os snapshots conferiam com os
  arquivos de origem ao fim da execução.
- O adaptador C++ fornece memória big-endian limitada a duas páginas de 4 KiB.
  Acesso fora dessas regiões falha explicitamente. Não usa o runtime do port.
- Comparação: todos os 32 GPRs, CR, LR, CTR, XER com máscara `0xe000007f` e
  todos os 8.192 bytes das duas regiões, incluindo áreas que deveriam ficar intactas.
- Unicorn: PPC64 big-endian, CPU padrão, TLB virtual, MSR.SF=1. Máximo de
  128 instruções por chamada e verificação de retorno ao endereço sentinela.
- XER é inicializado/lido por `mtxer`/`mfxer` em um trampoline separado. O acesso
  direto pela API do Unicorn não inclui corretamente os flags separados internamente
  pelo QEMU. Os registradores usados pelo trampoline são restaurados ou capturados
  antes da instrumentação. CA32, que não é parte do escopo PS3 aqui, fica excluído.
- Quatro testes independentes validam preservação de registradores e oito combinações
  de SO/OV/CA, comparação unsigned/copiar SO/preservar outros campos CR, store
  big-endian sem alterar vizinhos e sensibilidade do comparador a registradores/memória.
- Controles negativos passaram: alterar deliberadamente um bit de r3 após a função
  é detectado; um store em endereço não mapeado é rejeitado pelo adaptador.
- Há avisos do compilador nos helpers originais `_mul128`/`_umul128` não usados
  por esta seleção; não impediram o build e não foram alterados.

## Cobertura observada

| Endereço | Operações cobertas | Casos equivalentes / total |
|---|---|---|
| `0x00011B84` | store32 | 1024 / 1024 |
| `0x0004AE70` | leitura TOC, ponteiro, store | 1024 / 1024 |
| `0x0004D338` | load/store64, store8/32 | 1024 / 1024 |
| `0x00133B74` | oris | 1024 / 1024 |
| `0x002A3524` | store com atualização do endereço | 1024 / 1024 |
| `0x002D4970` | subtração, extensão de sinal, memória | 1024 / 1024 |
| `0x002FB804` | soma, truncamento para 32 bits | 1024 / 1024 |
| `0x003027C8` | shift aritmético, carry, sinal | 1024 / 1024 |
| `0x00364EAC` | rotação/máscara de 64 bits | 1024 / 1024 |
| `0x0047E550` | comparação unsigned e desvio | **516 / 1024** |
| `0x004A70D4` | negação, shift/carry, rotações | 1024 / 1024 |
| `0x004D7784` | addic, store | 1024 / 1024 |
| `0x004E32F8` | cópia de 8/16/32 bits | 1024 / 1024 |
| `0x005DF650` | OR e memória64 | 1024 / 1024 |
| `0x005F3B00` | AND, shift/carry, sinal | 1024 / 1024 |
| `0x00A08C08` | extensão de sinal de 16 bits | 1024 / 1024 |
| `0x00AA34B8` | addic, cntlzw (inclui zero) | 1024 / 1024 |
| `0x00AA3BB4` | addc, addic, truncamento | 1024 / 1024 |

## Divergência reproduzida — T-015

**Observado:** `cmplwi cr7,r4,2` em `0x0047E550` copia XER.SO para o bit SO
de CR7 no oráculo. O C gerado escreve somente LT/GT/EQ e zera SO.

- XER.SO=0: 516 casos passaram; nenhum falhou.
- XER.SO=1: 508 casos falharam; todos diferem somente em `CR xor 0x1`.
- Primeiro exemplo: seed 98472, índice 1. CR PowerPC `0xfd61bc15`,
  CR nativo `0xfd61bc14`; XER de entrada `0xa000005e`.
- Retorno r3, demais registradores e memória equivalentes nesses 508 casos.
- Fonte gerada: `work/recompiled_1.00/ppu_recomp_002.cpp`, `func_0047E550`.
- Causa visível no gerador: `agents/astra/ps3recomp/tools/ppu_lifter.py`,
  bloco `cmplwi/cmpldi` (aproximadamente linhas 1320–1333), monta `cr_val`
  sem incorporar `((ctx->xer >> 31) & 1)`.

**Inferido pela inspeção estática:** outros blocos de comparação inteira do
mesmo gerador têm a mesma omissão. Precisam de testes específicos antes de
declarar a abrangência confirmada. Correção deve preservar SO e testar os
campos CR0–CR7, tamanhos 32/64 e comparações signed/unsigned.

**Desconhecido:** se esse bit influencia algum caminho de gameplay ou o
bloqueio atual após o menu. Não houve correção/relift, alteração no runtime nem
teste de boot nesta tarefa. T-015 registra a correção separadamente, respeitando
as travas do Claude e a necessidade de LIFT/INTEGRATION.

## Limites

Oráculo de emulação não é hardware PS3. A amostra contém funções inteiras pequenas,
sem chamadas externas; usa memória sintética válida. Não cobre FPU, SIMD, SPU,
reservas atômicas, concorrência, exceções, HLE nem o backend gráfico. Equivalência
em entradas amostradas não prova equivalência para todas as entradas.
