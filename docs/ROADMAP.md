# All star port — investigação e marcos

Objetivo: executar PlayStation All-Stars Battle Royale nativamente no PC e,
posteriormente, implementar partidas online. O projeto está em investigação;
não há port jogável nem código-fonte original recuperado.

## Critérios de avanço

1. Identidade e ambiente: registrar hashes, versões e ferramentas. Concluído para
   o disco BCUS98472 1.00; executável da atualização local 1.12 também preservado.
2. Análise PPU: importar ELF, validar ABI PS3, entrypoint/OPD/TOC e dependências.
   Parcial: ELF obtido, OPD/TOC/imports mapeados nas duas versões e conferidos;
   REA instalado rejeita PowerPC; Ghidra direto disponível. Faltam análise de
   chamadas, semântica e limites exatos das funções.
3. Recursos e SPU: mapear formatos, compactação e transformações dos PSARC;
   identificar programas SPU e tarefas DMA. Parcial: tabelas PSARC lidas, nomes
   não decodificados pelo perfil zlib comum; três imagens SPU por versão extraídas
   com validação estrutural de segmentos e limites de local store.
4. Prova nativa: selecionar uma função pura, recuperar comportamento e comparar
   resultados com referência para vários casos. Primeiro experimento concluído:
   VA 0x004A70D4 da versão 1.00 traduzida manualmente para DLL x64, 10.015 casos
   passaram contra Unicorn PPC64 para r3/r5/flags selecionadas. Ver NATIVE_PROOF.md.
   Ainda falta validar funções com memória e geração automática.
5. Runtime: memória/endian, threads, arquivos, entrada, áudio, LV2/PRX, RSX e SPU.
   Primeiro marco visível: primeiro frame correto, depois menu e combate local.
6. Equivalência local: conferir física, timing, animação, dano, áudio e controles
   contra execução de referência. Ainda não iniciada.
7. Online: investigar LAN/protocolos existentes, sincronização de simulação,
   matchmaking e transporte. Escolher rollback ou outra estratégia somente após
   medir determinismo e estado serializável. Ainda não iniciada.

## Fontes técnicas e limites (consultadas em 14/10/2026)

- [ps3recomp](https://github.com/sp00nznet/ps3recomp): candidato para recompilação
  estática, sem validação local para este jogo. A documentação possui afirmações
  divergentes sobre maturidade; fixar commit e testar antes de adotar.
- [Arquitetura](https://github.com/sp00nznet/ps3recomp/blob/master/docs/ARCHITECTURE.md)
  e [início](https://github.com/sp00nznet/ps3recomp/blob/master/docs/GETTING_STARTED.md).
- [RPCS3 CLI](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/rpcs3.cpp): comando
  de descriptografia usado numa cópia isolada da instalação local. Não houve boot.
- [PsasPs3Hooks](https://github.com/pschap/PsasPs3Hooks): investigação pública
  específica de hooks e dump de recursos. Endereços precisam corresponder à versão;
  não aplicados aqui. O build documentado depende de SDK Sony, portanto não foi
  adotado como dependência desta base.
- [All-Stars Matchmaker](https://www.playallstars.org/): site anuncia mod LAN e
  matchmaking com suporte RPCS3, mas ainda exibe Coming Soon. Não testado aqui.
  Não confundir isso com restauração de Ranked/Quick Match originais.
- [RPCN](https://github.com/RipleyTom/rpcn): projeto de serviços online do RPCS3;
  existência do projeto não prova suporte atual a BCUS98472.

## Regras de evidência

Separar 1.00 e 1.12; nunca transferir endereços entre versões sem validar bytes.
Pseudocódigo Ghidra é inferência de análise estática, não código original nem
equivalência funcional provada. Os relatórios Python/Ghidra não são REA Evidence.
Guardar cópias derivadas em analysis, com hash e transformação documentados.
Não versionar ou publicar binários e recursos do jogo junto das ferramentas.
