"""Idioma do proprio launcher (Samuel 19/10, #4535): portugues (padrao) e ingles.

Os textos do launcher sao escritos em portugues e passam por t(); em ingles, t() devolve a traducao desta tabela
(o que faltar aqui continua em portugues). As linhas de log que vem do core.py (conferencias do jogo, do ELF, do exe)
ficam em portugues nesta versao.

DS-3 (21/10): em ingles nao sobra texto da interface sem traducao — nem os que chegam a t() por tabela (rotulo de
opcao, estado 'ativo'/'em breve', nome de botao do controle, nome das abas). O teste (launcher/test_launcher.py,
I18nTests) cobra isso sozinho: texto novo em t() ou em core.SETTINGS/controls reprova ate entrar aqui. O que nao
precisa entrar e' o que se escreve igual em ingles (marca, simbolo, nome impresso no controle): esta em SAME, com o
porque. needs_translation() e' a regra que o teste usa.
"""

LANGS = {"Português": "pt", "English": "en"}

_lang = "pt"


def set_lang(code):
    global _lang
    _lang = code if code in LANGS.values() else "pt"


def lang():
    return _lang


def t(text):
    if _lang == "en":
        return EN.get(text, text)
    return text


# Textos da interface que ja sao ingles (DS-3): marca, valor tecnico e nome impresso no proprio controle. Sem isto
# o teste cobraria traducao de 'DualShock 4' e de 'LB'. So entra aqui o que se escreve IGUAL nos dois idiomas.
SAME = {
    "DualShock 4", "DualSense (PS5)", "Xbox / XInput",          # marca
    "720p (1x)", "1440p (2x)", "4K (3x)", "4x", "8x", "16x", "FXAA",   # valor tecnico (a mesma grafia em ingles)
    "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "LS", "RS",     # letras/botoes impressos no controle
    "Menu", "OPTIONS", "SHARE", "CREATE",
    "L1", "R1", "L2", "R2", "L3", "R3", "START", "SELECT",      # nomes dos botoes do PS3 (iguais em ingles)
}


def needs_translation(text):
    """True se o texto da interface deveria ter traducao: tem letra e nao e' igual em ingles. Regra do teste."""
    return bool(text) and any(c.isalpha() for c in text) and text not in SAME


