# PlayStation All-Stars Battle Royale: native PC port (Windows)

**Português:** [README em português](README_GITHUB.md)

Native Windows x64 port of PlayStation All-Stars Battle Royale (BCUS98472), built by static recompilation from a fork of [ps3recomp](https://github.com/sp00nznet/ps3recomp). It uses Direct3D 12 and does not rely on an emulator at runtime.

**Bug reports:** contact `samukambr` on Discord, or open an issue in this repository.

## About the project

The original game was compiled for the PlayStation 3 Cell processor. This project translates the code of the main processor (PPU) and of the synergistic processing units (SPU) to C, compiles that code together with a layer that replaces the console libraries, and forwards the graphics commands to Direct3D 12. The result is a native executable with no instruction-level emulation at runtime.

The port is generated on the user's computer from the user's own copy of the game. This repository does not contain the EBOOT, generated game code, the port executable, .psarc files, textures, audio, video, firmware or saves. A copy of the BCUS98472 disc, version 1.00, is required.

## What works

- Menus, character selection, battles with up to four fighters, stages and effects.
- On the test computer (Ryzen 7 7700 and RTX 5070), two-player battles hold 60 fps with internal resolution up to 3x, FXAA and anisotropic filtering. Four-player battles run close to 50 fps. Performance on more modest computers is still being measured.
- DualShock 4, DualSense, Xbox and generic controllers, including several connected at the same time, plus the keyboard.
- Shader pre-compilation before a match, which reduces the initial hitches.
- Local network matches using the game's own netcode.

## Requirements

- Windows 10 or 11, 64-bit, with a Direct3D 12 capable GPU.
- Your own copy of PlayStation All-Stars Battle Royale on disc, BCUS98472, version 1.00. The EBOOT.BIN is checked by SHA-256.
- RPCS3 only to decrypt the EBOOT.BIN, through Utilities, Decrypt PS3 Binaries.
- To build the port: Python 3 with Tcl/Tk, Visual Studio Build Tools with C++ support, LLVM with clang-cl, CMake and Ninja. The Launcher reports what is missing and does not download or install anything.

## How to play

This repository contains development sources, patches and documentation. No downloadable package has been published in GitHub Releases yet. The steps below describe the development package; cloning this repository alone does not provide the complete runtime or Launcher.

1. Open **Open Launcher.exe**.
2. On the Home tab, select the game folder, the one that contains PS3_GAME.
3. On the Prepare tab, follow the steps in order: check the game, decrypt with RPCS3, check the ELF, verify the tools, generate and build the port, and check the executable. Generation and building take tens of minutes.
4. Optional: to use the 1.12 update and the additional content, before generating and building, use buttons 7 and 8 on the Prepare tab. Button 7 asks for the update folder, for example dev_hdd0/game/BCUS98472 in RPCS3. Button 8 checks the decrypted EBOOT.BIN from the update. The generation step then produces both the 1.00 and 1.12 versions, and the game opens in 1.12. The update and the additional content belong to the user and are installed in the user's RPCS3.
5. Click Play. On the first match, the Launcher compiles the game shaders and shows the progress.

The detailed guide, for non-technical users, is in [HOW_TO_PLAY_WITH_A_FRIEND.md](HOW_TO_PLAY_WITH_A_FRIEND.md).

## Status

Work in progress. Version 1.00 of the disc is the base; the 1.12 update, with the additional content, is supported on top of it. The digital-only version, without the disc, is not supported yet.

The minimum target computer is defined: a Xeon E5-2680 v4 processor and an AMD RX 580 with 8 GB or an NVIDIA GTX 1660 with 6 GB, at 60 fps in 1080p with internal resolution from 1x to 1.5x. That target is still being measured.

## Known issues

- Short hitches the first time an effect or stage appears, while the corresponding shaders are compiled. Pre-compilation reduces this, but a few occurrences remain in the first match of each stage.
- Occasional visual glitches in specific cases, such as some particle effects and the intro of certain stages.
- Online play outside the local network is not available yet.

## Guides

- [How to play with a friend](HOW_TO_PLAY_WITH_A_FRIEND.md)
- [Common problems](PROBLEMAS_COMUNS.md)
- [How to play online over the local network](COMO_JOGAR_ONLINE_F3.md)

## Feedback

Report bugs through GitHub Issues or contact `samukambr` on Discord. Include the game version, your hardware, the build and steps to reproduce the problem. The [ps3recomp Discord](https://discord.gg/CRpzGWZFcu) is also available for community discussion.

Review logs before sharing them: remove personal paths, IP addresses and account details. Do not attach game files, firmware or keys.

## Credits and license

- Base: [ps3recomp](https://github.com/sp00nznet/ps3recomp), MIT license, by Ned Heller (sp00nznet) and contributors. The original license is in src/ps3recomp/LICENSE.
- [RPCS3](https://rpcs3.net) was used as a behavioural reference.
- PlayStation All-Stars Battle Royale is a trademark and property of Sony Interactive Entertainment. This project is not affiliated with Sony and does not distribute game content.

## Legal notice

This repository does not distribute the game or any file extracted from it. To use the port, you must own a legitimate copy of the disc and obtain the EBOOT.BIN from it. The project is not affiliated with Sony Interactive Entertainment and is not intended to let people play the game without owning it.
