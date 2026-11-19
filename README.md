# PlayStation All-Stars Battle Royale: native PC port (Windows)

Native Windows x64 port of PlayStation All-Stars Battle Royale (BCUS98472), built by static recompilation from a fork of [ps3recomp](https://github.com/sp00nznet/ps3recomp). It uses Direct3D 12 and does not rely on an emulator at runtime.

**Community:** ps3recomp Discord, sp00nznet recomp server (https://discord.gg/CRpzGWZFcu), user `@samukambr`.

## About the project

The original game was compiled for the PlayStation 3 Cell processor. This project translates the code of the main processor (PPU) and of the synergistic processing units (SPU) to C, compiles that code together with a layer that replaces the console libraries, and forwards the graphics commands to Direct3D 12. The result is a native executable with no instruction-level emulation at runtime.

The port is generated on the user's computer from the user's own copy of the game. This repository does not contain the EBOOT, generated game code, the port executable, .psarc files, textures, audio, video, firmware or saves. A copy of the BCUS98472 disc, version 1.00, is required.

## What works

- Menus, character selection, battles with up to four fighters, stages and effects.
- On the test computer (Ryzen 7 7700 and RTX 5070), two-player battles hold 60 fps with internal resolution up to 3x, FXAA and anisotropic filtering. Four-player battles run close to 50 fps. Performance on more modest computers is still being measured.
- DualShock 4, DualSense, Xbox and generic controllers, including several connected at the same time, plus the keyboard.
- Shader pre-compilation before a match, which reduces the initial hitches.
- Online matches using the game's own netcode: local network, gaming VPN, and **internet rooms** listed in the game (no IP typing). The host can close their room at any time.
- **In-game PC options (F3):** video (anti-aliasing, sharpening, anisotropic filtering, window mode, VSync live; resolution and frame limit on restart), audio, controls and online.
- **Faster startup and loading** (optional, in OPTIONS → Loading): skip the startup warning and logos, shorter loading waits and a cache kept between matches.
- **Mods** button in the Launcher: install, enable, disable, reorder and remove mods (mod creation is still in development; no mods are included).
- Audio reconnects by itself if the output device fails or the Windows default output changes.

## Requirements

- Windows 10 or 11, 64-bit, with a Direct3D 12 capable GPU.
- Your own copy of PlayStation All-Stars Battle Royale on disc, BCUS98472, version 1.00. The EBOOT.BIN is checked by SHA-256.
- Nothing else to decrypt the game: the Launcher decrypts your EBOOT.BIN by itself and keeps the result only if its SHA-256 matches. You do not need RPCS3 or the PS3 firmware.
- To build the port: Python 3 with Tcl/Tk plus a C++ compiler (the Microsoft compiler parts and LLVM clang-cl), CMake and Ninja. The Launcher downloads portable copies of the compiler by itself, from the official sources (about 1.1 GB to download, about 0.7 GB on disk, no administrator needed); only if that fails does it fall back to Visual Studio Build Tools (~3 GB) and the full LLVM (~4 GB) through winget. Building the game needs about 2 GB more free on C:. The "Install missing programs" button (Prepare tab) can install the missing build tools with `winget`, from official sources only: it first shows the list, source and size and asks for your confirmation, and accepting means accepting each package's license terms. Without `winget` it shows the official download links. It never installs the game or RPCS3. If Python 3 with Tcl/Tk is missing, "Open Launcher.exe" offers to install it the same way.

## How to play

1. Download the latest kit from [Releases](https://github.com/samuelMadureira23/allstars-port/releases), extract the zip and open **Open Launcher.exe**. The program is not signed, so Windows SmartScreen may say "Windows protected your PC". Click **More info**, then **Run anyway**:

   If Python 3 is missing, it offers to install it (official winget package, no administrator needed), then the Launcher opens by itself.
2. The first time, the Launcher opens straight on the **PREPARE THE GAME** screen, in your Windows language (English or Portuguese; you can change it in Options). It looks for your game folder by itself (the one that contains PS3_GAME) and shows "found: ...", with **change** next to it if it is another one. It only asks for the folder if it can't find it.
3. Click **PREPARE THE GAME**. It reads your disc and shows **a single question** with everything it will do and the free space:
   - download the 1.12 update from Sony's official server (about 1.1 GB; the newest version of the game, with the Portuguese text);
   - get the programs needed to build (portable compiler and LLVM, about 1.1 GB to download, plus CMake and Ninja). Only if the portable copies fail does it install Visual Studio Build Tools and LLVM through winget; then Windows asks for administrator permission: answer **Yes** (if the window does not show up, look for the blinking shield on the taskbar);
   - build the game (10 to 30 minutes depending on your PC, with progress).
   Click **START** and it does everything in order. If something goes wrong, you get one short sentence with **Try again** and **Copy details**. If the 1.12 update is already in RPCS3 (`dev_hdd0/game/BCUS98472`), it uses that one by itself, without downloading.
4. Click **PLAY**. On the first match the game compiles its shaders and shows the progress. With the 1.12 update installed, **Add DLC** also shows up, for those who bought the DLC.

### After updating the kit

When you update the kit (the **Update** button in the top right corner of the main menu, or extracting a new zip over the old folder), click **PREPARE THE GAME** again (the first item of the main menu while the game needs building). The port code changed, so the game must be built again with the new code. The Launcher reminds you on the Home page, and **PLAY** asks for it before opening the game. The programs are already installed, so it is faster than the first time. Your `user\` folder (saves and settings) stays.

The detailed guide, for non-technical users, is in [docs/HOW_TO_PLAY_WITH_A_FRIEND.md](docs/HOW_TO_PLAY_WITH_A_FRIEND.md).

## Status

Work in progress, with regular releases (see [Releases](https://github.com/samuelMadureira23/allstars-port/releases)). The disc (version 1.00) is the base and the Launcher updates it to **1.12**, the version the port is developed and tested on, with the additional content for those who own it. The digital-only version, without the disc, is not supported yet.

## Known issues

- Short hitches the first time an effect or stage appears, while the corresponding shaders are compiled. Pre-compilation reduces this, but a few occurrences remain in the first match of each stage.
- Occasional visual glitches in specific cases. Report them through Issues with a screenshot or video.
- Online over the internet depends on your network: if a direct connection between the two PCs is not possible, use a gaming VPN (a virtual LAN app on both PCs).

## Guides

- [How to play with a friend](docs/HOW_TO_PLAY_WITH_A_FRIEND.md)
- [Common problems](docs/PROBLEMAS_COMUNS.md) (in Portuguese)
- [How to play online over the local network](docs/COMO_JOGAR_ONLINE_F3.md) (in Portuguese)

The launcher is in English by default. Some guides exist only in Portuguese; they are marked above.

## Feedback

The ps3recomp community is on their Discord (the sp00nznet recomp server), where the runtime development happens: https://discord.gg/CRpzGWZFcu. Look for `@samukambr` there. For reports that should stay on record, use the repository Discussions or Issues. Do not send EBOOT, .psarc, keys, firmware or any game file; describe the problem and attach only the `user\logs\last_run.log` file, after reviewing it.

## Credits and license

- Base: [ps3recomp](https://github.com/sp00nznet/ps3recomp), MIT license, by Ned Heller (sp00nznet) and contributors. The original license is in src/ps3recomp/LICENSE.
- [RPCS3](https://rpcs3.net) was used only as a behavioural reference during development, to compare the original game's output. It is not needed to play.
- PlayStation All-Stars Battle Royale is a trademark and property of Sony Interactive Entertainment. This project is not affiliated with Sony and does not distribute game content.

## Legal notice

This repository does not distribute the game or any file extracted from it. To use the port, you must own a legitimate copy of the disc and obtain the EBOOT.BIN from it. The project is not affiliated with Sony Interactive Entertainment and is not intended to let people play the game without owning it.
