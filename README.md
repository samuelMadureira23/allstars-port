# PlayStation All-Stars Battle Royale: native PC port (Windows)

Native Windows x64 port of PlayStation All-Stars Battle Royale (BCUS98472 / NPUA80316), built by static recompilation from a fork of [ps3recomp](https://github.com/sp00nznet/ps3recomp). It uses Direct3D 12 and does not rely on an emulator at runtime.

**Community:** ps3recomp Discord, sp00nznet recomp server (https://discord.gg/CRpzGWZFcu), user `@samukambr`.

## About the project

The original game was compiled for the PlayStation 3 Cell processor. This project translates the code of the main processor (PPU) and of the synergistic processing units (SPU) to C, compiles that code together with a layer that replaces the console libraries, and forwards the graphics commands to Direct3D 12. The result is a native executable with no instruction-level emulation at runtime.

The port is generated on the user's computer from the user's own copy of the game: the US disc (as a folder or an ISO) or the US digital version with the user's own license. This repository does not contain the EBOOT, generated game code, the port executable, .psarc files, textures, audio, video, firmware, licenses or saves.

## What works

- Menus, character selection, battles with up to four fighters, stages and effects.
- **Online over the internet**: **internet rooms** listed inside the game (F3 → Online), with no IP typing. Local network and gaming VPN also work. It uses the game's own netcode. The host can close their room at any time.
- On the test computer (Ryzen 7 7700 and RTX 5070), two-player battles hold 60 fps with internal resolution up to 3x, FXAA and anisotropic filtering. Four-player battles run close to 50 fps. Performance on more modest computers is still being measured.
- **Fast loading** (on by default): fights load in about 4 seconds, and **Skip the intro** reaches PRESS START in about 5 seconds.
- **The intro movie plays**, with sound (START skips it). It needs the FFmpeg libraries (LGPL), downloaded by the launcher from the release attachment.
- **Mouse and keyboard like a PC game**: point and click in every menu (including the button hints), arrows/WASD + Enter/Esc in menus, your fight keys in the fight. Mouse and keyboard always work in menus, even with a controller as Player 1.
- DualShock 4, DualSense, Xbox and generic controllers, including several at the same time, plus the keyboard. Controllers can be plugged in with the game open. Each player's device can be chosen live in **F3 → Controls → Players**, and buttons can be remapped in **F3 → Controls → Change buttons**.
- **Button icons follow your device**: keyboard keys, Xbox 360 buttons or PS3 buttons, switching to the last device you used (or fixed to one).
- Shader pre-compilation before a match, which reduces the initial hitches.
- **In-game PC options (F3):** video (window mode, anti-aliasing, sharpening, anisotropic filtering, VSync live; resolution and frame limit on restart), audio, controls and online.
- **Mods** button in the Launcher: install, enable, disable, reorder and remove mods (mod creation is still in development; no mods are included).
- Audio reconnects by itself if the output device fails or the Windows default output changes.

## Requirements

- Windows 10 or 11, 64-bit, with a Direct3D 12 capable GPU.
- Your own copy of PlayStation All-Stars Battle Royale, one of:
  - the **US disc, BCUS98472**, as a folder (the one with PS3_GAME) or as an **ISO** (no need to extract it; encrypted ISOs work with your own disc key);
  - the **US digital version, NPUA80316**: your own PKG and **your own license** (the `.rap` file or its code). The launcher only uses what you provide; it never downloads, creates or bypasses a license, and the license never leaves your PC.
- The disc version (1.00) is just the starting point: the launcher updates the game to **1.12** by itself, from Sony's official server.
- Nothing else to decrypt the game: the Launcher decrypts your EBOOT.BIN by itself and keeps the result only if its SHA-256 matches. You do not need RPCS3 or the PS3 firmware.
- To build the port: Python 3 with Tcl/Tk plus a C++ compiler (the Microsoft compiler parts and LLVM clang-cl), CMake and Ninja. The Launcher downloads portable copies of the compiler by itself, from the official sources (about 1.1 GB to download, about 0.7 GB on disk, no administrator needed); only if that fails does it fall back to Visual Studio Build Tools (~3 GB) and the full LLVM (~4 GB) through winget. Building the game needs about 2 GB more free on C:. The "Install missing programs" button (Prepare tab) can install the missing build tools with `winget`, from official sources only: it first shows the list, source and size and asks for your confirmation, and accepting means accepting each package's license terms. Without `winget` it shows the official download links. It never installs the game or RPCS3. If Python 3 with Tcl/Tk is missing, "Open Launcher.exe" offers to install it the same way.

## How to play

1. Download the latest kit from [Releases](https://github.com/samuelMadureira23/allstars-port/releases), extract the zip and open **Open Launcher.exe**. The program is not signed, so Windows SmartScreen may say "Windows protected your PC". Click **More info**, then **Run anyway**.

   If Python 3 is missing, it offers to install it (official winget package, no administrator needed), then the Launcher opens by itself.
2. The first time, a **setup wizard** opens, in 3 steps:
   1. language and your nickname (used online);
   2. where your game is: **US disc** (folder or ISO; it searches by itself) or **US digital** (PKG plus your license);
   3. a settings preset (**Low-end**, **Mid-range**, **High-end** or **Custom**).

   The last button, **Prepare game**, starts preparing right away. It shows everything it will do and the free space:
   - download the 1.12 update from Sony's official server (about 1.1 GB; the newest version of the game, with the Portuguese text);
   - get the programs needed to build (portable compiler and LLVM, about 1.1 GB to download, plus CMake and Ninja), and the FFmpeg libraries for the intro movie (release attachment, checked by SHA-256). Only if the portable copies fail does it install Visual Studio Build Tools and LLVM through winget; then Windows asks for administrator permission: answer **Yes** (if the window does not show up, look for the blinking shield on the taskbar);
   - build the game (10 to 30 minutes depending on your PC, with progress).

   If something goes wrong, you get one short sentence with **Try again** and **Copy details**. If the 1.12 update is already in RPCS3 (`dev_hdd0/game/BCUS98472`), it uses that one by itself, without downloading.
3. Click **PLAY**. On the first match the game compiles its shaders and shows the progress. With the 1.12 update installed, **Add DLC** also shows up, for those who bought the DLC. If your game is an ISO and the PC was restarted, the launcher mounts it again by itself.

### After updating the kit

When you update the kit (the **Update** button in the top right corner of the main menu, or extracting a new zip over the old folder), click **PREPARE THE GAME** again (the first item of the main menu while the game needs building). The port code changed, so the game must be built again with the new code. The Launcher reminds you on the Home page, and **PLAY** asks for it before opening the game. The programs are already installed, so it is faster than the first time. Your `user\` folder (saves and settings) stays.

The detailed guide, for non-technical users, is in [docs/HOW_TO_PLAY_WITH_A_FRIEND.md](docs/HOW_TO_PLAY_WITH_A_FRIEND.md).

## Status

Work in progress, with regular releases (see [Releases](https://github.com/samuelMadureira23/allstars-port/releases)). The port is developed and tested on version **1.12**, and the launcher brings your game to it by itself. The additional content works for those who own it.

## Known issues

- Short hitches the first time an effect or stage appears, while the corresponding shaders are compiled. Pre-compilation reduces this, but a few occurrences remain in the first match of each stage.
- Occasional visual glitches in specific cases. Report them through Issues with a screenshot or video.
- Online over the internet depends on your network: if a direct connection between the two PCs is not possible, use a gaming VPN (a virtual LAN app on both PCs).
- The digital version is newer in the port: saving and loading, DLC and online between a disc player and a digital player are still being tested. Please report any problem.

## Guides

- [How to play with a friend](docs/HOW_TO_PLAY_WITH_A_FRIEND.md)
- [Common problems](docs/PROBLEMAS_COMUNS.md) (in Portuguese)
- [How to play online over the local network](docs/COMO_JOGAR_ONLINE_F3.md) (in Portuguese)

The launcher is in English by default. Some guides exist only in Portuguese; they are marked above.

## Feedback

The ps3recomp community is on their Discord (the sp00nznet recomp server), where the runtime development happens: https://discord.gg/CRpzGWZFcu. Look for `@samukambr` there. For reports that should stay on record, use the repository Discussions or Issues, or the **Report a problem** button on the launcher's Home. Do not send EBOOT, .psarc, keys, licenses (.rap), firmware or any game file; describe the problem and attach only the `user\logs\last_run.log` file, after reviewing it.

## Credits and license

- Base: [ps3recomp](https://github.com/sp00nznet/ps3recomp), MIT license, by Ned Heller (sp00nznet) and contributors. The original license is in src/ps3recomp/LICENSE.
- The intro movie is decoded with [FFmpeg](https://ffmpeg.org) libraries under the LGPL, distributed as a separate release attachment.
- [RPCS3](https://rpcs3.net) was used only as a behavioural reference during development, to compare the original game's output. It is not needed to play.
- PlayStation All-Stars Battle Royale is a trademark and property of Sony Interactive Entertainment. This project is not affiliated with Sony and does not distribute game content.

## Legal notice

This repository does not distribute the game or any file extracted from it. To use the port, you must own a legitimate copy of the game (the disc, or the digital version with your own license) and use your own files. The project is not affiliated with Sony Interactive Entertainment and is not intended to let people play the game without owning it.
