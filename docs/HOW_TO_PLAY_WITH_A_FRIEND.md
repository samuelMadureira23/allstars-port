# How to play with a friend over the internet (Radmin VPN)

A guide for non-technical users. The two of you play the **PC port** of PlayStation All-Stars Battle Royale, each on your
own computer, connected through a **virtual network** (Radmin VPN). The game thinks you are both in the same house (LAN).

> **Important:** this package does NOT include the game. Each of you needs **your own copy of the disc** (BCUS98472,
> version 1.00); the 1.12 update and the DLC are optional (Prepare buttons 7 and 8). Both players need the SAME version.
The port is built on your PC from your game, by the **Launcher**.

> The Launcher opens in English by default and can be switched to Portuguese; the Portuguese button names are kept in
> parentheses because the language selector still offers Portuguese.

---

## Part 1 — Build the port on your PC (first time only)

1. Double-click **`Open Launcher.exe`** (in the port folder).
   - If you see "Não achei um Python 3 com tkinter" ("I could not find a Python 3 with tkinter"): install **Python 3**
     from python.org. During setup, tick **"Add python.exe to PATH"** and leave the **"tcl/tk and IDLE"** option ticked.
     Then open the Launcher again.
2. Page **"Início"** (Home): click **Escolher...** (Choose...) and pick the folder of your game (the one that has the
   `PS3_GAME` folder inside).
3. Page **"Preparar"** (Prepare), follow the buttons in order:
   1. **1) Conferir o jogo** (Check the game).
      You should see "OK: EBOOT.BIN igual ao do disco 1.00". If it says the file is different, pick the DISC
      folder (the update goes in separately, with buttons 7 and 8).
   2. **2) Como decriptar** (How to decrypt): shows how to use **your RPCS3** (the emulator) to produce the `EBOOT.elf`
      file. In short: in RPCS3, menu *Utilities → Decrypt PS3 Binaries*, choose the `PS3_GAME\USRDIR\EBOOT.BIN` of your
      game.
   3. **3) Conferir ELF** (Check the ELF): checks the generated file and puts it in the right place.
   4. **4) Ferramentas** (Tools): tells you what is missing to build (Visual Studio Build Tools with C++, LLVM, CMake,
      Ninja). The Launcher **installs nothing by itself**: it only shows the name; install it and click again.
   5. **5) Gerar e compilar** (Generate and build): generates the code from your game and builds it. It takes a while
      (tens of minutes).
   6. **6) Conferir o exe** (Check the exe): checks the program that was generated.
   7. **Optional — 7) Update 1.12 + DLC** and **8) Conferir ELF 1.12**, BEFORE step 5: pick the update folder in your
      RPCS3 (`dev_hdd0\game\BCUS98472`) and decrypt that folder's `USRDIR\EBOOT.BIN` in RPCS3 as in step 2. Step 5 then also
      builds 1.12 (Portuguese text, DLC fighters and stages) and the game starts on 1.12.

The first time you play, the game compiles effects while you play, so the first match may hitch a little. The
**Preparando os shaders** (Preparing shaders) screen compiles the shaders before a match, which reduces the hitches; a
short hitch may still happen in the first match of each stage.

## Part 2 — Options (optional)

Pages **"Gráficos"** (Graphics) and **"Controles"** (Controls): internal resolution (1440p or 4K make the image
sharper), VSync, sound, keyboard key file. The ones marked **"em breve"** (coming soon) are saved, but the game does not
use them yet. Click **Salvar** (Save).

## Part 3 — Join the same network (Radmin VPN), both of you

1. Each of you installs **Radmin VPN** (free, official site radmin-vpn.com) and opens it.
2. **One** of you creates the network: *Rede → Criar rede* (Network → Create network), picks a name and a password, and
   gives both to the friend.
3. The **other** one joins: *Rede → Entrar em uma rede existente* (Network → Join an existing network), with the same
   name and password.
4. At the top of the Radmin window you see **your IP**, something like **26.x.x.x**. Each of you writes down YOURS and
   sends it to the friend. When you are both on the same network, the friend's name appears in the list with a green dot.

## Part 4 — Allow it through the Windows firewall (both of you, first time)

On the first match, Windows asks whether **PlayStation All-Stars Battle Royale** (PSASBR.exe) may use the network: tick
**"Private networks"** and click **Allow**. The game only uses ports **UDP 4658, 4659 and 4660** (no TCP).
If you clicked "Cancel" by accident: *Control Panel → Windows Firewall → Allow an app* and tick PlayStation All-Stars
Battle Royale (PSASBR.exe) under "Private".

## Part 5 — Play together

Open the game as usual (Launcher → **JOGAR**, or `Play All-Stars.exe`). The online match is set up **inside the game**:
press **F3** to open the online menu, where each of you enters **your own Radmin IP** (26.x.x.x) and **your friend's**, and
chooses who creates the room.


## If something goes wrong

| Problem | What to do |
|---|---|
| The room is not found / it keeps waiting for the friend | Check both: you are on the **same Radmin network** (green dot) and the IPs typed in the F3 menu are **swapped the right way** (yours in "meu"/mine, the friend's in "amigo"/friend). |
| Windows never asked about the firewall and nothing connects | Allow PSASBR under "Private networks" (Part 4). |
| It works with one friend but not another | The port only talks to the 2 IPs you typed: check the new friend's IP. |
| Testing alone with 2 windows on the same PC | **Not possible** with the Radmin IP (Windows does not allow it). You need 2 PCs. |
| The game stays on a black screen at the start | Close it and open it again from the Launcher (it clears the game's cache every match). |
| Any other error | Open an *issue* on the project's GitHub page and attach the `user\logs\last_run.log` file from the port folder (Launcher → Avançado → Ver o último log). |

## Next times

- **`Play All-Stars.exe`** opens the game directly, with the folder and options saved (no need to go through the Launcher).
- Launcher → **Avançado → Criar atalho** (Advanced → Create shortcut) puts the **Play All-Stars** shortcut on the desktop.
- Saves, cache and logs live in the port's **`user\`** folder: keep that folder if you update the port.