# Engineering overview

The port recompiles the PS3 PPU and SPU code to native C/C++ and uses a runtime layer for console services. Graphics commands are translated to Direct3D 12. The [project README](../README.md) describes the current user-facing features and limitations.

## Repository contents

- `launcher/`: selected launcher modules.
- `scripts/` and `tools/`: analysis, build and development utilities.
- `patches/` and `backup/ps3recomp/`: runtime patches and the upstream revisions they target.
- `net/server/`: experimental local networking services.

This is a development snapshot, not a complete standalone build distribution. The runtime checkouts, generated code, game files and ready-to-run launcher package are not included. Patch directories record their upstream base in `BASE.txt` where available. No release package is currently published.

## Development tools

Configure paths for your machine instead of embedding local usernames or directories:

| Utility | Configuration |
| --- | --- |
| `scripts/run.ps1` | `PS3_VFS_ROOT`: your game's `PS3_GAME` directory |
| `scripts/decompile.py` | `GHIDRA_HOME`: Ghidra installation; `JAVA_HOME`: compatible JDK |
| `scripts/jogo_inventory.py` | `PS3_GAME_ROOT`: disc directory containing `PS3_GAME`; `PS3_PACKAGES_ROOT`: package directory; `PS3_UPDATE_ROOT`: installed update directory |

## Technical notes

- [Original native execution experiment](NATIVE_PROOF.md)
- [Differential testing](DIFFTEST.md)
- [PSARC analysis](PSARC.md)
- [Networking analysis](ONLINE_PROTOCOLO.md)
- [Contribution guidelines](../CONTRIBUTING.md)

Some technical notes document early experiments. Their dates and test scope matter; they are not current compatibility guarantees. Keep game versions and executable hashes separate when comparing results.