EN = {
    # janela e paginas
    "PlayStation All-Stars Battle Royale — port para PC": "PlayStation All-Stars Battle Royale — PC port",
    "Início": "Home", "Preparar": "Setup", "Gráficos": "Graphics", "Controles": "Controls",
    "LAN": "LAN", "Avançado": "Advanced", "Idioma": "Language",
    "Salvar": "Save", "Salvo.": "Saved.", "Há mudanças não salvas.": "There are unsaved changes.",
    # Inicio
    "Port para PC (BCUS98472, disco 1.00). Use a SUA cópia do jogo.":
        "PC port (BCUS98472, disc 1.00). Use YOUR copy of the game.",
    "Pasta do jogo:": "Game folder:", "Escolher...": "Browse...",
    "JOGAR": "PLAY", "JOGAR LAN": "PLAY LAN", "ONLINE (LAN)": "ONLINE (LAN)", "OPÇÕES": "OPTIONS", "PASTA DO JOGO": "GAME FOLDER", "‹ VOLTAR": "‹ BACK",
    "1ª vez? Vá à página 'Preparar'. Depois, o 'Jogar All-Stars.bat' abre direto com o que está salvo.":
        "First time? Go to the 'Setup' page. After that, 'Jogar All-Stars.bat' starts the game directly with your saved settings.",
    "Pasta do jogo (com PS3_GAME)": "Game folder (the one with PS3_GAME)",
    "Pronto para jogar.": "Ready to play.", "Falta:": "Missing:",
    "escolher a pasta do jogo": "choose the game folder",
    "decriptar e conferir o EBOOT (aba Preparar)": "decrypt and check the EBOOT (Setup page)",
    "gerar e compilar o port (aba Preparar)": "generate and build the port (Setup page)",
    # Preparar
    "Montar o port com o SEU jogo (só na 1ª vez). Siga os botões em ordem.":
        "Build the port from YOUR game (first time only). Follow the buttons in order.",
    "1) Conferir o jogo": "1) Check the game", "2) Como decriptar": "2) How to decrypt",
    "3) Conferir ELF": "3) Check the ELF", "4) Ferramentas": "4) Tools",
    "5) Gerar e compilar": "5) Generate and build", "6) Conferir o exe": "6) Check the exe",
    "7) Update 1.12 + DLC": "7) Update 1.12 + DLC", "8) Conferir ELF 1.12": "8) Check 1.12 ELF",
    "Opcional: com o update 1.12 + DLC, faça 7 e 8 antes do 5 (o 5 gera o 1.00 e o 1.12).":
        "Optional: with the 1.12 update + DLC, do 7 and 8 before 5 (step 5 builds both 1.00 and 1.12).",
    "Pasta do update 1.12 (no RPCS3: dev_hdd0/game/BCUS98472)": "1.12 update folder (in RPCS3: dev_hdd0/game/BCUS98472)",
    "  Update salvo. Agora decripte USRDIR\\EBOOT.BIN dessa pasta no RPCS3 e clique em 8.":
        "  Update saved. Now decrypt USRDIR\\EBOOT.BIN from that folder in RPCS3 and click 8.",
    "  Escolha antes a pasta do update (botão 7).": "  Choose the update folder first (button 7).",
    "EBOOT do update decriptado (.elf)": "Decrypted update EBOOT (.elf)",
    "  Pronto: o passo 5 vai gerar também o exe do 1.12, e o jogo passa a abrir no 1.12.":
        "  Done: step 5 will also build the 1.12 exe, and the game will start on 1.12.",
    "conferir o ELF do update 1.12 (aba Preparar)": "check the 1.12 update ELF (Prepare tab)",
    "Nada é baixado nem instalado automaticamente. A pasta do jogo é a escolhida na página Início.":
        "Nothing is downloaded or installed automatically. The game folder is the one chosen on the Home page.",
    "Conferindo o jogo (lê o EBOOT.BIN, pode levar alguns segundos)...":
        "Checking the game (reads EBOOT.BIN, may take a few seconds)...",
    "EBOOT decriptado (.elf)": "Decrypted EBOOT (.elf)", "Todos": "All files",
    "  Tudo pronto para compilar.": "  Everything is ready to build.",
    "  Passos com comando concluídos.": "  All steps with a command finished.",
    # Opcoes
    "'em breve' = guardado, mas o jogo ainda não lê; 'próximo build' = já existe no port, mas não no exe "
    "instalado. Clique em Salvar (embaixo) para guardar.":
        "'coming soon' = saved, but the game does not read it yet; 'next build' = the port has it, but the installed "
        "exe does not. Click Save (bottom) to keep your changes.",
    "ativo": "active", "em breve": "coming soon", "próximo build": "next build",
    "'próximo build' = já existe no port, mas não no exe instalado; 'em breve' = guardado, mas o jogo ainda não lê.":
        "'next build' = the port has it, but the installed exe does not; 'coming soon' = saved, but the game does not read it yet.",
    "Online": "Online", "Nick (seu nome no online)": "Nick (your online name)",
    "Preparando os shaders": "Preparing shaders", "Preparando os shaders...": "Preparing shaders...", "de": "of",
    "Falta cerca de": "About", "Pronto.": "Done.", "Jogar mesmo assim": "Play anyway", "Cancelar": "Cancel",
    "Só na 1ª vez (ou depois de atualizar o port ou o driver). Assim a partida não trava compilando.\nSe parar no meio, "
    "na próxima vez continua de onde parou.":
        "Only the first time (or after updating the port or the driver), so matches don't stutter compiling.\n"
        "If you stop halfway, next time it continues where it left off.",
    "Cancelado. Na próxima vez os shaders continuam de onde pararam.":
        "Cancelled. Next time the shaders continue where they left off.",
    "O jogo anterior ainda está aberto. Fechar e abrir de novo?": "The previous game is still open. Close it and open again?",
    "Fechando o jogo anterior...": "Closing the previous game...",
    "Não consegui fechar o jogo anterior. Feche-o e tente de novo.": "Could not close the previous game. Close it and try again.",
    "Nick inválido: 3 a 16 letras, números, - ou _, começando por letra.":
        "Invalid nick: 3 to 16 letters, digits, - or _, starting with a letter.",
    "Sala e IP do amigo: no jogo, tecla F3. Seu nick é o nome da sua sala: quem entra digita o nick de quem criou.": "Room and friend's IP: in the game, F3 key. Your nick is your room's name: whoever joins types the creator's nick.",
    "No jogo · F3: menu do port (online, desempenho, vídeo, áudio) · F9: fps":
        "In game · F3: port menu (online, performance, video, audio) · F9: fps",
    "Canto do fps na tela": "On-screen fps corner", "Só no título da janela": "Window title only",
    "Na tela: só fps": "On screen: fps only", "Na tela: fps + gráfico": "On screen: fps + graph",
    "Na tela: completo": "On screen: full", "Superior esquerdo": "Top left", "Superior direito": "Top right",
    "Inferior esquerdo": "Bottom left", "Inferior direito": "Bottom right",
    "Controles": "Controls", "Áudio": "Audio", "Tipo de controle": "Controller type", "Automático": "Automatic",
    "TECLADO": "KEYBOARD", "CONTROLE": "CONTROLLER", "Padrão": "Default", "aperte a tecla…": "press a key…",
    "Clique na tecla de um botão e aperte a tecla nova. O teclado vale quando não há controle ligado na porta 1.":
        "Click a button's key and press the new key. The keyboard is used when no controller is on port 1.",
    "Aperte o botão novo para": "Press the new button for",
    "(no controle, ou clique no botão do desenho; clique de novo no mesmo para cancelar).":
        "(on the controller, or click the button on the drawing; click the same one again to cancel).",
    "Clique num botão do desenho para trocar a função dele.": "Click a button on the drawing to change its function.",
    "Pular": "Jump", "Ataque 1": "Attack 1", "Ataque 2": "Attack 2", "Ataque 3": "Attack 3",
    "Defender / rolar": "Block / roll", "Pegar item": "Pick up item", "Super": "Super", "Pausa": "Pause",
    "Mover": "Move", "Analógico esq. ↑": "Left stick ↑", "Analógico esq. ↓": "Left stick ↓",
    "Analógico esq. ←": "Left stick ←", "Analógico esq. →": "Left stick →", "Esquiva ↑": "Dodge ↑",
    "Esquiva ↓": "Dodge ↓", "Esquiva ←": "Dodge ←", "Esquiva →": "Dodge →",
    "Teclado": "Keyboard", "Direcional": "D-pad", "FUNÇÃO NO JOGO": "IN-GAME ACTION", "BOTÃO": "BUTTON",
    "TECLA": "KEY", "aperte o botão…": "press a button…",
    "Aperte o botão novo (ou a tecla, no Teclado). Esc ou clicar de novo na linha cancela.":
        "Press the new button (or key, on Keyboard). Esc or clicking the row again cancels.",
    "Clique numa linha e aperte a tecla nova. O teclado vale quando não há controle ligado na porta 1.":
        "Click a row and press the new key. The keyboard is used when no controller is on port 1.",
    "Clique numa linha e aperte o botão novo no controle. Se o botão já tinha outra função, as duas trocam de lugar.":
        "Click a row and press the new button on the controller. If that button had another action, the two swap.",
    "Janela": "Window", "Sem borda": "Borderless", "Tela cheia": "Fullscreen", "Desligado": "Off", "Desligada": "Off",
    "Ligado": "On", "No título da janela": "In the window title", "Na tela": "On screen", "Mudo": "Muted",
    "Sem limite de fps: o jogo roda a lógica pelo quadro (60 por segundo); mais fps aceleraria a luta e um limite de 30 a deixaria em câmera lenta.":
        "No fps limit: the game runs its logic per frame (60 per second); more fps would speed the fight up and a 30 fps cap would put it in slow motion.",
    "Controle XInput (Xbox/DS4 via DS4Windows) funciona direto. O teclado usa o keymap.ini ao lado do exe\n"
    "(ou o arquivo escolhido acima). Padrão: quadrado/triângulo/círculo = ataques, X = pulo, R1 = defesa.":
        "XInput controllers (Xbox, or DS4 through DS4Windows) work directly. The keyboard uses keymap.ini next to the exe\n"
        "(or the file chosen above). Default: square/triangle/circle = attacks, X = jump, R1 = block.",
    "Resolução interna": "Internal resolution", "Janela / sem borda / tela cheia": "Window / borderless / fullscreen",
    "VSync": "VSync", "Mostrar fps": "Show fps",
    "Filtro anisotrópico": "Anisotropic filtering", "Antisserrilhado": "Anti-aliasing", "Nitidez": "Sharpening",
    "Arquivo de teclas (teclado)": "Key map file (keyboard)", "Som": "Sound", "Volume (%)": "Volume (%)",
    "Idioma do jogo (texto + dublagem)": "Game language (text + voice)",
    "Idioma do launcher": "Launcher language",
    "O idioma do jogo vale na próxima partida. O do launcher troca na hora.":
        "The game language applies from the next match. The launcher language changes right away.",
    # LAN
    "Os dois PCs na MESMA rede local. Guia: docs\\COMO_JOGAR_COM_AMIGO.md":
        "Both PCs on the SAME local network. Guide (Portuguese): docs\\COMO_JOGAR_COM_AMIGO.md",
    "Eu CRIO a sala (clico PRIMEIRO)": "I CREATE the room (I click FIRST)",
    "Eu ENTRO na sala do amigo (clico logo depois, até ~10 s)": "I JOIN my friend's room (I click right after, within ~10 s)",
    "Meu IP (192.168.x.x):": "My IP (192.168.x.x):", "IP do amigo:": "My friend's IP:",
    "JOGAR LAN": "PLAY LAN",
    "Abram JUNTOS (combinem 3, 2, 1): o menu anda num horário fixo até a luta (4–7 min).":
        "Start TOGETHER (count 3, 2, 1): the menu advances on a fixed schedule until the fight (4–7 min).",
    "Firewall: na 1ª vez, permita o PlayStation All-Stars Battle Royale em 'Redes privadas' (UDP 4658–4660).":
        "Firewall: the first time, allow PlayStation All-Stars Battle Royale on 'Private networks' (UDP 4658–4660).",
    # Avancado
    "Abrir a pasta user\\ (saves, cache, logs)": "Open the user\\ folder (saves, cache, logs)",
    "Ver o último log (user\\logs\\last_run.log)": "Open the last log (user\\logs\\last_run.log)",
    "Criar atalho 'Jogar All-Stars' na área de trabalho": "Create a 'Jogar All-Stars' shortcut on the desktop",
    "Limpar o cache do jogo (user\\cache)": "Clear the game cache (user\\cache)",
    "Abrir o guia de jogar com amigo": "Open the play-with-a-friend guide",
    "Problema? Mande o user\\logs\\last_run.log da partida que deu errado para quem te passou o jogo.":
        "Problem? Send the user\\logs\\last_run.log of the match that went wrong to whoever gave you the game.",
    "Ainda não existe:": "Does not exist yet:", "Atalho": "Shortcut", "Criado:": "Created:",
    "Não consegui criar o atalho:": "Could not create the shortcut:", "Cache": "Cache",
    "Apagar user\\cache? O jogo refaz o cache na próxima partida.":
        "Delete user\\cache? The game rebuilds it on the next match.",
    # Shaders (T-266)
    "Compilando shaders": "Compiling shaders", "Compilando shaders...": "Compiling shaders...",
    "Só na 1ª vez (ou depois de atualizar o port ou o driver). Depois o jogo abre direto.":
        "Only the first time (or after updating the port or the driver). After that the game starts right away.",
    "Recompilar shaders": "Recompile shaders", "Limpar cache de shaders": "Clear shader cache",
    "Ainda não há exe: faça a página Preparar primeiro.": "There is no exe yet: do the Setup page first.",
    "Apagar o cache de shaders? Na próxima partida eles são compilados de novo.":
        "Delete the shader cache? They are compiled again on the next match.",
    "Este exe ainda não pré-compila shaders (entra num próximo build).":
        "This exe cannot precompile shaders yet (coming in a later build).",
    "Shaders prontos.": "Shaders ready.",
    # Jogar
    "Jogar": "Play", "Escolha a pasta do seu jogo na página Início.": "Choose your game folder on the Home page.",
    "Abrindo o jogo...": "Starting the game...",
    "Jogo aberto": "Game started", "Não abriu:": "Did not start:",
    # Valores que chegam a t() por tabela (DS-3): idioma do jogo (core.GAME_LANGS) e nome do botao do Xbox.
    # O texto mostrado tambem e' o valor gravado no port_settings.ini, entao a volta (tela -> ini) e' cobrada no
    # teste: core.stored_value precisa achar o valor interno (core.OPT_LABELS).
    "Inglês (EUA)": "English (US)", "Espanhol": "Spanish", "Francês": "French",
    "Português (Brasil) — só com o update 1.12": "Portuguese (Brazil) — only with update 1.12",
    "Exibir": "View",
}
