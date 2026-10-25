"""Nucleo do launcher do port (T-257 = T-241 kit 'traga seu jogo' + T-256 opcoes de PC).

Sem interface aqui: so verificacoes, configuracao e montagem dos comandos, para os testes rodarem sem jogo e sem tkinter.
Nada do jogo e embutido: so os SHA-256 de referencia (impressoes digitais, nao o conteudo).
"""
import configparser
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # pasta do port (a do Abrir Launcher.bat)
REF_FILE = Path(__file__).resolve().parent / "referencia.json"
PIPELINE_FILE = Path(__file__).resolve().parent / "kit_pipeline.json"
SETTINGS_FILE = ROOT / "port_settings.ini"
ELF_DEST = ROOT / "work" / "eboot" / "EBOOT_1.00_disc.elf"
# T-300 (Samuel 21/10: versao publica com o 1.12 + DLC): o update do PROPRIO usuario (pasta dev_hdd0/game/BCUS98472 do
# RPCS3, com o PARAM.SFO 01.12, o EBOOT.BIN do update, os .psarc do patch/DLC e os .edat de direito). O disco 1.00
# continua sendo a base (/dev_bdvd); o update entra por PORT_UPDATE_DIR e o exe do 1.12 e um build separado.
ELF112_DEST = ROOT / "work" / "eboot" / "EBOOT_1.12_update.elf"
BUILD112_DIRS = ("build-samuel-v112", "build-v112")
USER_DIR = ROOT / "user"            # como no port do GoW3: saves, cache e logs do usuario (manter ao atualizar)
STATE_FILE = USER_DIR / "launcher.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def reference():
    return load_json(REF_FILE)


# ---------------------------------------------------------------- aba (a): preparar com o seu jogo

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def parse_sfo(path):
    """Le um PARAM.SFO do PS3 e devolve {chave: valor} (texto ou inteiro)."""
    data = Path(path).read_bytes()
    if len(data) < 20 or data[:4] != b"\x00PSF":
        raise ValueError("nao e um PARAM.SFO (assinatura \\0PSF ausente)")
    _ver, key_start, data_start, count = struct.unpack_from("<IIII", data, 4)
    out = {}
    for i in range(count):
        key_off, fmt, length, _max_len, data_off = struct.unpack_from("<HHIII", data, 20 + 16 * i)
        k0 = key_start + key_off
        key = data[k0:data.index(b"\x00", k0)].decode("ascii", "replace")
        raw = data[data_start + data_off:data_start + data_off + length]
        if fmt == 0x0404:
            out[key] = struct.unpack("<I", raw[:4])[0]
        else:
            out[key] = raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
    return out


def find_game_files(game_dir):
    """Aceita a pasta do jogo (com PS3_GAME) ou a propria PS3_GAME. Devolve (sfo, eboot) ou levanta erro claro."""
    g = Path(game_dir)
    base = g / "PS3_GAME" if (g / "PS3_GAME").is_dir() else g
    sfo, eboot = base / "PARAM.SFO", base / "USRDIR" / "EBOOT.BIN"
    if not sfo.is_file():
        raise FileNotFoundError(f"nao achei PARAM.SFO em {base}")
    if not eboot.is_file():
        raise FileNotFoundError(f"nao achei USRDIR\\EBOOT.BIN em {base}")
    return sfo, eboot


def game_art(game_dir):
    """Arte do launcher (T-267) lida do JOGO DO USUARIO, na hora: nada disso vem no pacote (AGENTS.md secao 8).
    {'icon': ICON0.PNG (logo 320x176), 'roster': PIC0.PNG (elenco, com transparencia), 'bg': PIC1.PNG (fundo 1920x1080)};
    so as que existirem. Sem pasta valida = {} e o launcher usa o visual neutro."""
    if not game_dir:
        return {}
    g = Path(game_dir)
    base = g / "PS3_GAME" if (g / "PS3_GAME").is_dir() else g
    names = {"icon": "ICON0.PNG", "roster": "PIC0.PNG", "bg": "PIC1.PNG"}
    return {k: base / n for k, n in names.items() if (base / n).is_file()}


def check_game(game_dir, ref=None, hasher=sha256_file):
    """Confere titulo e versao (PARAM.SFO) e o SHA do EBOOT.BIN contra o disco BCUS98472 1.00. Devolve (ok, linhas)."""
    ref = ref or reference()
    lines, ok = [], True
    try:
        sfo, eboot = find_game_files(game_dir)
    except FileNotFoundError as e:
        return False, [f"ERRO: {e}"]
    try:
        info = parse_sfo(sfo)
    except ValueError as e:
        return False, [f"ERRO: {e}"]
    title_id, ver = info.get("TITLE_ID", "?"), info.get("APP_VER", info.get("VERSION", "?"))
    lines.append(f"Jogo: {info.get('TITLE', '?')}  |  codigo {title_id}  |  versao {ver}")
    if title_id != ref["title_id"]:
        ok = False
        lines.append(f"ERRO: o codigo e {title_id}; este port e do {ref['title_id']} (disco americano).")
    sha = hasher(eboot)
    if sha == ref["eboot_sha256"]:
        lines.append("OK: EBOOT.BIN igual ao do disco 1.00 usado no port.")
    else:
        ok = False
        lines.append(f"ERRO: EBOOT.BIN diferente do disco 1.00 (SHA {sha[:16]}...). Escolha a pasta do DISCO "
                     "(o update 1.12 + DLC entra separado, nos botoes 7 e 8 da aba Preparar).")
    return ok, lines


