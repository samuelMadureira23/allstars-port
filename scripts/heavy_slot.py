"""Fila de trabalho pesado: no maximo N (padrao 2) trabalhos pesados ao mesmo tempo no PC.

Pesado = build (scripts\\build.bat), lift/recompilacao (ppu_lifter, spu_lifter, relift), rodar o
jogo (scripts\\run.ps1), Ghidra headless e testes longos. Ler/editar codigo NAO entra na fila.

A fila e por ordem de chegada: quem pede primeiro pega a primeira vaga livre. Cada vaga e um
arquivo coord/locks/heavy/slot-<i>.lock criado de forma atomica (O_CREAT|O_EXCL).

Uso (o mais simples: "run" pega a vaga, roda o comando e devolve a vaga mesmo se falhar):
  python scripts/heavy_slot.py run claude --what "build Release" -- scripts\\build.bat Release claude
  python scripts/heavy_slot.py run claude --what "jogo 200s" -- powershell -ExecutionPolicy Bypass -File scripts\\run.ps1 -Agent claude -Seconds 200 -Tag claude-x
  python scripts/heavy_slot.py status                         # quem esta usando e quem esta na fila

Uso manual (para sessoes longas; renove ou a vaga expira):
  python scripts/heavy_slot.py acquire claude --what "relift PPU" [--ttl-min 120] [--no-wait]
  python scripts/heavy_slot.py renew   claude
  python scripts/heavy_slot.py release claude

Vaga esquecida: no modo "run" a vaga e renovada a cada 60 s e cai se o processo morrer ou se
passar 5 min sem renovacao; no modo manual cai quando passa o --ttl-min (padrao 120 min) sem renew.
Pedidos na fila que somem (processo morto) caem depois de 2 min. O usuario pode limpar com
"release <nome> --force" ou "release --slot <i> --force".
Variavel HEAVY_SLOTS muda o numero de vagas (padrao 2).
"""
import argparse
import datetime as dt
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "coord", "locks", "heavy")
QUEUE = os.path.join(DIR, "queue")
SLOTS = int(os.environ.get("HEAVY_SLOTS", "2"))
RUN_TTL_S = 5 * 60
HEARTBEAT_S = 60
TICKET_TTL_S = 120
POLL_S = 3


def now():
    return time.time()


def iso(t):
    return dt.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write(path, info):
    tmp = path + ".tmp-" + uuid.uuid4().hex[:6]
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def pid_alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def slot_path(i):
    return os.path.join(DIR, f"slot-{i}.lock")


def stale(info):
    if info is None:
        return True
    if info.get("host") == socket.gethostname() and info.get("watch_pid") and not pid_alive(info["watch_pid"]):
        return True
    return now() > info.get("expires", 0)


def clean():
    os.makedirs(QUEUE, exist_ok=True)
    for i in range(SLOTS):
        p = slot_path(i)
        if os.path.exists(p):
            info = read(p)
            if stale(info):
                try:
                    os.remove(p)
                    print(f"[heavy] vaga {i} liberada (esquecida/expirada): {info and info.get('agent')}", file=sys.stderr)
                except OSError:
                    pass
    for name in os.listdir(QUEUE):
        p = os.path.join(QUEUE, name)
        t = read(p)
        if t is None or (now() - t.get("heartbeat", 0) > TICKET_TTL_S) or \
                (t.get("host") == socket.gethostname() and not pid_alive(t.get("pid"))):
            try:
                os.remove(p)
            except OSError:
                pass


def tickets():
    out = []
    for name in sorted(os.listdir(QUEUE)):
        t = read(os.path.join(QUEUE, name))
        if t:
            out.append((name, t))
    return out


def free_slots():
    return [i for i in range(SLOTS) if not os.path.exists(slot_path(i))]


