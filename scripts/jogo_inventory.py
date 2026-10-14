"""Inventário estático do jogo (frente 1): dump, PARAM.SFO, PKGs, ELF decriptado
(segmentos, seções, process_param, imports/NIDs, syscalls, módulos carregados via
cellSysmodule, imagens SPU embutidas). Só lê arquivos; grava metadados (nunca bytes
do jogo) em analysis/jogo/.

Uso: python scripts/jogo_inventory.py [--out analysis/jogo]
"""
import argparse
import collections
import hashlib
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.dirname(ROOT)
GAME = os.path.join(DOCS, "[Downloadgameps3.com]PLUS", "BCUS98472 - [Play Station All Stars Battle Royale]")
PKGS = os.path.join(DOCS, "[Downloadgameps3.com]PLUS")
RPCS3_UPD = os.path.join(DOCS, "rpcs3-v0.0.28-15372-38a5313e_win64", "dev_hdd0", "game", "BCUS98472")
ELFS = {
    "1.00": os.path.join(ROOT, "work", "eboot", "EBOOT_1.00_disc.elf"),
    "1.12": os.path.join(ROOT, "work", "eboot", "EBOOT_1.12_update.elf"),
}
SELFS = {
    "1.00": os.path.join(GAME, "PS3_GAME", "USRDIR", "EBOOT.BIN"),
    "1.12": os.path.join(RPCS3_UPD, "USRDIR", "EBOOT.BIN"),
}
PS3RECOMP = os.path.join(ROOT, "src", "ps3recomp")
sys.path.insert(0, os.path.join(PS3RECOMP, "tools"))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- PARAM.SFO
def parse_sfo(path):
    d = open(path, "rb").read()
    magic, ver, keyoff, dataoff, n = struct.unpack_from("<4sIIII", d, 0)
    assert magic == b"\0PSF", path
    out = {}
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from("<HHIII", d, 20 + i * 16)
        key = d[keyoff + ko:d.index(b"\0", keyoff + ko)].decode()
        raw = d[dataoff + do:dataoff + do + ln]
        if fmt == 0x0404:
            out[key] = struct.unpack("<I", raw)[0]
        else:
            out[key] = raw.rstrip(b"\0").decode("utf-8", "replace")
    out.pop("LICENSE", None)
    return out


# ---------------------------------------------------------------- PKG (cabeçalho em claro)
def parse_pkg(path):
    with open(path, "rb") as f:
        h = f.read(0x100)
        magic, rev, typ, moff, mcnt, msize, items, total, doff, dsize = struct.unpack_from(">IHHIIIIQQQ", h, 0)
        if magic != 0x7F504B47:
            return {"erro": "magic"}
        cid = h[0x30:0x60].rstrip(b"\0").decode()
        f.seek(moff)
        meta = {}
        for _ in range(mcnt):
            t, sz = struct.unpack(">II", f.read(8))
            meta[t] = f.read(sz)
    out = {"tamanho": os.path.getsize(path), "revision": hex(rev),
           "tipo": {1: "PS3", 2: "PSP"}.get(typ, typ), "content_id": cid, "itens": items}
    if 1 in meta:
        out["drm_type"] = {1: "Network", 2: "Local", 3: "Free", 0xD: "Free(PSP?)"}.get(
            struct.unpack(">I", meta[1])[0], struct.unpack(">I", meta[1])[0])
    if 2 in meta:
        ct = struct.unpack(">I", meta[2])[0]
        out["content_type"] = {4: "GameData", 5: "GameExec", 6: "PS1emu", 9: "Theme", 0xB: "Widget",
                               0xC: "License", 0xD: "VSH Module", 0xE: "PSN Avatar", 0x15: "Minis"}.get(ct, hex(ct))
    if 5 in meta and len(meta[5]) >= 4:
        _, pv = struct.unpack(">HH", meta[5][:4])
        out["package_version"] = "%02x.%02x" % (pv >> 8, pv & 0xFF)
    if 6 in meta and len(meta[6]) >= 4:
        out["meta6_hex"] = meta[6].hex()
    return out


