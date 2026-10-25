"""Backup do código em repositórios PRIVADOS no GitHub do Samuel (pedido dele, 14/10/2026).

O que sobe (remote extra "backup"; os remotes originais não são tocados):
  - raiz (coordenação, docs, scripts, tools)  -> <usuario>/allstars-port      (privado), todas as branches
  - src/allstars-ps3 (todas as branches)        -> <usuario>/allstars-ps3-port  (privado)
  - src/ps3recomp: SÓ as nossas mudanças, como patches (git format-patch sobre o commit público
    39e4f49 do upstream) em backup/ps3recomp/<branch>/ dentro da raiz. O histórico do upstream traz
    fw_spu/ (firmware Sony recompilado) e não sai desta máquina.

Antes de cada push o script confere que nenhum arquivo rastreado é do jogo ou derivado dele
(extensões do jogo, código gerado, work/, arquivos > 2 MB) e aborta se achar algo.

Uso: python scripts/backup_github.py [--dry-run]
Requer: gh autenticado (gh auth login) com escopo repo.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
UPSTREAM_BASE = "39e4f49286447b3ae3dcc2358700c840860ee677"
BAD = re.compile(r"(\.(elf|self|bin|psarc|xvag|pam|at3|sfo|pkg|sprx|trp|edat|sdat|rap|bmp)$|"
                 r"(^|/)work/|ppu_recomp_\d+|spu_recomp\.[ch]$|(^|/)fw_spu/|(^|/)eboot)", re.I)
MAX_BYTES = 2 * 1024 * 1024
GIT_ID = []  # Use the repository's configured Git identity; never hard-code a personal email.


def run(cmd, cwd=ROOT, check=True, capture=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture)
    if check and r.returncode != 0:
        sys.exit(f"falhou: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip() if capture else ""


def git(repo, *args, check=True):
    return run(["git", "-C", repo, *args], check=check)


def audit(repo):
    """Todos os blobs de todas as branches, não só o HEAD."""
    bad = []
    objs = git(repo, "rev-list", "--objects", "--branches").splitlines()
    paths = {}
    for line in objs:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            paths[parts[0]] = parts[1]
    if not paths:
        return bad
    batch = subprocess.run(["git", "-C", repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                           input="\n".join(paths), text=True, capture_output=True).stdout.splitlines()
    for line in batch:
        oid, typ, size = line.split()
        if typ != "blob":
            continue
        p = paths[oid].replace("\\", "/")
        if BAD.search(p) or int(size) > MAX_BYTES:
            bad.append(f"{p} ({size} B)")
    return bad


def ensure_repo(owner, name, desc, dry):
    exists = subprocess.run([GH, "repo", "view", f"{owner}/{name}", "--json", "visibility", "-q", ".visibility"],
                            text=True, capture_output=True)
    if exists.returncode == 0:
        if exists.stdout.strip() != "PRIVATE":
            sys.exit(f"{owner}/{name} existe e NÃO é privado ({exists.stdout.strip()}); abortando")
        return
    if dry:
        print(f"[dry] criaria {owner}/{name} (privado)")
        return
    run([GH, "repo", "create", f"{owner}/{name}", "--private", "--description", desc])
    print(f"criado {owner}/{name} (privado)")


def set_remote(repo, url):
    remotes = git(repo, "remote").split()
    if "backup" in remotes:
        git(repo, "remote", "set-url", "backup", url)
    else:
        git(repo, "remote", "add", "backup", url)


def export_ps3recomp_patches():
    src = os.path.join(ROOT, "src", "ps3recomp")
    out = os.path.join(ROOT, "backup", "ps3recomp")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    branches = git(src, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
    n = 0
    for b in branches:
        if b in ("master", "main"):
            continue  # branches do upstream, sem mudanças nossas
        if subprocess.run(["git", "-C", src, "merge-base", "--is-ancestor", UPSTREAM_BASE, b]).returncode:
            continue  # branch que não parte do upstream usado (ex.: master antigo)
        d = os.path.join(out, b.replace("/", "__"))
        git(src, "format-patch", "-q", "--no-merges", f"{UPSTREAM_BASE}..{b}", "-o", d)
        with open(os.path.join(d, "BASE.txt"), "w", encoding="utf-8") as f:
            f.write(f"upstream: https://github.com/sp00nznet/ps3recomp @ {UPSTREAM_BASE}\n"
                    f"branch: {b} @ {git(src, 'rev-parse', b)}\n"
                    f"restaurar: git checkout -b {b} {UPSTREAM_BASE} && git am *.patch\n")
        n += len([x for x in os.listdir(d) if x.endswith(".patch")])
    print(f"ps3recomp: {n} patches em backup/ps3recomp/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    owner = run([GH, "api", "user", "-q", ".login"])
    print("conta GitHub:", owner)

    export_ps3recomp_patches()
    git(ROOT, "add", "backup")
    if git(ROOT, "status", "--porcelain", "backup"):
        git(ROOT, *GIT_ID, "commit", "-q", "-m", "backup: patches do ps3recomp (nossas mudancas sobre o upstream)",
            "-m", "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>", "--", "backup")

    targets = [(ROOT, "allstars-port", "Port nativo PSASBR: coordenação, docs, scripts (sem arquivos do jogo)"),
               (os.path.join(ROOT, "src", "allstars-ps3"), "allstars-ps3-port",
                "Fork local de ColinGamez/allstars-ps3 (sem arquivos do jogo)")]
    for repo, name, desc in targets:
        bad = audit(repo)
        if bad:
            sys.exit(f"ABORTADO: {repo} tem arquivos proibidos no histórico:\n  " + "\n  ".join(bad[:20]))
        print(f"auditoria ok: {os.path.relpath(repo, ROOT)}")
    for repo, name, desc in targets:
        ensure_repo(owner, name, desc, a.dry_run)
        set_remote(repo, f"https://github.com/{owner}/{name}.git")
        if a.dry_run:
            print(f"[dry] push --all de {os.path.relpath(repo, ROOT)} -> {owner}/{name}")
            continue
        helper = "!'" + GH.replace("\\", "/") + "' auth git-credential"
        run(["git", "-C", repo, "-c", "credential.helper=", "-c", f"credential.helper={helper}",
             "push", "backup", "--all"], capture=False)
        print(f"push ok: {owner}/{name}")


if __name__ == "__main__":
    main()
