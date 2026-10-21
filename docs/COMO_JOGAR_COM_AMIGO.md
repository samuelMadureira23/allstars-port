# Como jogar com um amigo pela internet (Radmin VPN)

**English:** [How to play with a friend](HOW_TO_PLAY_WITH_A_FRIEND.md)

Guia para quem não é técnico. Vocês dois jogam o **port para PC** de PlayStation All-Stars Battle Royale, cada um no seu
computador, ligados por uma **rede virtual** (Radmin VPN). O jogo acha que vocês estão na mesma casa (LAN).

> **Importante:** este pacote NÃO traz o jogo. Cada um precisa da **sua própria cópia do disco** (BCUS98472, versão 1.00).
> O update 1.12 e as DLC são opcionais: veja o passo 7/8 abaixo. Para jogar juntos, os dois precisam da MESMA versão. O port é montado no seu PC a partir do seu jogo, pelo **Launcher**.

---

## Parte 1 — Montar o port no seu PC (só na 1ª vez)

1. Dê dois cliques em **`Open Launcher.exe`** (na pasta do port).
   - Se aparecer "Não achei um Python 3 com tkinter": instale o **Python 3** do site python.org. Na instalação, marque
     **"Add python.exe to PATH"** e deixe marcada a opção **"tcl/tk and IDLE"**. Depois abra o Launcher de novo.
2. Página **"Início"**: **Escolher...** a pasta do seu jogo (a que tem a pasta `PS3_GAME` dentro).
3. Página **"Preparar"**, siga os botões em ordem:
   1. **1) Conferir o jogo**.
      Tem que aparecer "OK: EBOOT.BIN igual ao do disco 1.00". Se disser que é diferente, escolha a pasta do DISCO
      (o update entra separado, nos botões 7 e 8).
   2. **2) Como decriptar**: mostra como usar o **seu RPCS3** (o emulador) para gerar o arquivo `EBOOT.elf`.
      Resumo: no RPCS3, menu *Utilities → Decrypt PS3 Binaries*, escolha o `PS3_GAME\USRDIR\EBOOT.BIN` do seu jogo.
   3. **3) Conferir ELF**: confere o arquivo gerado e o coloca no lugar certo.
   4. **4) Ferramentas**: diz o que falta instalar para compilar (Visual Studio Build Tools com C++, LLVM, CMake,
      Ninja). O Launcher **não instala nada sozinho**: ele só mostra o nome; instale e clique de novo.
   5. **5) Gerar e compilar**: gera o código a partir do seu jogo e compila. Demora (dezenas de minutos).
   6. **6) Conferir o exe**: confere o programa gerado.
   7. **Opcional — 7) Update 1.12 + DLC** e **8) Conferir ELF 1.12**, ANTES do passo 5: escolha a pasta do update no seu
      RPCS3 (`dev_hdd0\game\BCUS98472`) e decripte o `USRDIR\EBOOT.BIN` dessa pasta no RPCS3 como no passo 2. Com isso o
      passo 5 gera também o 1.12 (textos em português, lutadores e fases de DLC) e o jogo abre no 1.12.

Na 1ª vez que jogar, o jogo compila os efeitos enquanto você joga: a 1ª partida pode ter umas travadinhas. A tela **Preparando os shaders** compila os shaders antes da partida, o que reduz as travadas; ainda pode haver alguma travada curta na primeira luta de cada fase.

## Parte 2 — Opções (opcional)

Páginas **"Gráficos"** e **"Controles"**: resolução interna (1440p ou 4K deixam a imagem mais nítida), VSync, som, arquivo de teclas do teclado.
As marcadas **"em breve"** são guardadas, mas o jogo ainda não as usa. Clique em **Salvar**.

## Parte 3 — Entrar na mesma rede (Radmin VPN), os dois

1. Cada um instala o **Radmin VPN** (gratuito, site oficial radmin-vpn.com) e abre.
2. **Um** de vocês cria a rede: *Rede → Criar rede*, escolhe um nome e uma senha, e passa os dois ao amigo.
3. O **outro** entra: *Rede → Entrar em uma rede existente*, com o mesmo nome e senha.
4. No topo da janela do Radmin aparece o **seu IP**, do tipo **26.x.x.x**. Cada um anota o SEU e manda o seu ao amigo.
   Quando os dois estão na mesma rede, o nome do amigo aparece na lista com uma bolinha verde.

## Parte 4 — Liberar o firewall do Windows (os dois, 1ª vez)

Na primeira partida, o Windows pergunta se o **PlayStation All-Stars Battle Royale** (PSASBR.exe) pode usar a rede: marque **"Redes privadas"** e
clique em **Permitir**. O jogo usa só as portas **UDP 4658, 4659 e 4660** (nada TCP).
Se você clicou em "Cancelar" sem querer: *Painel de Controle → Firewall do Windows → Permitir um aplicativo* e marque o
PlayStation All-Stars Battle Royale (PSASBR.exe) em "Privada".

## Parte 5 — Jogar juntos

Abra o jogo normalmente (Launcher → **JOGAR**, ou o `Play All-Stars.exe`). A partida online é configurada **dentro do
jogo**: aperte **F3** para abrir o menu de online, onde cada um põe o **seu IP do Radmin** (26.x.x.x) e o **do amigo**, e
escolhe quem cria a sala.


## Se der errado

| Problema | O que fazer |
|---|---|
| Não acha a sala / fica esperando o amigo | Confiram: os dois na **mesma rede** do Radmin (bolinha verde) e os IPs digitados **trocados certo** no menu F3 (o seu no "meu", o dele no "amigo"). |
| O Windows não perguntou do firewall e nada conecta | Libere o PSASBR em "Redes privadas" (Parte 4). |
| Funciona com um amigo e não com outro | O port só conversa com os 2 IPs digitados: confira o IP do amigo novo. |
| Testar sozinho com 2 janelas no mesmo PC | **Não dá** com o IP do Radmin (o Windows não deixa). Precisa de 2 PCs. |
| O jogo fica na tela preta no começo | Feche e abra de novo pelo Launcher (ele limpa o cache do jogo a cada partida). |
| Qualquer outro erro | Abra uma *issue* na página do projeto no GitHub e anexe o arquivo `user\logs\last_run.log` da pasta do port (Launcher → Avançado → Ver o último log). |

## Próximas vezes

- **`Play All-Stars.exe`** abre o jogo direto, com a pasta e as opções salvas (sem passar pelo Launcher).
- Launcher → **Avançado → Criar atalho** põe o atalho **Play All-Stars** na área de trabalho.
- Saves, cache e logs ficam na pasta **`user\`** do port: guarde essa pasta se for atualizar o port.