# ---------------------------------------------------------------- SELF
def parse_self(path):
    d = open(path, "rb").read(0x400)
    magic, ver, flags, typ, metaoff, hdrlen, datalen = struct.unpack_from(">4sIHHIQQ", d, 0)
    # app_info: authid u64, vendor u32, self_type u32, version u64
    appoff = struct.unpack_from(">Q", d, 0x28 + 0x0)[0] if False else 0x70
    authid, vendor, stype, sver = struct.unpack_from(">QIIQ", d, appoff)
    return {"magic": magic.decode("latin1"), "criptografado": magic == b"SCE\0",
            "key_revision": flags, "self_type": stype, "auth_id": hex(authid),
            "app_version": "%x.%02x" % ((sver >> 48) & 0xFF, (sver >> 32) & 0xFF) if sver else hex(sver),
            "elf_len": datalen, "tamanho": os.path.getsize(path)}


# ---------------------------------------------------------------- ELF
class Elf:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        d = self.d
        assert d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 2
        (self.type, self.machine, _, self.entry, self.phoff, self.shoff, _, _, self.phentsize,
         self.phnum, self.shentsize, self.shnum, self.shstrndx) = struct.unpack_from(">HHIQQQIHHHHHH", d, 16)
        self.ph = [struct.unpack_from(">IIQQQQQQ", d, self.phoff + i * self.phentsize) for i in range(self.phnum)]
        self.sh = [struct.unpack_from(">IIQQQQIIQQ", d, self.shoff + i * self.shentsize) for i in range(self.shnum)]

    def va2off(self, va):
        for t, fl, off, vaddr, pa, fsz, msz, al in self.ph:
            if t == 1 and vaddr <= va < vaddr + fsz:
                return off + va - vaddr
        return None

    def u32(self, va):
        o = self.va2off(va)
        return None if o is None else struct.unpack_from(">I", self.d, o)[0]

    def cstr(self, va):
        o = self.va2off(va)
        return self.d[o:self.d.index(b"\0", o)].decode("latin1")

    def section_names(self):
        stro = self.sh[self.shstrndx][4] if self.shstrndx < self.shnum else None
        out = []
        for name, typ, flags, addr, off, size, link, info, al, es in self.sh:
            n = ""
            if stro is not None and name:
                e = self.d.find(b"\0", stro + name)
                n = self.d[stro + name:e].decode("latin1")
            out.append({"nome": n, "tipo": typ, "flags": hex(flags), "addr": hex(addr), "offset": hex(off),
                        "tamanho": size})
        return out


PT = {1: "LOAD", 7: "TLS", 0x60000001: "PROC_PARAM", 0x60000002: "PRX_PARAM"}