def default_elf_for(game_dir):
    """Onde o RPCS3 costuma gravar o EBOOT decriptado (mesma pasta, extensao .elf)."""
    try:
        _sfo, eboot = find_game_files(game_dir)
    except FileNotFoundError:
        return None
    for cand in (eboot.with_suffix(".elf"), eboot.with_name("EBOOT.elf")):
        if cand.is_file():
            return cand
    return None


def check_update(update_dir, ref=None):
    """Confere a pasta do update 1.12 (+ DLC) do usuario: PARAM.SFO do titulo certo na versao 01.12 e USRDIR/EBOOT.BIN.
    Lista o conteudo de DLC achado (so para informar; o jogo testa cada direito pelo .edat). Devolve (ok, linhas)."""
    ref = ref or reference()
    d = Path(update_dir or "")
    sfo, usr = d / "PARAM.SFO", d / "USRDIR"
    if not update_dir or not sfo.is_file() or not (usr / "EBOOT.BIN").is_file():
        return False, ["ERRO: escolha a pasta do update (no RPCS3: dev_hdd0/game/BCUS98472, com PARAM.SFO e USRDIR/EBOOT.BIN)."]
    try:
        info = parse_sfo(sfo)
    except ValueError as e:
        return False, [f"ERRO: {e}"]
    tid, ver = info.get("TITLE_ID", "?"), info.get("APP_VER", "?")
    lines = [f"Update: codigo {tid}  |  versao {ver}"]
    if tid != ref["title_id"]:
        return False, lines + [f"ERRO: o update e do {tid}; este port e do {ref['title_id']}."]
    want = ref.get("update_app_ver", "01.12")
    if ver != want:
        return False, lines + [f"ERRO: versao {ver}; o port suporta o update {want}."]
    names = {p.name.lower() for p in usr.iterdir() if p.is_file()}
    fighters = sorted(n for n in names if n.endswith("_char_setup.psarc"))
    stages = sorted(n for n in ("heavenlysword.psarc", "medievil.psarc") if n in names)
    edats = sum(1 for n in names if n.endswith(".edat"))
    lines.append(f"OK: update {want} conferido.")
    lines.append(f"DLC achado: {len(fighters)} lutador(es), {len(stages)} fase(s), {edats} arquivo(s) de direito (.edat).")
    return True, lines


def default_elf112_for(update_dir):
    """Onde o RPCS3 grava o EBOOT do update decriptado (USRDIR/EBOOT.elf)."""
    if not update_dir:
        return None
    usr = Path(update_dir) / "USRDIR"
    for cand in (usr / "EBOOT.elf", usr / "EBOOT.ELF"):
        if cand.is_file():
            return cand
    return None


def check_and_copy_elf(elf_path, ref=None, hasher=sha256_file, dest=ELF_DEST, key="elf_sha256"):
    """Confere o .elf decriptado (key = elf_sha256 do disco 1.00 ou elf112_sha256 do update) e copia para work/eboot."""
    ref = ref or reference()
    if not elf_path or not Path(elf_path).is_file():
        return False, ["ERRO: escolha o EBOOT decriptado (.elf) que o RPCS3 gerou."]
    sha = hasher(elf_path)
    if sha != ref[key]:
        which = "do update 1.12 (USRDIR/EBOOT.BIN da pasta do update)" if key == "elf112_sha256" else "do disco 1.00"
        return False, [f"ERRO: o .elf nao e o esperado (SHA {sha[:16]}...). Decripte o EBOOT.BIN {which} de novo."]
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(elf_path, dest)
    return True, [f"OK: ELF conferido e copiado para {Path(dest).relative_to(ROOT) if ROOT in Path(dest).parents else dest}."]


DECRYPT_GUIDE = (
    "Como decriptar o EBOOT com o SEU RPCS3 (o port nao faz isso por voce):\n"
    "  1. Abra o RPCS3 (com o firmware do PS3 instalado nele).\n"
    "  2. Menu Utilities > Decrypt PS3 Binaries.\n"
    "  3. Escolha o EBOOT.BIN da pasta do jogo (PS3_GAME\\USRDIR\\EBOOT.BIN).\n"
    "  4. O RPCS3 grava o EBOOT.elf na mesma pasta. Volte aqui e clique em 'Conferir ELF'."
)


def check_tools(env=None, which=shutil.which, exists=os.path.exists):
    """O que o build precisa no PC (so verifica; nao instala nada). Devolve lista de (nome, ok, dica)."""
    env = env or os.environ
    local = env.get("LOCALAPPDATA", "")
    vc = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    res = [
        ("Python 3", True, "ja esta rodando este launcher"),
        ("Visual Studio Build Tools (C++ x64)", exists(vc), "instale 'Build Tools for Visual Studio' com 'Desenvolvimento para desktop com C++'"),
        ("LLVM (clang-cl)", bool(which("clang-cl")) or exists(r"C:\Program Files\LLVM\bin\clang-cl.exe"), "instale o LLVM para Windows"),
        ("CMake", bool(which("cmake")) or exists(r"C:\Program Files\CMake\bin\cmake.exe"), "instale o CMake"),
        ("Ninja", bool(which("ninja")) or exists(os.path.join(local, r"Microsoft\WinGet\Links\ninja.exe")), "instale o Ninja"),
    ]
    return res


def pipeline_steps(path=PIPELINE_FILE, versions=("100",)):
    """Passos de geracao/compilacao (lift PPU, lift SPU, build). Os ainda sem comando ficam como 'pendente'.
    versions: '100' (disco) e, com o ELF do update conferido, '112' (os passos do 1.12 vem depois e reaproveitam o 1.00)."""
    return [s for s in load_json(path)["steps"] if s.get("versao", "100") in versions]


def pipeline_versions(root=ROOT):
    """Versoes a gerar: o 1.00 sempre; o 1.12 quando o ELF do update ja foi conferido (work/eboot/EBOOT_1.12_update.elf)."""
    return ("100", "112") if (Path(root) / "work" / "eboot" / ELF112_DEST.name).is_file() else ("100",)


