# Problemas comuns — solução de problemas

Guia para quem recebeu o pacote do port e algo não funcionou. Está na ordem em que os problemas aparecem:
**abrir o Launcher → preparar (conferir o jogo, decriptar, ferramentas, compilar) → jogar → controle → antivírus**.

> **Antes de tudo:** este pacote **não traz o jogo**. Cada pessoa monta o port no próprio PC, a partir da **própria
> cópia do disco** (BCUS98472, versão 1.00), pelo Launcher. Se você ainda não passou pela página **Preparar**, comece
> pelo guia passo a passo `docs/COMO_JOGAR_COM_AMIGO.md` (escrito para quem não é técnico).

## 0. Onde ficam as coisas (guarde esta tabela)

Tudo o que o port gera fica dentro da pasta do port (a que tem `Abrir Launcher.bat`):

| Onde | O que é | Apague? |
|---|---|---|
| `user\logs\last_run.log` | o log **da última partida** (é ele que se manda quando algo dá errado) | pode apagar, mas mande antes |
| `user\logs\last_run.prev.log` | o log da partida **anterior** | pode apagar |
| `user\logs\shaders.log` | o log do preparo dos shaders | pode apagar |
| `user\saves\` | seus **saves** | **não** |
| `user\cache\` | cache do jogo, refeito a cada partida | sim, sem medo (Avançado → Limpar o cache) |
| `user\keymap.ini` | suas teclas do teclado | não |
| `port_settings.ini` | as opções salvas (as mesmas do menu F3 dentro do jogo) | não |
| `work\` e `build\` | o código gerado e o programa compilado do **seu** jogo | só se quiser recompilar do zero |

Ao atualizar o port, **substitua tudo menos a pasta `user\`**.

## 1. O Launcher não abre

| O que aparece | O que fazer |
|---|---|
| "Não achei um Python 3 com tkinter" | Instale o **Python 3** do site oficial **python.org**. Na instalação, marque **"Add python.exe to PATH"** e deixe marcada a opção **"tcl/tk and IDLE"**. Abra o `Abrir Launcher.bat` de novo. |
| O `Abrir Launcher.bat` pisca e fecha | Falta o Python 3 (instale como acima). Se você já tem um Python instalado, mas ele não traz o tkinter, instale o de **python.org** e marque, na instalação, a opção **"tcl/tk and IDLE"**. |
| O `Jogar All-Stars.bat` diz "Nao achei o Python 3" | O mesmo caso: o atalho direto também precisa do Python instalado. |

O Launcher **não baixa nem instala nada sozinho**: ele só mostra o nome do que falta.

## 2. A página "Preparar" diz que falta uma ferramenta (botão "4) Ferramentas")

O botão imprime uma lista e marca `FALTA` no que não achou. São estas cinco coisas, todas gratuitas:

| Nome no Launcher | O que é | De onde baixar (só do site oficial) |
|---|---|---|
| **Python 3** | a linguagem que roda o Launcher e as ferramentas | `python.org` |
| **Visual Studio Build Tools (C++ x64)** | o compilador da Microsoft | `visualstudio.microsoft.com` — baixe **"Build Tools for Visual Studio"** e marque o componente **"Desenvolvimento para desktop com C++"** (*Desktop development with C++*) |
| **LLVM (clang-cl)** | o compilador que a compilação usa de fato | `releases.llvm.org` — "LLVM for Windows" |
| **CMake** | organiza a compilação | `cmake.org` |
| **Ninja** | o programa que executa a compilação | `ninja-build.org` — no Windows também vem pelo `winget` |

Instale o que falta, feche e abra o Launcher, e clique em **4) Ferramentas** de novo.

### "Instalei, mas continua dizendo FALTA"

O Launcher procura cada ferramenta num lugar específico. Se você instalou em outro lugar (ou escolheu outro tipo de
instalação), ele não acha:

| Ferramenta | Onde o Launcher (e a compilação) procuram |
|---|---|
| Build Tools | `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat` |
| LLVM | o `clang-cl` no PATH, ou `C:\Program Files\LLVM\bin\clang-cl.exe` |
| CMake | o `cmake` no PATH, ou `C:\Program Files\CMake\bin\cmake.exe` |
| Ninja | o `ninja` no PATH, ou `%LOCALAPPDATA%\Microsoft\WinGet\Links\ninja.exe` |

Duas causas comuns:

- **Você instalou o Visual Studio completo (Community/Professional) em vez do "Build Tools".** Instale o
  **Build Tools for Visual Studio** — é um item separado, na mesma página da Microsoft, e é o que cai na pasta que a
  compilação espera.
- **Você já tinha outra versão do Visual Studio** (por exemplo a de 2022) e a compilação procura a pasta da versão nova
  (a pasta `18`). Nesse caso, avise quem te passou o pacote: **este é um ponto conhecido em aberto** — a compilação
  deveria achar a sua instalação sozinha.

## 3. "1) Conferir o jogo" diz que o EBOOT é de outra versão

As duas mensagens possíveis, e o que cada uma significa:

| Mensagem | O que significa |
|---|---|
| `ERRO: o codigo e BCUSxxxxx; este port e do BCUS98472 (disco americano).` | Você apontou para **outro jogo** (ou outra região). Escolha a pasta do **PlayStation All-Stars Battle Royale, disco, BCUS98472** (a que tem `PS3_GAME` dentro). |
| `ERRO: EBOOT.BIN diferente do disco 1.00 (SHA ...). Escolha a pasta do DISCO` | A pasta escolhida na página Início tem de ser a do **disco 1.00** (BCUS98472). Se você tem o update 1.12 e as DLC (no RPCS3: `dev_hdd0\game\BCUS98472`), eles entram **separados**, pelos botões **7) Update 1.12 + DLC** e **8) Conferir ELF 1.12**, antes do passo 5. A versão só digital (sem o disco) ainda não é suportada. |

O que **é** conferido: o código do jogo (`TITLE_ID`, lido do `PARAM.SFO`) e o `EBOOT.BIN`, por impressão digital
(SHA-256). Nada do jogo sai do seu PC.

### "3) Conferir ELF" diz que o `.elf` não é o esperado

A mensagem é `ERRO: o .elf nao e o esperado (SHA ...). Decripte o EBOOT.BIN do disco 1.00 de novo.` — quer dizer que o
arquivo escolhido não veio do EBOOT do disco 1.00. Decripte de novo, com atenção:

1. No **seu** RPCS3 (o emulador), com o firmware do PS3 instalado nele.
2. Menu **Utilities → Decrypt PS3 Binaries**.
3. Escolha o `PS3_GAME\USRDIR\EBOOT.BIN` **da pasta do disco** — não o do update, se você tiver o update instalado no
   RPCS3: esse é outro arquivo e não serve.
4. O RPCS3 grava o `EBOOT.elf` na mesma pasta. Volte ao Launcher e clique em **3) Conferir ELF** (ele acha o arquivo
   sozinho; se houver mais de um, aponte o certo na mão).

O RPCS3 é usado **só para decriptar** o seu arquivo. O jogo não roda nele por causa do port.

## 4. "5) Gerar e compilar" falhou

**Onde está o log:** não existe arquivo — a compilação inteira é escrita **na caixa preta da própria página Preparar**,
embaixo dos botões. O Launcher mostra cada passo, o comando e a saída dele. Quando um passo falha, a última linha é:

```
  ERRO em '<nome do passo>' (código N). Copie as linhas acima e mande para quem te passou o jogo.
