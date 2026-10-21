# PlayStation All-Stars Battle Royale: port nativo para PC (Windows)

**English:** [README in English](docs/README_GITHUB_EN.md)

Port nativo para Windows x64 de PlayStation All-Stars Battle Royale (BCUS98472), feito por recompilação estática a partir do fork do [ps3recomp](https://github.com/sp00nznet/ps3recomp). Usa Direct3D 12 e não depende de emulador para executar.

**Comunidade:** Discord do ps3recomp, servidor sp00nznet recomp (https://discord.gg/CRpzGWZFcu), usuário `@samukambr`.

## Sobre o projeto

O jogo original foi compilado para o processador Cell do PlayStation 3. Este projeto traduz o código do processador principal (PPU) e das unidades sinérgicas (SPU) para C, compila esse código junto com uma camada que substitui as bibliotecas do console e encaminha os comandos gráficos para o Direct3D 12. O resultado é um executável nativo, sem emulação de instruções em tempo de execução.

O port é gerado no computador do usuário a partir da cópia dele do jogo. Este repositório não contém EBOOT, código gerado, executável do port, arquivos .psarc, texturas, áudio, vídeo, firmware ou saves. É necessário ter a própria cópia do disco BCUS98472, versão 1.00.

## O que funciona

- Menus, seleção de personagens, lutas com até quatro lutadores, cenários e efeitos.
- No computador de testes (Ryzen 7 7700 e RTX 5070), as lutas de dois jogadores mantêm 60 fps com resolução interna de até 3x, FXAA e filtro anisotrópico. As lutas de quatro jogadores ficam próximas de 50 fps. O desempenho em computadores mais modestos ainda está em medição.
- DualShock 4, DualSense, controles Xbox e genéricos, inclusive vários conectados ao mesmo tempo, além de teclado.
- Pré-compilação de shaders antes da partida, que reduz as travadas iniciais.
- Partidas em rede local, usando o netcode do próprio jogo.

## Requisitos

- Windows 10 ou 11, 64 bits, com placa de vídeo compatível com Direct3D 12.
- Cópia própria de PlayStation All-Stars Battle Royale em disco, BCUS98472, versão 1.00. O EBOOT.BIN é conferido por SHA-256.
- RPCS3 apenas para decriptar o EBOOT.BIN, pela opção Utilities, Decrypt PS3 Binaries.
- Para compilar o port: Python 3 com Tcl/Tk, Visual Studio Build Tools com suporte a C++, LLVM com clang-cl, CMake e Ninja. O Launcher informa o que estiver faltando e não baixa nem instala nada.

## Como jogar

1. Abra **Open Launcher.exe**.
2. Na aba Início, selecione a pasta do jogo, aquela que contém PS3_GAME.
3. Na aba Preparar, siga os passos na ordem: conferir o jogo, decriptar com o RPCS3, conferir o ELF, verificar as ferramentas, gerar e compilar o port e conferir o executável. A geração e a compilação levam dezenas de minutos.
4. Opcional: para usar o update 1.12 e os conteúdos adicionais, antes de gerar e compilar, use os botões 7 e 8 da aba Preparar. O botão 7 pede a pasta do update, por exemplo dev_hdd0/game/BCUS98472 do RPCS3. O botão 8 confere o EBOOT.BIN decriptado do update. O passo de geração passa a produzir as versões 1.00 e 1.12, e o jogo abre na 1.12. O update e os conteúdos adicionais são os do usuário, instalados no RPCS3 dele.
5. Clique em Jogar. Na primeira partida, o Launcher compila os shaders do jogo e mostra o progresso.

O guia detalhado, para quem não é técnico, está em [docs/COMO_JOGAR_COM_AMIGO.md](docs/COMO_JOGAR_COM_AMIGO.md).

## Estado

Projeto em andamento. A versão 1.00 do disco é a base; o update 1.12, com os conteúdos adicionais, é suportado por cima dela. A versão apenas digital, sem o disco, ainda não é suportada.

O alvo mínimo de computador está definido: processador Xeon E5-2680 v4 e placa AMD RX 580 de 8 GB ou NVIDIA GTX 1660 de 6 GB, com 60 fps em 1080p e resolução interna de 1x a 1,5x. Esse alvo ainda está em medição.

## Problemas conhecidos

- Travadas curtas na primeira vez que um efeito ou cenário aparece, enquanto os shaders correspondentes são compilados. A pré-compilação reduz esse efeito, mas ainda restam algumas ocorrências na primeira luta de cada fase.
- Falhas visuais pontuais em casos específicos, como alguns efeitos de partículas e a intro de determinados cenários.
- O modo online fora da rede local ainda não está disponível.

## Guias

- [Como jogar com um amigo](docs/COMO_JOGAR_COM_AMIGO.md)
- [Problemas comuns](docs/PROBLEMAS_COMUNS.md)
- [Como jogar online pela rede local](docs/COMO_JOGAR_ONLINE_F3.md)

## Feedback

A comunidade do ps3recomp fica no Discord deles (servidor sp00nznet recomp), onde o desenvolvimento do runtime acontece: https://discord.gg/CRpzGWZFcu. Lá, procure por `@samukambr`. Para relatos que devam ficar registrados, use as Discussions ou as Issues do repositório. Não envie EBOOT, .psarc, chaves, firmware ou qualquer arquivo do jogo; descreva o problema e anexe apenas o log `user\logs\last_run.log`, revisado antes.

## Créditos e licença

- Base: [ps3recomp](https://github.com/sp00nznet/ps3recomp), licença MIT, de Ned Heller (sp00nznet) e colaboradores. A licença original está em src/ps3recomp/LICENSE.
- O [RPCS3](https://rpcs3.net) foi usado como referência de comportamento.
- PlayStation All-Stars Battle Royale é marca e propriedade da Sony Interactive Entertainment. Este projeto não é afiliado à Sony e não distribui conteúdo do jogo.

## Aviso legal

Este repositório não distribui o jogo nem qualquer arquivo extraído dele. Para usar o port, é necessário possuir uma cópia legítima do disco e obter o EBOOT.BIN a partir dela. O projeto não é afiliado à Sony Interactive Entertainment e não tem como objetivo permitir o uso do jogo por quem não o possui.

## Desenvolvimento

A documentação de engenharia, o diário de coordenação e as regras de contribuição ficam em [docs/ENGINEERING.md](docs/ENGINEERING.md), [AGENTS.md](AGENTS.md), [coord/TASKS.md](coord/TASKS.md) e [PLANO.md](PLANO.md).