def step_command(step, root=ROOT):
    """Comando de um passo com {root} trocado; None se o passo ainda esta pendente."""
    cmd = step.get("cmd")
    if not cmd or step.get("pendente"):
        return None
    return [c.replace("{root}", str(root)).replace("{py}", sys.executable) for c in cmd]


def step_env(step, game_dir, base=None, root=ROOT):
    """Ambiente de um passo: o do processo + o 'env' do passo com {game} = pasta do jogo do usuario. O build usa
    PORT_ICON_PNG = <jogo>\\PS3_GAME\\ICON0.PNG (icone do PSASBR.exe vindo do disco DELE; sem ele o SHA muda)."""
    env = dict(os.environ if base is None else base)
    # sem UTF-8 o lifter grava os comentarios com travessao em cp1252 e o lift sai diferente do de referencia (T-300)
    env.setdefault("PYTHONUTF8", "1")
    for k, v in (step.get("env") or {}).items():
        env[k] = v.replace("{game}", str(game_dir or "")).replace("{root}", str(root))
    return env


def check_exe(exe_path, ref=None, hasher=sha256_file):
    ref = ref or reference()
    if not Path(exe_path).is_file():
        return False, [f"ERRO: nao achei {exe_path} (o build terminou?)"]
    sha = hasher(exe_path)
    if not ref.get("exe_reprodutivel", True):
        return True, [f"INFO: exe gerado (SHA {sha[:16]}...). A versao de referencia ainda nao e "
                      "reprodutivel, entao o SHA nao pode ser comparado nesta versao do kit."]
    if sha == ref["exe_sha256"]:
        return True, [f"OK: o seu {Path(exe_path).name} e IGUAL ao de referencia."]
    return False, [f"AVISO: o exe saiu diferente do de referencia (SHA {sha[:16]}... x {ref['exe_sha256'][:16]}...). "
                   "Pode funcionar, mas a partida LAN entre versoes diferentes nao e garantida. Mande o log para quem te passou o jogo."]


# ---------------------------------------------------------------- aba (b): opcoes de PC

# idioma do sistema do PS3 (CELL_SYSUTIL_LANG_*, libs/system/cellSysutil.h; claude-int #4538: 2 = frances, 3 = espanhol).
# Sem a chave o port usa 1 (ingles EUA). Disco 1.00 (claude-int #4597): ingles, espanhol e frances; o texto em portugues
# vem com o conteudo do update 1.12 (o RPCS3 do Samuel, que tem o 1.12, mostra PT-BR); no 1.00 o PT-BR cai no ingles.
GAME_LANGS = {"Inglês (EUA)": "1", "Espanhol": "3", "Francês": "2",
              "Português (Brasil) — só com o update 1.12": "17"}

# chave do ini -> (rotulo, valores possiveis, padrao, variavel que o port ja le hoje ou None = 'em breve')
SETTINGS = [
    # Graficos (docs/OPCOES_PC.md + coordenador #4387). Sem limite de fps (coordenador 20/10): a logica e por quadro; 120 aceleraria e 30 deixaria a luta em camera lenta.
    ("video", "resolucao_interna", "Resolução interna", ["720p (1x)", "1440p (2x)", "4K (3x)", "1080p (1,5x)"], "720p (1x)", "RSX_RES_SCALE"),
    ("video", "modo_janela", "Janela / sem borda / tela cheia", ["janela", "sem_borda", "tela_cheia"], "janela", "PORT_WINDOW"),
    ("video", "vsync", "VSync", ["0", "1"], "0", "RSX_VSYNC"),
    # na_tela = overlay de fps/frametime do claude-gpu (T-260, F9 alterna no jogo); o titulo da janela sempre mostra o fps
    # overlay do claude-gpu (#4749): RSX_OVERLAY=1 so fps | 2 fps + grafico | 3 completo; RSX_OVERLAY_POS = canto
    ("video", "mostrar_fps", "Mostrar fps", ["titulo", "so_fps", "fps_grafico", "completo"], "titulo", "RSX_OVERLAY"),
    ("video", "posicao_fps", "Canto do fps na tela", ["tl", "tr", "bl", "br"], "tl", "RSX_OVERLAY_POS"),
    ("video", "anisotropia", "Filtro anisotrópico", ["desligado", "4x", "8x", "16x"], "desligado", "RSX_ANISO"),
    ("video", "antisserrilhado", "Antisserrilhado", ["desligado", "FXAA"], "desligado", "RSX_FXAA"),
    ("video", "nitidez", "Nitidez", ["0", "25", "50", "75", "100"], "0", "RSX_SHARPEN"),     # CAS em %
    # Controles / audio / sistema
    # tipo de controle (claude-int T-273): auto = DS4/DualSense por HID primeiro, Xbox/XInput nas portas que sobrarem
    ("controles", "tipo", "Tipo de controle", ["auto", "ds4", "ds5", "xbox"], "auto", "PAD_TYPE"),
    ("controles", "keymap", "Arquivo de teclas (teclado)", None, "", "PAD_KEYMAP_FILE"),
    ("audio", "som", "Som", ["ligado", "mudo"], "ligado", "PORT_AUDIO_MUTE"),
    ("audio", "volume", "Volume (%)", ["100", "75", "50", "25"], "100", "PORT_AUDIO_VOLUME"),   # claude-int #4709
    ("idioma", "jogo", "Idioma do jogo (texto + dublagem)", list(GAME_LANGS), "Inglês (EUA)", "PS3_SYSTEM_LANG"),
    # nick do online (pedido do Samuel 20/10): o runtime le PS3_NP_ONLINE_ID (np_psnr.c); sala e IP ficam no menu F3
    ("online", "nick", "Nick (seu nome no online)", None, "", "PS3_NP_ONLINE_ID"),
]


