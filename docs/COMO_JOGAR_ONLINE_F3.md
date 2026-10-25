# Jogar online com um amigo pelo menu F3 (rede local) — guia curto

Para o Samuel e o amigo. Vocês dois jogam o port, cada um no seu PC, na **mesma rede local**, e criam a sala **de dentro do jogo**, pelo menu **F3**. Não precisa de `.bat` especial nem de digitar o seu próprio IP: o port acha o IP local sozinho.

## Antes (só na 1ª vez, os dois)

1. Os dois computadores na **mesma rede local** (o mesmo roteador), por cabo ou Wi-Fi. Se a rede isolar os clientes (comum em Wi-Fi de visitantes), os dois não se enxergam.
2. Anote o **IP local do amigo** (o número `192.168.x.x` que ele te mandar; no Windows, `ipconfig` mostra em "Endereço IPv4").
3. **Firewall do Windows:** na 1ª partida o Windows pergunta se o jogo (**PSASBR.exe**) pode usar a rede: marque **Redes privadas** e clique em **Permitir**. O jogo usa só **UDP 4658, 4659 e 4660**.

## Jogar

1. Os dois abrem o jogo normalmente (pelo Launcher, aba Jogar, ou pelo `Play All-Stars.exe`).
2. Passem do **PRESS START** e **parem no MENU PRINCIPAL**. É importante: a sala tem de ser criada **antes** de entrar em Versus ou em qualquer outro modo.
3. Os dois apertam **F3**. Com **Tab**, vão até a aba **Online**.
   (No menu: **Tab** troca de aba, **setas ↑↓** escolhem a linha, **Enter** edita ou confirma, **Esc** ou **F3** fecha. Enquanto o menu está aberto, o controle não mexe no jogo.)
4. Os dois preenchem:
   - **Seu nick**: o seu nome no jogo (3 a 16 letras, números, `_` ou `-`, sem espaço). Ele fica salvo para a próxima vez.
   - **IP do amigo**: o IP local do amigo.
5. **Quem cria a sala** (por exemplo, o Samuel): vai em **Criar sala** e aperta **Enter**. Aparece "Criando a sala...". Feche o menu (**F3**).
6. **Quem entra** (o amigo): em **Sala (nick do amigo)** digita o **nick de quem criou**, exatamente igual (maiúsculas contam); depois vai em **Entrar na sala** e aperta **Enter**. Aparece "Entrando na sala...". Feche o menu (**F3**). Faça isso **depois** que o amigo criou a sala (até ~1 minuto depois; a busca leva uns 20 segundos).
7. Daqui em diante é o próprio jogo: os dois aparecem na sala de **Versus LAN**, escolhem o lutador no controle, e quem criou a sala começa a partida.

## Se der errado

| O que aconteceu | O que fazer |
|---|---|
| "Confira o nick, o IP do amigo e a sala" | Nick com 3 a 16 caracteres, sem espaço; o IP do amigo preenchido; para entrar, a sala = nick de quem criou. |
| "Já há um pedido em andamento" | Já foi pedido; espere uns 30 s. Se nada acontecer, feche o jogo e comece de novo do menu principal. |
| Quem entra não acha a sala | Os dois na mesma rede local? IP do amigo certo dos dois lados? O nick em "Sala" igual ao de quem criou? Quem criou fez isso **primeiro**? Fechem os dois jogos e repitam. |
| Criei a sala depois de entrar em Versus | Não funciona assim: feche o jogo, abra de novo e use o F3 ainda no menu principal. |
| Nada conecta e o Windows não perguntou do firewall | Libere o PSASBR.exe em "Redes privadas" (Painel de Controle → Firewall do Windows → Permitir um aplicativo). |
| Trocou o build e o Windows perguntou do firewall de novo | Normal: a regra vale por arquivo; aceite "Redes privadas" outra vez. |
| Testar sozinho com 2 janelas no mesmo PC | Pela rede local, não dá (o Windows não roteia entre o IP da rede e o próprio PC). Precisa de 2 PCs. |

O que já foi provado (T28, 20/10 04:40): duas cópias do port fizeram exatamente esse caminho do F3 (criar / entrar pelo nick) e chegaram à luta e à tela de **MATCH SUMMARY** igual nas duas janelas (`work/runs/claude-net-LANMENU1_{A,B}05.png`). Ainda **não testado entre dois PCs de verdade** na rede local: a 1ª partida do Samuel com o amigo é esse teste. O guia do Launcher com o kit do amigo é o `docs/COMO_JOGAR_COM_AMIGO.md`.