def try_take(i, info):
    try:
        fd = os.open(slot_path(i), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return True


def acquire(agent, what, ttl_s, wait=True, watch_pid=None):
    clean()
    tid = f"{now():017.6f}-{agent}-{uuid.uuid4().hex[:6]}.req"
    tpath = os.path.join(QUEUE, tid)
    ticket = {"agent": agent, "what": what, "pid": os.getpid(), "host": socket.gethostname(),
              "since": now(), "heartbeat": now()}
    write(tpath, ticket)
    announced = False
    try:
        while True:
            clean()
            ticket["heartbeat"] = now()
            write(tpath, ticket)
            free = free_slots()
            ahead = [n for n, _ in tickets() if n < tid]
            if free and len(ahead) < len(free):
                info = {"agent": agent, "what": what, "host": socket.gethostname(), "watch_pid": watch_pid,
                        "since": now(), "since_iso": iso(now()), "expires": now() + ttl_s}
                for i in free:
                    if try_take(i, info):
                        print(f"[heavy] {agent} pegou a vaga {i}: {what}", file=sys.stderr)
                        return i
            if not wait:
                print(f"[heavy] sem vaga agora ({SLOTS} ocupadas ou fila na frente)", file=sys.stderr)
                return None
            if not announced:
                print(f"[heavy] {agent} na fila ({len(ahead)} na frente); aguardando...", file=sys.stderr)
                announced = True
            time.sleep(POLL_S)
    finally:
        try:
            os.remove(tpath)
        except OSError:
            pass


def mine(agent, slot=None):
    out = []
    for i in range(SLOTS):
        info = read(slot_path(i))
        if info and (slot == i or (slot is None and info.get("agent") == agent)):
            out.append((i, info))
    return out


def cmd_status(_):
    clean()
    for i in range(SLOTS):
        info = read(slot_path(i))
        if info:
            left = int((info["expires"] - now()) / 60)
            print(f"vaga {i}: {info['agent']} -- {info['what']} (desde {info['since_iso']}, expira em {left} min)")
        else:
            print(f"vaga {i}: livre")
    q = tickets()
    if q:
        print("fila:")
        for n, t in q:
            print(f"  {t['agent']} -- {t['what']} (esperando desde {iso(t['since'])})")
    else:
        print("fila: vazia")


def cmd_acquire(a):
    i = acquire(a.agent, a.what, a.ttl_min * 60, wait=not a.no_wait)
    sys.exit(0 if i is not None else 1)


def cmd_renew(a):
    got = mine(a.agent)
    if not got:
        sys.exit(f"{a.agent} nao tem vaga")
    for i, info in got:
        info["expires"] = now() + a.ttl_min * 60
        write(slot_path(i), info)
        print(f"OK: vaga {i} renovada por {a.ttl_min} min")


def cmd_release(a):
    got = mine(a.agent, a.slot)
    if not got:
        sys.exit("nenhuma vaga para liberar")
    for i, info in got:
        if info.get("agent") != a.agent and not a.force:
            sys.exit(f"vaga {i} e de {info.get('agent')}; so o dono libera (ou o usuario com --force)")
        os.remove(slot_path(i))
        print(f"OK: vaga {i} liberada")


def cmd_run(a):
    cmd = a.command
    if not cmd:
        sys.exit("faltou o comando depois de --")
    i = acquire(a.agent, a.what or " ".join(cmd), RUN_TTL_S, watch_pid=os.getpid())
    stop = threading.Event()

    def beat():
        while not stop.wait(HEARTBEAT_S):
            info = read(slot_path(i))
            if info and info.get("watch_pid") == os.getpid():
                info["expires"] = now() + RUN_TTL_S
                write(slot_path(i), info)

    threading.Thread(target=beat, daemon=True).start()
    t0 = now()
    try:
        shell = os.name == "nt" and cmd[0].lower().endswith((".bat", ".cmd"))
        rc = subprocess.call(subprocess.list2cmdline(cmd) if shell else cmd, shell=shell, cwd=ROOT)
    finally:
        stop.set()
        info = read(slot_path(i))
        if info and info.get("watch_pid") == os.getpid():
            os.remove(slot_path(i))
        print(f"[heavy] vaga {i} devolvida ({int(now() - t0)} s)", file=sys.stderr)
    sys.exit(rc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    c = sub.add_parser("acquire"); c.add_argument("agent"); c.add_argument("--what", default="")
    c.add_argument("--ttl-min", type=int, default=120); c.add_argument("--no-wait", action="store_true")
    r = sub.add_parser("renew"); r.add_argument("agent"); r.add_argument("--ttl-min", type=int, default=120)
    l = sub.add_parser("release"); l.add_argument("agent", nargs="?", default="")
    l.add_argument("--slot", type=int); l.add_argument("--force", action="store_true")
    u = sub.add_parser("run"); u.add_argument("agent"); u.add_argument("--what", default="")
    argv = sys.argv[1:]
    command = []
    if "--" in argv:
        k = argv.index("--")
        argv, command = argv[:k], argv[k + 1:]
    a = ap.parse_args(argv)
    a.command = command
    {"status": cmd_status, "acquire": cmd_acquire, "renew": cmd_renew, "release": cmd_release,
     "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