def valid_nick(nick):
    """Mesma regra do runtime (np_psnr.c clean_online_id): 3 a 16 letras, digitos, - ou _, comecando por letra."""
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,15}", nick or ""))

# nome legivel de cada valor na tela (o ini guarda o valor interno; T-267). O que nao estiver aqui aparece como esta.
OPT_LABELS = {
    ("video", "modo_janela"): {"janela": "Janela", "sem_borda": "Sem borda", "tela_cheia": "Tela cheia"},
    ("video", "vsync"): {"0": "Desligado", "1": "Ligado"},
    ("video", "mostrar_fps"): {"titulo": "Só no título da janela", "so_fps": "Na tela: só fps",
                               "fps_grafico": "Na tela: fps + gráfico", "completo": "Na tela: completo"},
    ("video", "posicao_fps"): {"tl": "Superior esquerdo", "tr": "Superior direito", "bl": "Inferior esquerdo",
                               "br": "Inferior direito"},
    ("video", "anisotropia"): {"desligado": "Desligado"},
    ("video", "antisserrilhado"): {"desligado": "Desligado"},
    ("video", "nitidez"): {"0": "Desligada"},
    ("audio", "som"): {"ligado": "Ligado", "mudo": "Mudo"},
    ("controles", "tipo"): {"auto": "Automático", "ds4": "DualShock 4", "ds5": "DualSense (PS5)", "xbox": "Xbox / XInput"},
}


def display_value(sec, key, value, t=lambda s: s):
    return t(OPT_LABELS.get((sec, key), {}).get(value, value))


def stored_value(sec, key, label, t=lambda s: s):
    for v, lbl in OPT_LABELS.get((sec, key), {}).items():
        if label in (lbl, t(lbl)):
            return v
    return label


# o RSX_RES_SCALE do port e inteiro (1..4): 1080p (1,5x) fica 'em breve' ate o runtime aceitar fracao
RES_SCALE = {"720p (1x)": None, "1440p (2x)": "2", "4K (3x)": "3", "1080p (1,5x)": None}


# valores do ini de versoes anteriores -> atuais (o 'na_tela' de antes era o painel completo)
LEGACY = {("video", "mostrar_fps"): {"na_tela": "completo", "nao": "titulo"}, ("video", "antisserrilhado"): {"SMAA": "FXAA"}}
OVERLAY_MODES = {"so_fps": "1", "fps_grafico": "2", "completo": "3"}


def load_settings(path=None):
    path = path or SETTINGS_FILE
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    vals = {}
    for sec, key, _lbl, _opts, default, _env in SETTINGS:
        v = cp.get(sec, key, fallback=default)
        vals[(sec, key)] = LEGACY.get((sec, key), {}).get(v, v)
    return vals


def merge_settings(loaded, mine, disk):
    """Vale a ULTIMA mudanca (coordenador #4717): o menu F3 do jogo grava no mesmo port_settings.ini. Ao salvar, o
    launcher grava so o que o usuario mudou nele desde que abriu (mine != loaded); o resto fica como esta no disco."""
    return {k: (mine[k] if mine.get(k) != loaded.get(k) else disk.get(k, mine[k])) for k in mine}


def save_settings(vals, path=None, extra=None):
    """Grava as opcoes do launcher PRESERVANDO o resto do ini (secoes/chaves do F3 e do cellPad, ex. [controle]).
    extra = {secao: {chave: valor}} para gravar junto (a pagina Controles)."""
    path = path or SETTINGS_FILE
    cp = configparser.ConfigParser()
    cp.optionxform = str
    if Path(path).is_file():
        try:
            cp.read(path, encoding="utf-8")
        except configparser.Error:
            cp = configparser.ConfigParser(); cp.optionxform = str
    for sec, items in (extra or {}).items():
        if cp.has_section(sec):
            cp.remove_section(sec)
        cp.add_section(sec)
        for k, v in items.items():
            cp.set(sec, k, str(v))
    for sec, key, _lbl, _opts, default, _env in SETTINGS:
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, str(vals.get((sec, key), default)))
    with open(path, "w", encoding="utf-8") as f:
        f.write("; Opcoes do port (launcher T-257). As marcadas 'em breve' ainda nao sao lidas pelo jogo.\n")
        cp.write(f)


def settings_env(vals):
    """Traduz o ini para as variaveis que o port ja le (as 'em breve' nao geram nada)."""
    env = {}
    for sec, key, _lbl, _opts, default, var in SETTINGS:
        v = str(vals.get((sec, key), default))
        if var == "RSX_RES_SCALE" and RES_SCALE.get(v):
            env[var] = RES_SCALE[v]
        elif var == "RSX_ANISO" and v.endswith("x"):
            env[var] = v[:-1]          # T-258 (claude-gpu): RSX_ANISO=4/8/16; desligado = nao define
        elif var == "RSX_VSYNC":
            env[var] = "1" if v == "1" else "0"
        elif var == "PORT_AUDIO_MUTE":
            env[var] = "1" if v == "mudo" else "0"
        elif var == "PAD_KEYMAP_FILE" and v:
            env[var] = v
        elif var == "PAD_TYPE" and v in ("ds4", "ds5", "xbox"):
            env[var] = v               # auto = sem a chave (o cellPad decide)
        elif var == "PS3_NP_ONLINE_ID" and valid_nick(v):
            env[var] = v
        elif var == "PORT_AUDIO_VOLUME" and v.isdigit() and v != "100":
            env[var] = v               # % linear no mixer (claude-int, T-191); 100 = padrao = sem a chave
        elif var == "RSX_OVERLAY" and v in OVERLAY_MODES:
            env[var] = OVERLAY_MODES[v]
        elif var == "RSX_OVERLAY_POS" and v in ("tr", "bl", "br"):
            env[var] = v               # tl = padrao = sem a chave
        elif var == "RSX_FXAA" and v == "FXAA":
            env[var] = "1"
        elif var == "RSX_SHARPEN" and v.isdigit() and v != "0":
            env[var] = v
        elif var == "PS3_SYSTEM_LANG" and v in GAME_LANGS and v != default:
            env[var] = GAME_LANGS[v]   # padrao (ingles EUA) = sem a chave, como o port ja faz
        elif var == "PORT_WINDOW" and v != "janela":
            env[var] = v               # T-262: sem_borda / tela_cheia (janela = nao define)
    return env