def elf_report(ver, path, db, implemented, sysnames, modnames):
    e = Elf(path)
    rep = {"arquivo": os.path.relpath(path, ROOT), "sha256": sha256(path), "tamanho": len(e.d),
           "machine": e.machine, "tipo": e.type}
    rep["segmentos"] = [{"tipo": PT.get(t, hex(t)), "flags": hex(fl), "offset": hex(off), "vaddr": hex(va),
                         "filesz": fsz, "memsz": msz} for t, fl, off, va, pa, fsz, msz, al in e.ph]
    rep["secoes"] = e.section_names()
    opd_func, opd_toc = e.u32(e.entry), e.u32(e.entry + 4)
    rep["entry"] = {"opd": hex(e.entry), "funcao": hex(opd_func), "toc_r2": hex(opd_toc)}
    for t, fl, off, va, pa, fsz, msz, al in e.ph:
        if t == 0x60000001:
            f = struct.unpack_from(">IIIIIIIII", e.d, off)
            rep["sys_process_param"] = {"magic": hex(f[1]), "version": hex(f[2]), "sdk_version": hex(f[3]),
                                        "primary_prio": f[4], "primary_stacksize": hex(f[5]),
                                        "malloc_pagesize": hex(f[6]), "ppc_seg": hex(f[7])}
        if t == 0x60000002:
            f = struct.unpack_from(">IIIIIIII", e.d, off)
            rep["sys_proc_prx_param"] = {"magic": hex(f[1]), "libent": [hex(f[4]), hex(f[5])],
                                         "libstub": [hex(f[6]), hex(f[7])]}
            libstub = (f[6], f[7])
            libent = (f[4], f[5])
        if t == 7:
            rep["tls"] = {"vaddr": hex(va), "filesz": fsz, "memsz": msz}

    # imports
    imports = []
    va = libstub[0]
    while va < libstub[1]:
        o = e.va2off(va)
        size = e.d[o]
        (ver_, attr, nfunc, nvar, ntls, ih, ith, _, name, nids, addrs, vnids, vstubs, _, _) = \
            struct.unpack_from(">HHHHHBBHIIIIIII", e.d, o + 2)
        lib = e.cstr(name)
        funcs = []
        for i in range(nfunc):
            nid = e.u32(nids + 4 * i)
            hit = db.lookup_nid(nid)
            funcs.append({"nid": "0x%08x" % nid, "nome": hit[1] if hit else None,
                          "slot": hex(addrs + 4 * i), "stub": hex(e.u32(addrs + 4 * i)), "hle": nid in implemented})
        vars_ = ["0x%08x" % e.u32(vnids + 4 * i) for i in range(nvar)]
        imports.append({"biblioteca": lib, "funcoes": funcs, "variaveis": vars_})
        va += size
    rep["imports"] = imports
    # exports
    exports = []
    va = libent[0]
    while va < libent[1]:
        o = e.va2off(va)
        size = e.d[o]
        _, attr, nfunc, nvar, ntls, ih, ith, _, name, nids, addrs = struct.unpack_from(">HHHHHBBHIII", e.d, o + 2)
        exports.append({"nome": e.cstr(name) if name else "(sem nome / módulo principal)",
                        "funcoes": nfunc, "variaveis": nvar})
        va += size
    rep["exports"] = exports

    # syscalls (sc precedido de li r11,N) e chamadas a cellSysmoduleLoadModule (li r3,N)
    text = [(off, va, fsz) for t, fl, off, va, pa, fsz, msz, al in e.ph if t == 1 and fl & 1]
    sys_hits = collections.defaultdict(list)
    sc_unknown = 0
    stub_of = {}
    for lib in imports:
        for fn in lib["funcoes"]:
            stub_of[int(fn["slot"], 16)] = (lib["biblioteca"], fn["nome"] or fn["nid"])
    # stubs: cada stub de import é um trecho de código que carrega o ponteiro de stub_of[addr]
    # localiza as funções-stub (call sites fazem bl para o código do stub, não para a tabela)
    stub_code = {}
    for off, va0, fsz in text:
        words = struct.unpack_from(">%dI" % (fsz // 4), e.d, off)
        for i, w in enumerate(words):
            # padrão do stub: li r12,0 ; oris r12,r12,hi ; lwz r12,lo(r12)  (ver ppu_loader)
            if (w & 0xFFFF0000) == 0x3D800000 or (w & 0xFFFF0000) == 0x658C0000:
                if i + 1 < len(words) and (words[i + 1] & 0xFFFF0000) == 0x818C0000:
                    hi = w & 0xFFFF
                    lo = words[i + 1] & 0xFFFF
                    tgt = ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF
                    if tgt in stub_of:
                        start = va0 + 4 * i
                        if i > 0 and words[i - 1] == 0x39800000:
                            start -= 4
                        stub_code[start] = stub_of[tgt]
        for i, w in enumerate(words):
            if w == 0x44000002:
                n = None
                for j in range(i - 1, max(-1, i - 24), -1):
                    if (words[j] & 0xFFFF0000) == 0x39600000:
                        n = words[j] & 0xFFFF
                        break
                if n is None:
                    sc_unknown += 1
                else:
                    sys_hits[n].append(va0 + 4 * i)
    rep["syscalls"] = [{"numero": n, "nome": sysnames.get(n), "ocorrencias": len(v),
                        "exemplos": [hex(x) for x in v[:4]]} for n, v in sorted(sys_hits.items())]
    rep["syscalls_sem_numero_resolvido"] = sc_unknown

    load_mod = [a for a, (lib, nm) in stub_code.items() if nm in ("cellSysmoduleLoadModule",)]
    mods = collections.Counter()
    for off, va0, fsz in text:
        words = struct.unpack_from(">%dI" % (fsz // 4), e.d, off)
        for i, w in enumerate(words):
            if (w & 0xFC000003) == 0x48000001:  # bl
                disp = w & 0x03FFFFFC
                if disp & 0x02000000:
                    disp -= 0x04000000
                tgt = va0 + 4 * i + disp
                if tgt in load_mod:
                    for j in range(i - 1, max(-1, i - 12), -1):
                        if (words[j] & 0xFFFF0000) == 0x38600000:
                            mods[words[j] & 0xFFFF] += 1
                            break
                    else:
                        mods["?"] += 1
    rep["cellSysmoduleLoadModule"] = {"stubs": [hex(a) for a in load_mod],
                                      "modulos": [{"id": hex(k) if k != "?" else "?",
                                                   "nome": modnames.get(k), "chamadas": c}
                                                  for k, c in sorted(mods.items(), key=lambda x: str(x[0]))]}

    # imagens SPU embutidas (ELF com e_machine 23)
    spu = []
    pos = 0
    while True:
        pos = e.d.find(b"\x7fELF\x01\x02\x01", pos + 1)
        if pos < 0:
            break
        mach, = struct.unpack_from(">H", e.d, pos + 18)
        if mach != 23:
            continue
        (etype, _, _, entry, phoff, shoff, _, _, phes, phn, shes, shn, _) = struct.unpack_from(">HHIIIIIHHHHHH", e.d, pos + 16)
        end = shoff + shn * shes if shn else 0
        segs = []
        for i in range(phn):
            pt, po, pv, ppa, pfs, pms, pfl, pal = struct.unpack_from(">IIIIIIII", e.d, pos + phoff + i * phes)
            end = max(end, po + pfs)
            segs.append({"tipo": pt, "ls_addr": hex(pv), "filesz": pfs, "memsz": pms, "flags": pfl})
        vaddr = None
        for t, fl, off, va0, pa, fsz, msz, al in e.ph:
            if t == 1 and off <= pos < off + fsz:
                vaddr = va0 + pos - off
        blob = e.d[pos:pos + end]
        spu.append({"offset_arquivo": hex(pos), "vaddr": hex(vaddr) if vaddr else None, "tamanho": end,
                    "entry_ls": hex(entry), "segmentos": segs, "sha256": hashlib.sha256(blob).hexdigest()})
    rep["imagens_spu_elf"] = spu
    return rep


def load_sysnames():
    names = {}
    p = os.path.join(PS3RECOMP, "runtime", "syscalls", "lv2_syscall_table.h")
    for m in re.finditer(r"#define\s+SYS_(\w+)\s+(\d+)", open(p, encoding="utf-8", errors="replace").read()):
        names.setdefault(int(m.group(2)), "sys_" + m.group(1).lower())
    return names


def load_modnames():
    names = {}
    p = os.path.join(PS3RECOMP, "libs", "system", "cellSysmodule.h")
    for m in re.finditer(r"#define\s+CELL_SYSMODULE_(\w+)\s+(0x[0-9A-Fa-f]+)", open(p, encoding="utf-8").read()):
        names.setdefault(int(m.group(2), 16), m.group(1))
    return names


def dump_inventory():
    ext = collections.Counter()
    size = collections.Counter()
    total = 0
    for dp, dn, fn in os.walk(GAME):
        for f in fn:
            p = os.path.join(dp, f)
            e = os.path.splitext(f)[1].lower() or "(sem ext)"
            s = os.path.getsize(p)
            ext[e] += 1
            size[e] += s
            total += s
    magic = {}
    for rel in ["PS3_GAME/USRDIR/movies/attract.pam", "PS3_GAME/SND0.AT3", "PS3_GAME/TROPDIR/NPWR02621_00/TROPHY.TRP",
                "PS3_GAME/PS3LOGO.DAT", "PS3_GAME/LICDIR/LIC.DAT", "PS3_DISC.SFB"]:
        p = os.path.join(GAME, rel)
        if os.path.exists(p):
            magic[rel] = open(p, "rb").read(16).hex()
    for sub in ["PS3_GAME/USRDIR/sound", "PS3_GAME/USRDIR/music"]:
        for dp, dn, fn in os.walk(os.path.join(GAME, sub)):
            if fn:
                magic[os.path.relpath(os.path.join(dp, fn[0]), GAME).replace("\\", "/")] = \
                    open(os.path.join(dp, fn[0]), "rb").read(16).hex()
                break
    return {"pasta": GAME, "arquivos": sum(ext.values()), "bytes": total,
            "por_extensao": {k: {"arquivos": ext[k], "bytes": size[k]} for k in sorted(ext)},
            "magics": magic}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis", "jogo"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    from nid_database import get_default_db, NIDDatabase
    db = get_default_db()
    impl = NIDDatabase()
    impl.load_implemented(PS3RECOMP)
    implemented = {nid for nid, _, _ in impl.all_entries()}
    sysnames, modnames = load_sysnames(), load_modnames()

    inv = {"dump": dump_inventory(),
           "param_sfo": {"disco PS3_GAME": parse_sfo(os.path.join(GAME, "PS3_GAME", "PARAM.SFO")),
                         "disco PKGDIR": parse_sfo(os.path.join(GAME, "PS3_GAME", "PKGDIR", "PARAM.SFO")),
                         "disco PKGDIR/PKG00": parse_sfo(os.path.join(GAME, "PS3_GAME", "PKGDIR", "PKG00", "PARAM.SFO")),
                         "RPCS3 dev_hdd0 (update instalado)": parse_sfo(os.path.join(RPCS3_UPD, "PARAM.SFO"))},
           "pkgs": {}, "selfs": {}}
    for f in sorted(os.listdir(PKGS)):
        if f.lower().endswith(".pkg"):
            inv["pkgs"][f] = parse_pkg(os.path.join(PKGS, f))
    inv["pkgs"]["PS3_GAME/PKGDIR/PKG00/INSTALL.PKG"] = parse_pkg(os.path.join(GAME, "PS3_GAME", "PKGDIR", "PKG00", "INSTALL.PKG"))
    rp = os.path.join(RPCS3_UPD, "USRDIR")
    inv["rpcs3_update_usrdir"] = sorted(os.listdir(rp))
    for v, p in SELFS.items():
        inv["selfs"][v] = parse_self(p) | {"sha256": sha256(p)}
    json.dump(inv, open(os.path.join(a.out, "inventario.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    for v, p in ELFS.items():
        rep = elf_report(v, p, db, implemented, sysnames, modnames)
        json.dump(rep, open(os.path.join(a.out, "elf_%s.json" % v), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        nimp = sum(len(l["funcoes"]) for l in rep["imports"])
        print(v, "imports", nimp, "libs", len(rep["imports"]), "syscalls", len(rep["syscalls"]),
              "spu", len(rep["imagens_spu_elf"]), "mods", len(rep["cellSysmoduleLoadModule"]["modulos"]))


if __name__ == "__main__":
    main()
