"""Decompile functions (by address) from the saved Ghidra project into work/decomp/.

Usage: python scripts/decompile.py 0x300150 0x17910 ...
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = r"C:\Users\samue\Documents\pes 13 descompilado\ferramentas"
GHIDRA = os.path.join(TOOLS, "ghidra", "ghidra_12.1.4_PUBLIC")


def main():
    env = dict(os.environ, JAVA_HOME=os.path.join(TOOLS, "jdk21"))
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