def exe_reads(exe_path, names, reader=None):
    """Quais variaveis o exe realmente le: o nome aparece como texto no exe (getenv("RSX_ANISO")). Assim uma opcao
    so aparece 'ativo' quando o build instalado tem a chave (#4518: o ANISO aparecia ativo num exe sem ele)."""
    try:
        data = reader(exe_path) if reader else Path(exe_path).read_bytes()
    except OSError:
        return set()
    return {n for n in names if n and n.encode() + b"\0" in data}


def option_state(var, supported):
    """'ativo' | 'próximo build' (o port ja tem, o exe instalado nao) | 'em breve' (o port ainda nao le).
    supported=None = sem exe para conferir (PC do amigo antes de compilar): vale o que o port tem."""
    if not var:
        return "em breve"
    if supported is None or var in supported:
        return "ativo"
    return "próximo build"


# ---------------------------------------------------------------- aba (c): jogar

LAN_COMMON = {"PS3_NET_ONLINE": "1", "PORT_LAN_LOG": "1", "PORT_LAN_UI_MODE": "8",
              "PORT_LAN_FORCE_ADMIT": "", "PORT_LAN_S204": ""}
LAN_HOST = {"PS3_NP_ONLINE_ID": "asbrA", "PORT_LAN": "host", "PORT_LAN_AT": "225", "PORT_LAN_FLAG_EARLY": "1",
            "PORT_LAN_JOIN": "",
            "PAD_SCRIPT": "100:0x0008,105:0x0008,185:0x2000,192:0x4000,320:0x4000,330:0x4000,345:0x0008,"
                          "360:0x0008,375:0x4000,390:0x4000,405:0x4000,420:0x0008"}
LAN_JOIN = {"PS3_NP_ONLINE_ID": "asbrB", "PORT_LAN": "join", "PORT_LAN_AT": "245", "PORT_LAN_FLAG_EARLY": "",
            "PORT_LAN_JOIN": "asbrA", "PORT_LAN_JOIN_AT": "265",
            "PAD_SCRIPT": "100:0x0008,105:0x0008,185:0x2000,192:0x4000,320:0x4000,330:0x4000"}


def valid_lan_ip(ip):
    parts = ip.strip().split(".")
    if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return False
    return True


def play_env(game_dir, vals, lan=None, root=ROOT, update_dir=None):
    """Variaveis do jogo (as mesmas do 'Jogar port all star.bat' e do 'Jogar LAN.bat'), com a pasta do jogo DO usuario.

    lan = None (sozinho) ou {'papel': 'host'|'join', 'meu_ip': ..., 'amigo_ip': ...}.
    """
    # mesmas do 'Jogar port all star.bat' do Samuel. Sem SPURS_JOB_LANES=3 desde a T26: a piscada foi corrigida no
    # exe (mascara de prioridade da job chain; build-samuel 4f3f5e65, ORIGEM.txt)
    env = {"PS3_VFS_ROOT": str(Path(game_dir)), "PS3_SAVEDATA_PERSIST": "1",
           "PS3_TITLE": "PlayStation All-Stars Battle Royale", "SPU_XFLOAT": "2",
           # o menu F3 do jogo grava no MESMO ini que o launcher le (vale a ultima mudanca, #4717)
           "PORT_SETTINGS_INI": str(Path(root) / "port_settings.ini")}
    env.update(settings_env(vals))
    if update_dir:                                     # T-300: o update 1.12 + DLC do usuario (montado pelo runtime)
        env["PORT_UPDATE_DIR"] = str(Path(update_dir))
    tag = "launcher-jogo"
    if lan:
        for k in ("meu_ip", "amigo_ip"):
            if not valid_lan_ip(lan.get(k, "")):
                raise ValueError(f"IP invalido: {lan.get(k)!r} (use o IP local, 192.168.x.x)")
        env.update(LAN_COMMON)
        env.update(LAN_HOST if lan["papel"] == "host" else LAN_JOIN)
        env["PS3_NET_LAN_IP"] = lan["meu_ip"].strip()
        env["PS3_NET_LAN_PEERS"] = f"{lan['meu_ip'].strip()},{lan['amigo_ip'].strip()}"
        tag = "launcher-lan-" + lan["papel"]
    # cache do jogo limpo a cada partida (cache.idx truncado trava o boot, T-219); saves em user\saves
    env["PS3_HDD1_ROOT"] = str(Path(root) / "user" / "cache" / tag)
    return env, tag


def update_ready(state, root=ROOT):
    """Pasta do update 1.12 quando o 1.12 esta configurado (pasta salva + ELF do update conferido); senao None."""
    upd = (state or {}).get("update_dir")
    if upd and Path(upd).is_dir() and (Path(root) / "work" / "eboot" / ELF112_DEST.name).is_file():
        return upd
    return None


