# Primeira prova de execução nativa — 14/10/2026

Resultado: **10.015 casos passaram** para uma tradução manual de uma função do
executável BCUS98472 1.00, compilada como DLL Windows x64 com MSVC 14.51.

## Escopo exato

- ELF: `analysis/base-1.00-isolated/EBOOT.elf`.
- SHA-256: `a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5`.
- Entrada de código: `0x004A70D4`, offset no arquivo `0x004970D4`.
- OPD `0x00C68290` aponta para esse código com TOC `0x00C84768`.
- Nove instruções, 36 bytes; sem memória, chamadas externas ou uso do TOC.
- O significado da função dentro do jogo ainda não foi identificado.
- Comparados r3, r5 e os campos SO/OV/CA/byte-count de XER (máscara `0xe000007f`).
- 15 casos de borda e 10.000 entradas pseudoaleatórias de 64 bits, semente 98472.

O código nativo é tradução manual instrução a instrução. A referência executa os
bytes originais em Unicorn 2.1.4, PPC64 big-endian, com MSR.SF=1 e TLB virtual.
O teste não utiliza RPCS3 para executar essa função nem valida em hardware PS3.

## Detalhe necessário do oráculo

A API XER do Unicorn 2.1.4 lê/escreve `env->xer`, enquanto o motor mantém flags
aritméticas separadas. A primeira tentativa detectou divergências de observação.
O teste final usa instruções `mtxer`/`mfxer` antes/depois do trecho para inicializar
e observar as flags arquiteturais. Essas duas instruções pertencem ao teste,
não ao jogo. O modelo padrão também expõe flags de ISA posterior, excluídas
explicitamente da comparação. Isso não é comparação de todo o estado da CPU.

Fonte: [implementação de registradores do Unicorn 2.1.4](https://github.com/unicorn-engine/unicorn/blob/2.1.4/qemu/target/ppc/unicorn.c).

## Reexecutar

Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe tools/prove_native.py --compiler 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe'
```

Saídas: `reports/native-proof.json`, `analysis/native-proof/translated_leaf.c`,
`translated_leaf.dll` e `build.log`. O script confere hash do ELF, bytes e OPD
antes de compilar. Relatório inclui hashes da fonte, DLL e digest dos casos.

## O que permanece aberto

Esta prova cobre apenas uma função isolada e um conjunto finito de entradas.
Não prova recompilação automática, cobertura de toda a ISA, fidelidade em hardware,
inicialização do jogo, runtime, gráficos, áudio, tarefas SPU ou rede.
Próximo passo: enriquecer o Ghidra com OPD/imports e comparar uma função que usa
memória e TOC; depois testar geração automática de código e dependências do runtime.
