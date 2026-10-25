"""Monta o pacote do port para o amigo (T-257/T-262). Roda no PC do Samuel; o resultado vai ao critico antes de sair.

Leva SO o que e nosso, nos commits exatos do build de referencia (launcher/referencia.json):
  src/ps3recomp (git archive), src/allstars-ps3 (git archive), launcher/, kit/ (com os lifters fixos de
  fazer_ferramentas.py), scripts/build.bat, os .bat de abrir/jogar e o guia docs/COMO_JOGAR_COM_AMIGO.md.
Nada de work/, build*/, user/, EBOOT/ELF, codigo gerado, .psarc, assets nem firmware: o amigo gera tudo com o
Launcher a partir do PROPRIO disco. O fonte do ps3recomp vai como esta (com as chaves SDAT/EDAT): excecao do Samuel
(#4461, 19/10), so neste pacote.

Uso: python kit\\montar_pacote.py [--out dist\\AllStarsPort_kit]   (sai com codigo 1 se achar algo proibido)
"""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["scripts/build.bat", "docs/COMO_JOGAR_COM_AMIGO.md",
         "docs/HOW_TO_PLAY_WITH_A_FRIEND.md", "docs/PROBLEMAS_COMUNS.md",
         "docs/COMO_JOGAR_ONLINE_F3.md"]
DIRS = ["launcher", "kit"]
# tipos que nunca podem ir (conteudo do jogo, binarios do PS3, capturas, firmware, pacotes)
PROIBIDO = {".elf", ".self", ".sprx", ".prx", ".bin", ".psarc", ".pkg", ".pup", ".rrc", ".rsxf", ".sfo", ".edat",
            ".sdat", ".rap", ".rif", ".at3", ".at9", ".vag", ".bik", ".pam", ".dds", ".gtf", ".mp4", ".exe", ".dll",
            ".pdb", ".obj", ".lib", ".gz", ".zip", ".7z", ".rar"}
IGNORAR_DIR = {"__pycache__", ".git"}
# Samuel 21/10: o pacote leva os atalhos em .exe (launcher\stub, compilados aqui SEM o icone do jogo), nao em .bat.
# Sao os unicos .exe permitidos.
STUB_EXES = {"Open Launcher.exe", "Play All-Stars.exe"}
TEXTO = {".py", ".c", ".h", ".cpp", ".hpp", ".inc", ".cmake", ".txt", ".md", ".json", ".bat", ".rc", ".sh", ".toml", ".yml",
         ".m", ".java", ".patch", ".vert", ".deps"}
# versao para outros usuarios (Samuel 21/10): sem o nome do dono do projeto em comentarios, testes e nomes internos.
# Troca uniforme em todo o pacote (a vaga 'samuel' do launcher so existe no PC de desenvolvimento, onde ha scripts/gpu.py;
# no pacote ela vira 'local' nos dois lados, core.py e testes).
LIMPAR = [(r"Abrir Launcher\.bat", "Abrir Launcher.exe"), (r"Jogar All-Stars\.bat", "Jogar All-Stars.exe"),
          (r"\((?:pedido |decis[aã]o )?(?:do )?Samuel,? (\d+/\d+)\)", r"(\1)"), (r",? Samuel (\d+/\d+)", r" \1"),
          (r"(?<=\()Samuel (\d+/\d+)", r"\1"), (r"Samuel pelo Launcher", "Jogo pelo Launcher"), (r"\bpelo Samuel\b", "pelo usuario"),
          (r"requested by the Samuel", "requested by users"), (r"the Samuel's", "the user's"),
          (r"\bdo Samuel\b", "do usuario"), (r"\bo Samuel\b", "o usuario"), (r"\bao Samuel\b", "ao usuario"),
          (r"Samuel_pelo_Launcher", "Jogo_pelo_Launcher"), (r"SamuelF3", "Jogador1F3"), (r"\bSamuel\b", "Jogador1"),
          (r"samuels_pc", "dev_pc"), (r"SAMUEL", "LOCAL"), (r"samuel", "local")]


def git_export(repo, commit, dest):
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit],
                          capture_output=True, check=True).stdout
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(dest, filter="data")