def play_command(root=ROOT, state=None):
    """Executavel do port. build-samuel primeiro: no PC do Samuel o build/ e o da integracao (muda no meio dos trens e um
    exe aberto trava o link do claude-int, T-170). No PC do amigo so existe o build/ que o kit compilou.
    Com o update 1.12 configurado (T-300) usa SO o exe do 1.12 com o ELF do update; sem esse exe devolve (None, None) e
    nunca abre o 1.00 no lugar (o usuario escolheu o 1.12)."""
    if state is None:
        state = load_state() if Path(root) == ROOT else {}
    if update_ready(state, root):
        for d in BUILD112_DIRS:
            exe = game_exe(Path(root) / d)
            if exe:
                return [str(exe), str(Path(root) / "work" / "eboot" / ELF112_DEST.name)], d
        return None, None
    for d in ("build-samuel", "build"):
        exe = game_exe(Path(root) / d)
        if exe:
            return [str(exe), str(Path(root) / "work" / "eboot" / "EBOOT_1.00_disc.elf")], d
    return None, None


# nomes do exe do jogo (T-285: MyGameRecomp.exe -> PSASBR.exe; a mesma lista de scripts/game_exe_names.txt)
GAME_EXE_NAMES = ("PSASBR.exe", "MyGameRecomp.exe")


