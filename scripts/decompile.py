"""Decompile functions (by address) from the saved Ghidra project into work/decomp/.

Usage: python scripts/decompile.py 0x300150 0x17910 ...
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GHIDRA = os.environ.get("GHIDRA_HOME", "")


def main():
    if not GHIDRA or not os.path.isfile(os.path.join(GHIDRA, "support", "analyzeHeadless.bat")):
        sys.exit("Set GHIDRA_HOME to your Ghidra installation directory and JAVA_HOME to your JDK.")
    env = dict(os.environ)
    cmd = [os.path.join(GHIDRA, "support", "analyzeHeadless.bat"),
           os.path.join(ROOT, "work", "ghidra_proj"), "ps3recomp_analysis",
           "-process", "EBOOT_1.00_disc.elf", "-noanalysis",
           "-scriptPath", os.path.join(ROOT, "scripts", "ghidra"),
           "-postScript", "DecompileAt.java", os.path.join(ROOT, "work", "decomp"), *sys.argv[1:]]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    for line in (p.stdout + p.stderr).splitlines():
        if "DecompileAt" in line or "ERROR" in line or "Exception" in line:
            print(line)


if __name__ == "__main__":
    main()
