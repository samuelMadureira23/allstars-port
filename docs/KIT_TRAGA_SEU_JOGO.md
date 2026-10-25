# Kit "traga seu jogo" (T-241) — 1ª versão distribuível

Pedido do Samuel (19/10/2026 ~12:05): montar algo que ele possa distribuir para um amigo que TEM o jogo, para o amigo
pegar a cópia dele e chegar ao **mesmo build** que o Samuel tem, e os dois jogarem pela LAN.

## Princípio (AGENTS.md §8)
O pacote leva **só o nosso código e as nossas ferramentas**. Nunca: EBOOT/ELF decriptado, código gerado a partir do jogo
(`work/recompiled_1.00`, `work/spu/lifted`), exe do port, .psarc, texturas/áudio/vídeo, firmware, chaves, capturas.
Tudo que deriva do jogo é **gerado na máquina do amigo, a partir da cópia dele**. Quem envia o pacote é o Samuel (ação
externa); antes, o crítico audita o conteúdo.

## Fluxo proposto (a validar)
1. **Conferir a cópia:** o script lê `PS3_GAME/PARAM.SFO` e o `EBOOT.BIN` do amigo e confere o SHA-256 contra o do disco
   BCUS98472 1.00 que usamos (a tabela por versão do §7 já usa o SHA do ELF). Versão diferente → para com mensagem clara.
2. **Decriptar o EBOOT localmente:** com o RPCS3 do próprio amigo (Utilities → Decrypt PS3 Binaries, como fizemos em
   14/10) ou ferramenta equivalente que ele instala; o script só guia e confere o SHA do ELF resultante.
3. **Gerar e compilar:** o script roda os lifters (PPU e SPU) e o build (`scripts\build.bat`) com o mesmo commit do
   build-samuel. Exige no PC do amigo: Python, VS Build Tools + LLVM + CMake + Ninja (versões do §5) — o script verifica e
   diz o que falta (não instala nada sozinho).
4. **Conferir o resultado:** o exe gerado deve ter o **mesmo SHA** do build-samuel (build reprodutível) — se não tiver,
   diz onde divergiu. Copia o shadercache? NÃO (é derivado de shaders do jogo): o cache se forma no PC do amigo.
5. **Jogar:** atalho "Jogar LAN" com o IP local de cada um (depende da mudança do claude-net no filtro de
   IPs, T24).

## Donos sugeridos (T24)
claude-int (pipeline e build reprodutível) · Codex (script do kit + testes sem jogo, com o 2º PC do Samuel como 1º
"amigo", ver docs/SEGUNDO_PC.md) · claude-net (LAN) · claude-critico (auditoria do pacote antes de o Samuel enviar).

## Perguntas em aberto
- O build é reprodutível hoje (mesmo SHA em duas máquinas)? Caminhos absolutos e datas no exe podem mudar o SHA.
- Tempo de lift + compilação num PC comum (estimar no 2º PC).
- Versão do jogo do amigo (disco 1.00 × digital × com update 1.12).

## Launcher (pedido do Samuel, 19/10 20:08) — junta o kit (T-241) e as opções de PC (T-256)
Como nos ports oficiais de PC (ex.: launchers de ports de PS4), um programa que abre ANTES do jogo:
1. **1ª vez — 'Preparar com o seu jogo':** aponta a pasta do jogo do usuário, confere a versão (BCUS98472 1.00), guia a decriptação
   do EBOOT, gera e compila o port localmente e confere o SHA do exe (fluxo do kit acima). Mostra progresso e o que falta instalar.
2. **Opções de PC** (antes de abrir o jogo): resolução, janela/tela cheia, escala interna, VSync/limite de fps, mostrar fps, controles
   (remapear), volume, idioma, pasta de saves → grava `port_settings.ini` (o mesmo que o menu F2 dentro do jogo lê).
3. **Botões:** Jogar · Jogar LAN com o IP de cada um · Abrir pasta de capturas/saves.
Implementação sem download, se possível (Python/tkinter ou Win32 nativo com o toolchain do §5); empacotar como exe pede ferramenta
(ex.: PyInstaller) = download → ok do Samuel. Donos sugeridos: Codex (launcher + testes) + claude-int (build reprodutível) +
claude-net (LAN) + claude-critico (auditoria antes de o Samuel distribuir).

## Antes de qualquer publicação PÚBLICA

- **REVISAR `launcher/assets/controles/`**: fotos de produto dos controles (Sony DualShock 4 / DualSense, Microsoft Xbox), versionadas por decisão do Samuel (20/10) e usadas pela página Controles do launcher e pelo menu F3. No pacote PRIVADO ao amigo podem ir (coordenador #4899); numa publicação aberta, trocar por desenho próprio (o launcher já cai no desenho em linhas sem as fotos) ou confirmar o direito de uso. Para tirar do pacote: excluir a pasta em `kit/montar_pacote.py`.