def game_exe(folder):
    """O exe do jogo MAIS NOVO na pasta (como o run.ps1: durante a troca de nome os dois podem existir)."""
    found = [Path(folder) / n for n in GAME_EXE_NAMES if (Path(folder) / n).is_file()]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def running_games(root=ROOT):
    """[(pid, caminho)] dos exes do jogo abertos a partir das pastas de build deste port (build-samuel, build).
    So Windows; fora dele, []. Le os processos pela API (sem PowerShell: rapido)."""
    if os.name != "nt":
        return []
    import ctypes
    import ctypes.wintypes as W
    k, ps = ctypes.windll.kernel32, ctypes.windll.psapi
    arr, need = (W.DWORD * 4096)(), W.DWORD()
    if not ps.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(need)):
        return []
    dirs = [str((Path(root) / d)).lower() for d in ("build-samuel", "build")]
    names = {n.lower() for n in GAME_EXE_NAMES}
    out = []
    for pid in arr[:need.value // ctypes.sizeof(W.DWORD)]:
        h = k.OpenProcess(0x1000, False, pid)              # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            continue
        try:
            buf, n = ctypes.create_unicode_buffer(1024), W.DWORD(1024)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                path = Path(buf.value)
                if path.name.lower() in names and str(path.parent).lower() in dirs:
                    out.append((pid, str(path)))
        finally:
            k.CloseHandle(h)
    return out


def close_games(games, wait_s=15, sleep=None):
    """Encerra os jogos [(pid, caminho)] e espera sumirem (o cmd da vaga devolve a vaga sozinho). True se sumiram."""
    import time
    sleep = sleep or time.sleep
    for pid, _p in games:
        subprocess.run(["taskkill", "/f", "/pid", str(pid)], capture_output=True)
    for _ in range(int(wait_s * 4)):
        alive = {g[0] for g in running_games()}
        if not any(pid in alive for pid, _p in games):
            return True
        sleep(0.25)
    return False


def saves_dir(root=ROOT):
    return Path(root) / "user" / "saves"


def logs_dir(root=ROOT):
    return Path(root) / "user" / "logs"


def last_log(root=ROOT):
    return logs_dir(root) / "last_run.log"


def slot_cmd(action, root=ROOT):
    """No PC do Samuel (onde existe a fila de vagas dos agentes), o jogo pelo launcher pega a vaga 'samuel' como o
    'Jogar port all star.bat' (prioridade dele, nunca 3 jogos ao mesmo tempo). No PC do amigo nao ha fila: None."""
    gpu = Path(root) / "scripts" / "gpu.py"
    py = Path(root) / ".venv" / "Scripts" / "python.exe"
    if not (gpu.is_file() and py.is_file()):
        return None
    if action == "acquire":
        return [str(py), str(gpu), "acquire", "samuel", "--note", "Samuel pelo Launcher", "--minutes", "60", "--wait-min", "30"]
    return [str(py), str(gpu), "release", "samuel"]


# ---------------------------------------------------------------- cache de shaders (T-266; interface do claude-gpu #4660)
# <pasta do exe>\shadercache\: shaderlist.bin (programas vistos neste PC), *.dxbc, pipelines.bin. Pronto = existe
# 'ready-<SHA do exe>.txt'. Pre-compilar: 'MyGameRecomp.exe --precompile-shaders <ELF>', stdout com
# '[shc] precompile N/M' a cada passo e '[shc] precompile done M/M (X s)' no fim, codigo 0. So exes que tem a opcao
# (o nome aparece no exe) pre-compilam; nos outros o JOGAR segue como antes.
SHC_FLAG = "--precompile-shaders"
SHC_SOURCE_FLAG = "--shader-source-id"
_SHC_RE = re.compile(r"\[shc\] precompile (?:done )?(\d+)/(\d+)")


def shader_cache_dir(exe):
    return Path(exe).parent / "shadercache"


def shader_cache_ready(exe, hasher=sha256_file, identity=None):
    marker = shader_cache_dir(exe) / f"ready-{hasher(exe)}.txt"
    if identity is None:
        return marker.is_file()  # compatibility with exes predating the CFX reader
    try:
        return json.loads(marker.read_text(encoding="utf-8")) == identity
    except (OSError, ValueError):
        return False


def shader_source_identity(cmd, env, cwd, run=subprocess.run):
    """Read hashes/size/version from the user's CFX in RAM, without a D3D device or guest boot."""
    result = run([cmd[0], SHC_SOURCE_FLAG] + list(cmd[1:]), cwd=str(cwd), env=env,
                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                 **HIDDEN_CMD)
    prefix = "[shc] source identity: "
    for line in result.stdout.splitlines() if result.returncode == 0 else ():
        if line.startswith(prefix):
            identity = json.loads(line[len(prefix):])
            if (identity.get("schema") == 1 and identity.get("table") and identity.get("elf_sha256")
                    and identity.get("sources") and "game_version" in identity):
                return identity
    raise RuntimeError("nao foi possivel identificar os shaders do disco/update/DLC; preparo nao confirmado")


def supports_precompile(exe, reader=None):
    return SHC_FLAG in exe_reads(exe, {SHC_FLAG}, reader=reader)


def parse_shc(line):
    """'[shc] precompile 12/80' -> (12, 80); outras linhas -> None."""
    m = _SHC_RE.search(line)
    return (int(m.group(1)), int(m.group(2))) if m else None


def clear_shader_cache(exe, rmtree=shutil.rmtree):
    d = shader_cache_dir(exe)
    if d.exists():
        rmtree(d, ignore_errors=True)
    return d


# control (dict) da pre-compilacao: o launcher le control["proc"] e grava control["action"] = "play" (jogar mesmo
# assim: o jogo compila o resto jogando) ou "cancel"; stop_precompile() mata so o exe (o cmd segue e devolve a vaga).
# O exe grava cada shader na hora (claude-gpu #5407): a proxima rodada so compila o que faltou.


def stop_precompile(control, action, root=ROOT):
    control["action"] = action
    for pid, _p in running_games(root):
        subprocess.run(["taskkill", "/f", "/pid", str(pid)], capture_output=True)


def precompile_shaders(cmd, env, cwd, progress=None, root=ROOT, popen=subprocess.Popen, control=None):
    """Roda o exe com --precompile-shaders e chama progress(n, m) a cada linha '[shc]'. Log em user\\logs\\shaders.log."""
    logs = logs_dir(root)
    logs.mkdir(parents=True, exist_ok=True)
    pc = [cmd[0], SHC_FLAG] + list(cmd[1:])
    # o --precompile-shaders confere a biblioteca de PSO contra o driver = cria device D3D12: no PC do Samuel tambem
    # passa pela vaga 'samuel' (claude-otim #5105)
    pc = slot_wrapped(pc, root) or pc
    with open(logs / "shaders.log", "w", encoding="utf-8", errors="replace") as log:
        p = popen(pc, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                  encoding="utf-8", errors="replace", **(HIDDEN_CMD if isinstance(pc, str) else {}))
        if control is not None:
            control["proc"] = p
        for line in p.stdout:
            log.write(line)
            nm = parse_shc(line)
            if nm and progress:
                progress(*nm)
        return p.wait()


# o cmd que segura a vaga nao precisa de janela (o Samuel via uma janela preta parada); a janela do jogo e dele mesmo
HIDDEN_CMD = {"creationflags": 0x08000000} if os.name == "nt" else {}    # CREATE_NO_WINDOW


def slot_wrapped(cmd, root=ROOT):
    """Linha de comando que segura a vaga 'samuel' ENQUANTO O JOGO RODA (claude-otim #4953). O gpu.py grava como dono
    da vaga o 1o processo nao-python acima dele; aberto pelo launcher, esse era o cmd do 'Abrir Launcher.bat', que ja
    tinha terminado -> a vaga caia na hora. Aqui um cmd vive o tempo do jogo: pega a vaga, roda o jogo, devolve (como o
    atalho antigo). None fora do PC do Samuel (sem fila)."""
    acq, rel = slot_cmd("acquire", root), slot_cmd("release", root)
    if not acq:
        return None
    q = lambda v: '"%s"' % v if (" " in v or not v) else v
    acq = acq[:acq.index("--note") + 1] + ["Samuel_pelo_Launcher"] + acq[acq.index("--note") + 2:]
    acq[acq.index("--minutes") + 1] = "240"
    inner = "%s && %s & %s" % (" ".join(map(q, acq)), " ".join(map(q, cmd)), " ".join(map(q, rel)))
    return 'cmd /s /c "%s"' % inner


def launch_game(game_dir, vals, lan=None, root=ROOT, popen=subprocess.Popen, rmtree=shutil.rmtree, run=subprocess.run,
                progress=None, only_shaders=False, hasher=sha256_file, reader=None, control=None, state=None):
    """Abre o jogo. progress(n, m): chamado durante a pre-compilacao de shaders (quando o exe tem a opcao e o cache
    nao esta pronto). only_shaders=True: so (re)compila os shaders, sem abrir o jogo (Avancado -> Recompilar)."""
    if state is None:
        state = load_state() if Path(root) == ROOT else {}
    upd = update_ready(state, root)
    cmd, which = play_command(root, state)
    if not cmd:
        raise FileNotFoundError("nao achei o exe do jogo (PSASBR.exe): faca a aba 'Preparar com o seu jogo' primeiro"
                                + (" (com o update 1.12 escolhido, o passo 5 gera tambem o exe do 1.12)" if upd else ""))
    env_add, tag = play_env(game_dir, vals, lan, root, update_dir=upd)
    hdd = Path(env_add["PS3_HDD1_ROOT"])
    if hdd.exists():
        rmtree(hdd, ignore_errors=True)
    hdd.mkdir(parents=True, exist_ok=True)
    wd = saves_dir(root)
    wd.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for k, v in env_add.items():
        if v == "":
            env.pop(k, None)
        else:
            env[k] = v
    source_identity = None
    prepare_exe_hash = hasher(cmd[0])
    if SHC_SOURCE_FLAG in exe_reads(cmd[0], {SHC_SOURCE_FLAG}, reader=reader):
        source_identity = shader_source_identity(cmd, env, wd)
    if supports_precompile(cmd[0], reader) and (only_shaders or not shader_cache_ready(cmd[0], hasher, source_identity)):
        control = {} if control is None else control
        rc = precompile_shaders(cmd, env, wd, progress, root, popen, control)
        action = control.get("action")
        if action == "cancel":
            return None, which, tag
        if action != "play":                           # 'jogar mesmo assim' segue sem o marcador (recompila depois)
            if rc != 0:
                raise RuntimeError("a compilacao de shaders falhou: veja user\\logs\\shaders.log")
            if source_identity is not None and shader_source_identity(cmd, env, wd) != source_identity:
                raise RuntimeError("os arquivos do jogo mudaram durante o preparo; repita a compilacao de shaders")
            if hasher(cmd[0]) != prepare_exe_hash:
                raise RuntimeError("o executavel mudou durante o preparo; repita a compilacao de shaders")
            # o exe nao grava o marcador (claude-gpu #4885): o launcher grava ao receber codigo 0
            d = shader_cache_dir(cmd[0])
            d.mkdir(parents=True, exist_ok=True)
            (d / f"ready-{prepare_exe_hash}.txt").write_text(
                json.dumps(source_identity, ensure_ascii=False, sort_keys=True) if source_identity is not None else "ok\n",
                encoding="utf-8")
    if only_shaders:
        return None, which, tag
    logs = logs_dir(root)
    logs.mkdir(parents=True, exist_ok=True)
    # o jogo herda o arquivo de log; o launcher fecha a sua copia logo depois de abrir o processo.
    # last_run.log = sempre o da ultima partida (o que o guia manda enviar ao Samuel).
    # no PC do Samuel o jogo sobe por um cmd que segura a vaga 'samuel' ate ele fechar (slot_wrapped)
    line = slot_wrapped(cmd, root)
    lg = last_log(root)
    if lg.is_file():                                   # guarda o log da partida anterior (o 2o clique apagava o 1o)
        try:
            lg.replace(lg.with_name("last_run.prev.log"))
        except OSError:
            pass
    with open(lg, "w", encoding="utf-8", errors="replace") as out:
        proc = popen(line or cmd, cwd=str(wd), env=env, stdout=out, stderr=subprocess.STDOUT,
                     **(HIDDEN_CMD if line else {}))
    return proc, which, tag


# ---------------------------------------------------------------- estado, status e avancado

def load_state(path=None):
    path = Path(path) if path else STATE_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(st, path=None):
    path = Path(path) if path else STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def status(state, root=ROOT, t=lambda s: s):
    """Resumo para a pagina Inicio: o que falta para jogar. t = traducao do launcher (i18n.t)."""
    falta = []
    if not state.get("game_dir") or not Path(state["game_dir"]).exists():
        falta.append(t("escolher a pasta do jogo"))
    if not (Path(root) / "work" / "eboot" / "EBOOT_1.00_disc.elf").is_file():
        falta.append(t("decriptar e conferir o EBOOT (aba Preparar)"))
    if state.get("update_dir") and not (Path(root) / "work" / "eboot" / ELF112_DEST.name).is_file():
        falta.append(t("conferir o ELF do update 1.12 (aba Preparar)"))
    if not play_command(root, state)[0]:
        falta.append(t("gerar e compilar o port (aba Preparar)"))
    return (t("Pronto para jogar.") if not falta else t("Falta:") + " " + "; ".join(falta) + "."), not falta


def clear_cache(root=ROOT, rmtree=shutil.rmtree):
    d = Path(root) / "user" / "cache"
    if d.exists():
        rmtree(d, ignore_errors=True)
    return d


def ico_from_png(png_bytes):
    """Arquivo .ico com 1 imagem PNG dentro (aceito pelo Windows desde o Vista); a PNG deve ter ate 256x256."""
    w, h = struct.unpack(">II", png_bytes[16:24])
    entry = struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(png_bytes), 6 + 16)
    return struct.pack("<HHH", 0, 1, 1) + entry + png_bytes


