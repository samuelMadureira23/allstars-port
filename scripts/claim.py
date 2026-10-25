"""Travas de tarefa para coordenar varios agentes na mesma pasta.

Uma trava e um arquivo coord/locks/<TAREFA>.lock criado de forma atomica
(O_CREAT|O_EXCL): se dois agentes tentarem pegar a mesma tarefa ao mesmo tempo,
so um consegue. A trava registra dono, horario, branch e os caminhos que o dono
vai alterar -- outro agente nao deve escrever nesses caminhos enquanto ela existir.

Uso:
  python scripts/claim.py list
  python scripts/claim.py claim   T-004 astra --paths tools/psarc_extract.py docs/PSARC.md --note "extrator psarc"
  python scripts/claim.py renew   T-004 astra --note "parte 2"
  python scripts/claim.py release T-004 astra
  python scripts/claim.py check   tools/psarc_extract.py      # quem esta mexendo neste caminho?

Tarefas especiais:
  INTEGRATION  -> obrigatoria antes de fazer merge em src/ (branch allstars-port)
  LIFT         -> obrigatoria antes de regenerar work/recompiled_1.00 ou work/spu/lifted
"""
import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCKS = os.path.join(ROOT, "coord", "locks")
STALE_HOURS = 24


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def lock_path(task):
    if not task.replace("-", "").replace("_", "").isalnum():
        sys.exit(f"nome de tarefa invalido: {task}")
    return os.path.join(LOCKS, f"{task}.lock")


def read_lock(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def all_locks():
    os.makedirs(LOCKS, exist_ok=True)
    for name in sorted(os.listdir(LOCKS)):
        if name.endswith(".lock"):
            p = os.path.join(LOCKS, name)
            try:
                yield p, read_lock(p)
            except (OSError, ValueError):
                yield p, {"task": name[:-5], "agent": "?", "corrupt": True}


def age_hours(info):
    try:
        t = dt.datetime.fromisoformat(info.get("renewed") or info["claimed"])
        return (dt.datetime.now().astimezone() - t).total_seconds() / 3600
    except (KeyError, ValueError):
        return 0.0


def norm(p):
    return os.path.normcase(os.path.normpath(p)).replace("\\", "/").rstrip("/")


def cmd_list(_):
    any_ = False
    for _, info in all_locks():
        any_ = True
        stale = "  [ANTIGA: >%dh sem renovar]" % STALE_HOURS if age_hours(info) > STALE_HOURS else ""
        print(f"{info.get('task')}: {info.get('agent')} desde {info.get('claimed')}{stale}")
        if info.get("paths"):
            print("    caminhos:", ", ".join(info["paths"]))
        if info.get("note"):
            print("    nota:", info["note"])
    if not any_:
        print("(nenhuma tarefa travada)")


def cmd_claim(a):
    os.makedirs(LOCKS, exist_ok=True)
    path = lock_path(a.task)
    mine = [norm(p) for p in a.paths]
    for _, info in all_locks():
        if info.get("agent") == a.agent:
            continue
        for theirs in info.get("paths", []):
            t = norm(theirs)
            for m in mine:
                if m == t or m.startswith(t + "/") or t.startswith(m + "/"):
                    sys.exit(f"CONFLITO: '{m}' sobrepoe '{t}' travado por {info['agent']} em {info['task']}")
    info = {"task": a.task, "agent": a.agent, "claimed": now(), "paths": a.paths, "note": a.note}
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        other = read_lock(path)
        sys.exit(f"JA TRAVADA por {other.get('agent')} desde {other.get('claimed')} -- escolha outra tarefa")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"OK: {a.task} travada para {a.agent}")


def own(a):
    path = lock_path(a.task)
    if not os.path.exists(path):
        sys.exit(f"{a.task} nao esta travada")
    info = read_lock(path)
    if info.get("agent") != a.agent and not a.force:
        sys.exit(f"{a.task} pertence a {info.get('agent')}; so o dono libera (ou o usuario com --force)")
    return path, info


def cmd_renew(a):
    path, info = own(a)
    info["renewed"] = now()
    if a.note:
        info["note"] = a.note
    with open(path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"OK: {a.task} renovada")


def cmd_release(a):
    path, _ = own(a)
    os.remove(path)
    print(f"OK: {a.task} liberada")


def cmd_check(a):
    target = norm(a.path)
    hit = False
    for _, info in all_locks():
        for theirs in info.get("paths", []):
            t = norm(theirs)
            if target == t or target.startswith(t + "/") or t.startswith(target + "/"):
                print(f"{a.path}: travado por {info['agent']} ({info['task']})")
                hit = True
    if not hit:
        print(f"{a.path}: livre")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("claim"); c.add_argument("task"); c.add_argument("agent")
    c.add_argument("--paths", nargs="*", default=[]); c.add_argument("--note", default="")
    r = sub.add_parser("renew"); r.add_argument("task"); r.add_argument("agent")
    r.add_argument("--note", default=""); r.add_argument("--force", action="store_true")
    l = sub.add_parser("release"); l.add_argument("task"); l.add_argument("agent")
    l.add_argument("--force", action="store_true")
    k = sub.add_parser("check"); k.add_argument("path")
    a = ap.parse_args()
    {"list": cmd_list, "claim": cmd_claim, "renew": cmd_renew, "release": cmd_release, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