```

Copie **as linhas dessa caixa** (do `>>>` do passo até o `ERRO`) e mande junto com o resto do item 13.

Causas comuns, em ordem:

| Sintoma na caixa | O que fazer |
|---|---|
| Um passo marcado `PENDENTE` | Esse passo não tem comando nesta versão do kit. Mande a linha para quem te passou o pacote. |
| Falha logo no começo, com erro do `vcvars64.bat` ou algo "não é reconhecido" | Ferramenta faltando ou fora do lugar: volte ao item 2. |
| `BUILD FALHOU: codigo N -- o .exe ... NAO foi atualizado` | A compilação parou no meio. Feche jogos, navegador e outros programas pesados (a compilação usa muita memória) e clique em **5) Gerar e compilar** de novo — ela continua de onde parou. |
| Falha sempre no mesmo arquivo | Anote o **nome do passo** e as últimas linhas e mande para quem te passou o pacote. |

As primeiras vezes demoram **dezenas de minutos** (é o jogo inteiro sendo traduzido e compilado). Depois disso,
recompilar é rápido. **Não feche a janela** enquanto estiver compilando.

## 5. "6) Conferir o exe" avisou que o exe saiu diferente

Se aparecer `AVISO: o exe saiu diferente do de referencia (SHA ...)`, **não é erro fatal**: o jogo provavelmente abre e
funciona. O aviso existe porque as duas pontas de uma partida em LAN precisam ter sido compiladas da mesma forma para a
conexão ser garantida. Se você instalou uma versão diferente de alguma ferramenta de compilação (item 2), o programa
final sai diferente mesmo com o mesmo jogo.

## 6. O jogo abre em tela preta

Em ordem de probabilidade:

1. **É o carregamento.** Antes da primeira imagem aparecer, o jogo lê e prepara muita coisa: dependendo do PC isso leva
   um tempo, com a tela preta parada. Espere ~1 minuto antes de concluir que travou. Se o
   `user\logs\last_run.log` continua crescendo, **não travou**.
2. **Cache do jogo de uma sessão que foi fechada à força.** Feche o jogo e abra de novo **pelo Launcher** (ou pelo
   `Jogar All-Stars.bat`): ele limpa o cache do jogo a cada partida, e isso costuma resolver. Se você abriu o
   `PSASBR.exe` direto, pela pasta `build\`, o cache antigo pode estar no caminho — use o Launcher.
3. **Shaders preparados pela metade.** Abra o Launcher → **Avançado → Recompilar shaders** e deixe terminar (a barra
   "Preparando os shaders"). Se falhar, o Launcher avisa "a compilacao de shaders falhou" e o motivo está em
   `user\logs\shaders.log`.
4. **Placa de vídeo / driver.** O port precisa de uma placa com **Direct3D 12** (Windows 10/11 64 bits) e de um driver
   atualizado. Driver velho é uma causa clássica de tela preta e de o jogo "voltar sozinho" para a área de trabalho.
   Atualize o driver no site do fabricante da sua placa (NVIDIA / AMD / Intel) e tente de novo.

Se mesmo assim ficar preto, mande o `user\logs\last_run.log` (item 13): ele diz onde o jogo parou.

## 7. A primeira partida engasga / "Preparando os shaders"

**É esperado.** Na primeira vez que um efeito aparece, o jogo precisa compilá-lo: a partida dá umas travadas curtas.
A partir daí, a tela **"Preparando os shaders"** deixa tudo pronto antes de cada partida — ela aparece só na 1a vez,
ou depois de você atualizar o port ou o driver.

- A janela tem os botões **"Jogar mesmo assim"** (abre o jogo já, e ele termina de compilar enquanto você joga) e
  **"Cancelar"**.
- Se parar no meio, **na próxima vez continua de onde parou**.
- Avançado → **Limpar cache de shaders** obriga tudo a ser compilado de novo (útil depois de trocar de placa ou driver).

## 8. O controle não é reconhecido

- Controles **Xbox** e **XInput** funcionam direto, sem instalar nada.
- **DualShock 4 e DualSense** também funcionam direto, por USB ou Bluetooth: o port lê o controle pela porta HID e não
  precisa de DS4Windows.
- **Controle genérico que só aparece como "DInput"** (sem XInput) pode não ser reconhecido. Duas saídas: (a) usar o
  teclado; (b) usar um programa que exponha o controle como XInput (por exemplo o **Steam**, com o jogo adicionado como
  "jogo não-Steam", ou o **DS4Windows**) — aí o port o vê como um controle normal.
- Confira em Launcher → **Controles → Tipo de controle**: `Automático` é o padrão e é o certo para a maioria dos casos.
  Se você escolher `Xbox / XInput` com um DualSense na mão, os **nomes dos botões na tela** ficam trocados (o controle
  continua funcionando, mas o desenho não bate).
- Um controle **conectado tem prioridade sobre o teclado**. A lista de botões é editável: clique na linha da função e
  aperte o botão novo (Esc cancela). O botão **Padrão** volta tudo ao de fábrica.
- Vários controles ao mesmo tempo funcionam (até 4 lutadores).

### O teclado não funciona

O teclado só vale na porta 1 **quando não há controle ligado nela**, e **a janela do jogo precisa estar em primeiro
plano** (clique nela). As teclas ficam em `user\keymap.ini`, editáveis na página **Controles → Tipo de controle =
Teclado** (a coluna "TECLA" é o que o jogo recebe).

## 9. O antivírus / o Windows bloqueia o programa

O `PSASBR.exe` é **compilado no seu próprio PC e não tem assinatura digital** — por isso o Windows e alguns antivírus
desconfiam dele:

- **"O Windows protegeu o seu PC" (SmartScreen)**: clique em **Mais informações → Executar assim mesmo**. É o aviso
  padrão para programa sem assinatura; como o arquivo foi compilado por você, é seguro.
- **O antivírus apaga ou põe em quarentena** o `PSASBR.exe` (ou atrapalha a compilação): coloque a **pasta do port** na
  lista de exceções do antivírus e compile de novo. Antivírus muito agressivo também deixa a compilação lenta.
- **O Windows bloqueou um arquivo "que veio da internet"**: clique com o botão direito no arquivo → **Propriedades** →
  marque **Desbloquear**.
- Na LAN, o Windows pergunta se o jogo pode usar a rede: marque **"Redes privadas"** e clique em **Permitir** (as portas
  usadas são **UDP 4658, 4659 e 4660**, nada TCP). Se você clicou em "Cancelar", refaça em
  *Painel de Controle → Firewall do Windows → Permitir um aplicativo*.

## 10. Não acha a sala / o amigo / a partida em LAN

Isso tem guia próprio: `docs/COMO_JOGAR_COM_AMIGO.md` (seção "Se der errado"). O resumo: os dois na **mesma rede local**
e os **IPs digitados trocados certo** no menu do jogo (**tecla F3** — o seu em "meu" e o do
amigo em "amigo"). Testar sozinho com duas janelas no mesmo PC **não funciona**.

## 11. Outras mensagens do Launcher (e o que elas querem dizer)

| Mensagem | O que fazer |
|---|---|
| "Escolha a pasta do seu jogo na página Início." | Você clicou em **JOGAR** antes de escolher a pasta. Início → **PASTA DO JOGO** → escolha a que tem `PS3_GAME`. |
| "nao achei o exe do jogo (PSASBR.exe): faca a aba 'Preparar com o seu jogo' primeiro" | Falta o passo **5) Gerar e compilar**. O jogo não vem no pacote: ele é compilado na sua máquina. |
| "abra o Launcher uma vez e escolha a pasta do jogo" (no `Jogar All-Stars.bat`) | O atalho direto usa o que está salvo. Abra o `Abrir Launcher.bat`, escolha a pasta e clique em **Salvar**. |
| "O jogo anterior ainda está aberto. Fechar e abrir de novo?" | Responda **Sim**. Se ele não conseguir fechar, abra o **Gerenciador de Tarefas** (Ctrl+Shift+Esc), encerre o `PSASBR.exe` e tente de novo. |
| "Não consegui fechar o jogo anterior." | Feche o `PSASBR.exe` no Gerenciador de Tarefas e clique em JOGAR outra vez. |
| "os arquivos do jogo mudaram durante o preparo; repita a compilacao de shaders" | Alguém mexeu na pasta do jogo enquanto os shaders eram preparados. Feche tudo, deixe a pasta quieta e clique em JOGAR de novo. |
| "o executavel mudou durante o preparo; repita a compilacao de shaders" | Você recompilou o port enquanto os shaders preparavam. Deixe a compilação terminar e abra o jogo de novo. |
| "nao foi possivel identificar os shaders do disco/update/DLC; preparo nao confirmado" | O exe não conseguiu ler a origem dos shaders do seu jogo. Confira se a pasta escolhida é a certa (item 3) e tente de novo. |
| "Nick inválido: 3 a 16 letras, números, - ou _, começando por letra." | Só no campo de nick do online: comece por letra, use de 3 a 16 caracteres. |
| Na página Gráficos: **"em breve"** / **"próximo build"** | `em breve` = a opção é guardada, mas o jogo ainda não a lê. `próximo build` = o port já tem, mas **o seu exe** (compilado antes) não: recompile (página Preparar) para ela passar a valer. |
| "Este exe ainda não pré-compila shaders (entra num próximo build)." | Normal num exe antigo: recompile o port para ter o preparo de shaders antes da partida. |
| "Ainda não existe: <arquivo>" | Aquele arquivo ainda não foi criado (por exemplo o log, antes da primeira partida). Jogue uma vez e ele aparece. |

## 12. Opções que não fazem efeito

Clique em **Salvar** antes de jogar — opções não salvas não valem. Depois de salvar, o **idioma do jogo** vale na
**próxima** partida (o do Launcher troca na hora).

Uma observação importante: **as opções do Launcher e o menu F3 do jogo gravam no mesmo arquivo**, o
`port_settings.ini`. Vale sempre a **última** mudança que você fez, não importa por onde.

## 13. Se nada disso resolver: o que mandar

Abra uma *issue* na página do projeto no GitHub e anexe:

1. **`user\logs\last_run.log`** — o log da partida que deu errado (Launcher → **Avançado → Ver o último log**). É o
   item mais importante; sem ele ninguém consegue dizer o que houve.
2. O texto da caixa da página **Preparar**, se o problema foi na compilação (item 4).
3. O arquivo **`ORIGEM_KIT.txt`**, que vem na pasta do port (diz qual versão do pacote você tem).
4. O que você tem: **Windows 10 ou 11**, qual **placa de vídeo** e versão do driver, e o que você fez antes do erro.

> **Não mande nada do jogo** (nem `EBOOT.BIN`, nem `.elf`, nem `.psarc`, nem texturas, áudio ou saves). Ninguém precisa
> disso para ajudar, e o projeto não distribui conteúdo do jogo.