def shortcut_icon_path(root=ROOT):
    """Icone do atalho, gerado do ICON0 do jogo DO USUARIO (fica em user\\, nunca no pacote)."""
    return Path(root) / "user" / "allstars.ico"


def desktop_shortcut_command(target, name="Jogar All-Stars", desktop=None, icon=None):
    """Comando do PowerShell que cria o atalho na area de trabalho (so quando o usuario clica)."""
    desktop = desktop or os.path.join(os.path.expanduser("~"), "Desktop")
    lnk = os.path.join(desktop, name + ".lnk")
    q = lambda v: str(v).replace("'", "''")
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath='{t}';"
          "$s.WorkingDirectory='{w}';").format(lnk=q(lnk), t=q(target), w=q(Path(target).parent))
    if icon and Path(icon).is_file():
        ps += "$s.IconLocation='{i},0';".format(i=q(icon))
    ps += "$s.Save()"
    return ["powershell", "-NoProfile", "-Command", ps], lnk


def play_direct(lan=False, root=ROOT, popen=subprocess.Popen, state=None, vals=None, progress=None):
    """'Jogar All-Stars.bat': abre com o que esta salvo (pasta do jogo, opcoes e, com lan=True, a LAN salva)."""
    state = load_state() if state is None else state
    vals = load_settings() if vals is None else vals
    game = state.get("game_dir")
    if not game:
        raise FileNotFoundError("abra o Launcher uma vez e escolha a pasta do jogo")
    lan_cfg = None
    if lan:
        lan_cfg = {"papel": state.get("papel", "host"), "meu_ip": state.get("meu_ip", ""), "amigo_ip": state.get("amigo_ip", "")}
    return launch_game(game, vals, lan_cfg, root=root, popen=popen, progress=progress, state=state)
