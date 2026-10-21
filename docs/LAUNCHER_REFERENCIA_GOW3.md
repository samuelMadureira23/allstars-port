# Referência para o nosso launcher: o port de PC do God of War III Remastered (gow3_pc)

O Samuel tem na área de trabalho (`C:\Users\samue\Desktop\gow3-windows`) o port comunitário do GoW III Remastered (PS4→PC), cujo
launcher ele acha muito bom. Li só o README-Windows.txt, a config (gow3.ini) e a lista de arquivos — nada de código nem de dados
do jogo. Abaixo, o que vale copiar como IDEIA (não código) para o nosso (T-257, claude-ciclo).

## Como ele funciona (pelo README dele)
- **Sem arquivos do jogo**: o usuário aponta a própria pasta (eboot.bin etc.); lista as versões testadas (title ID + versão).
- **Dois executáveis**: `God of War III.exe` = launcher; `Play God of War III.exe` = abre o jogo direto com as configurações salvas
  (para atalho na área de trabalho / "Adicionar jogo não-Steam").
- **1ª vez**: "Choose the game folder" → Browse → volta ao Home → PLAY; "a 1ª abertura demora enquanto a imagem do jogo é preparada".
- **Páginas**: Home (ajustes rápidos + PLAY), Graphics, Performance, Game (controles, ícones de botões), Advanced (atalho na área de
  trabalho, log, verificar atualizações). Botão **Save** para guardar as mudanças pendentes.
- **Patches/correções automáticos**, com os padrões ligados (ex.: pular vídeos, fps alto), cada um só aplica onde a assinatura bate.
- **Menu dentro do jogo**: tecla **Insert** (ou R3+L2 no controle) → trapaças, imagem, desempenho e o overlay de desempenho.
- **Config em ini** ao lado do exe (display_mode=borderless, fps_limit, render_resolution, vsync, anisotropy, show_fps,
  frames_queued, async_shaders, vibration…); opções do launcher em %APPDATA%.
- **Pastas**: `user\` (saves, cache de shader, log — manter ao atualizar), `out\` (arquivos gerados).
- **README forte de problemas**: requisitos de CPU/GPU, "Windows protegeu seu PC → Mais informações → Executar assim mesmo" (não
  assinado), tela preta, texturas erradas, memória/arquivo de paginação, e "mande o user\last_run.log".
- **Mapa de teclado** padrão escrito no README; troca em Game → Controls.

## O que adotar no nosso
1. Dois atalhos: `All-Stars Launcher` (configurar/preparar) e `Jogar All-Stars` (direto, com as configurações salvas).
2. Páginas: **Início** (pasta do jogo, status "pronto/precisa preparar", ajustes rápidos, JOGAR e JOGAR LAN), **Gráficos**
   (janela/sem borda/tela cheia, escala interna, VSync, limite de fps, mostrar fps), **Controles** (teclado/controle, ícones),
   **LAN** (IP de cada um, quem cria), **Avançado** (log, abrir pastas, atalho na área de trabalho, limpar cache de shader).
3. Botão Salvar + `port_settings.ini` ao lado do exe; pasta `user\` para saves, cache de shader e logs; `out\` para o gerado.
4. Menu dentro do jogo numa tecla fácil (o Samuel sugeriu F2; o GoW usa Insert) — T-256.
5. README/guia com: versões testadas (BCUS98472 1.00), requisitos, "Windows protegeu seu PC", problemas comuns e "mande o log".

## Diferença importante (pergunta em aberto)
O GoW traz o Python dentro da pasta e "prepara a imagem do jogo" na 1ª abertura **sem o usuário instalar compilador**. O nosso kit,
hoje, precisa compilar o código gerado na máquina do amigo (VS Build Tools + LLVM, ~10 GB). Vale estudar (claude-int): dá para
levar um compilador portátil redistribuível (ex.: clang/lld, licença Apache) e evitar o VS? O SDK do Windows não é redistribuível.
Se não der, o launcher guia a instalação passo a passo (como hoje).