def copy_tree(src, dst):
    for p in src.rglob("*"):
        if p.is_file() and not (set(p.relative_to(src).parts) & IGNORAR_DIR):
            out = dst / p.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, out)


def limpar_nomes(out):
    import re
    n = 0
    for p in out.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXTO:
            try:
                s = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            s2 = s
            for a, b in LIMPAR:
                s2 = re.sub(a, b, s2)
            if s2 != s:
                p.write_text(s2, encoding="utf-8", newline="")
                n += 1
    return n


def audit(out):
    bad, big = [], []
    for p in out.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(out).as_posix()
        if p.suffix.lower() in PROIBIDO and not (p.parent == out and p.name in STUB_EXES):
            bad.append(rel)
        if p.stat().st_size > 2_000_000:
            big.append((p.stat().st_size, rel))
    return bad, sorted(big, reverse=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist" / "AllStarsPort_kit"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    ref = json.loads((ROOT / "launcher" / "referencia.json").read_text(encoding="utf-8"))
    for name in ("tools_ppu_e0dafce3", "tools_spu_3557fed5", "tools_rt_fdffa4a3"):
        if not (ROOT / "kit" / name / "tools").is_dir():
            sys.exit(f"ERRO: falta kit/{name}: rode antes  python kit\\fazer_ferramentas.py")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    git_export(ROOT / "src" / "ps3recomp", ref["ps3recomp_commit"], out / "src" / "ps3recomp")
    git_export(ROOT / "src" / "allstars-ps3", ref["allstars_ps3_commit"], out / "src" / "allstars-ps3")
    for d in DIRS:
        copy_tree(ROOT / d, out / d)
    for f in FILES:
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / f, out / f)
    (out / "kit" / "montar_pacote.py").unlink(missing_ok=True)     # ferramenta do Samuel, nao do amigo
    shutil.copyfile(ROOT / "docs" / "README_GITHUB.md", out / "README.md")
    shutil.copyfile(ROOT / "docs" / "README_GITHUB_EN.md", out / "README_GITHUB_EN.md")   # o README.md aponta para ele (mesma pasta)
    print(f"nomes pessoais limpos em {limpar_nomes(out)} arquivos")
    r = subprocess.run([str(ROOT / "launcher" / "stub" / "build_stub.bat"), "public", str(out.resolve())],
                       capture_output=True, text=True)
    if r.returncode != 0 or not all((out / n).is_file() for n in STUB_EXES):
        sys.exit("ERRO: nao consegui compilar os atalhos .exe (launcher\\stub\\build_stub.bat public):\n" + r.stdout + r.stderr)
    shutil.rmtree(out / "_stub_obj", ignore_errors=True)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    n = sum(1 for p in out.rglob("*") if p.is_file())
    (out / "ORIGEM_KIT.txt").write_text(
        f"Pacote do port PlayStation All-Stars Battle Royale (PC) - montado em {datetime.now():%Y-%m-%d %H:%M}\n"
        f"Projeto (launcher/kit/scripts): {head}\n"
        f"ps3recomp: {ref['ps3recomp_commit']}  allstars-ps3: {ref['allstars_ps3_commit']}\n"
        f"Exe de referencia: {ref['exe_sha256']} ({ref['exe_label']}; reprodutivel: {ref['exe_reprodutivel']})\n"
        f"Jogo esperado: {ref['title_id']} disco 1.00, EBOOT.BIN SHA-256 {ref['eboot_sha256']}\n"
        f"{n} arquivos. NAO contem nada do jogo: cada um usa a propria copia (Abrir Launcher.bat -> Preparar).\n",
        encoding="utf-8")
    bad, big = audit(out)
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"pacote: {out}  ({n + 1} arquivos, {total / 1e6:.1f} MB)")
    for size, rel in big[:10]:
        print(f"  grande: {size / 1e6:6.1f} MB  {rel}")
    if bad:
        print("PROIBIDO no pacote:", *bad, sep="\n  ")
        return 1
    print("auditoria automatica: nenhum tipo proibido (o critico ainda confere antes de enviar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
