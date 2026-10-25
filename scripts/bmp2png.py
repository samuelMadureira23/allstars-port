"""Convert 24/32-bit BMPs (rsxcap output) to PNG using only the standard library.

Usage: python scripts/bmp2png.py <in.bmp> [out.png] [--scale N]   (N = integer downscale)
"""
import struct
import sys
import zlib


def read_bmp(path):
    d = open(path, "rb").read()
    off = struct.unpack_from("<I", d, 10)[0]
    w, h = struct.unpack_from("<ii", d, 18)
    bpp = struct.unpack_from("<H", d, 28)[0]
    bottom_up = h > 0
    h = abs(h)
    bpr = w * (bpp // 8)
    stride = (bpr + 3) & ~3
    rows = []
    for y in range(h):
        r = d[off + y * stride: off + y * stride + bpr]
        px = []
        step = bpp // 8
        for x in range(w):
            b, g, rr = r[x * step], r[x * step + 1], r[x * step + 2]
            px.append((rr, g, b))
        rows.append(px)
    if bottom_up:
        rows.reverse()
    return w, h, rows


def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in rows)
    def chunk(t, data):
        c = struct.pack(">I", len(data)) + t + data
        return c + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def main():
    args = [a for a in sys.argv[1:]]
    scale = 1
    if "--scale" in args:
        i = args.index("--scale"); scale = int(args[i + 1]); del args[i:i + 2]
    src = args[0]
    dst = args[1] if len(args) > 1 else src.rsplit(".", 1)[0] + ".png"
    w, h, rows = read_bmp(src)
    if scale > 1:
        rows = [row[::scale] for row in rows[::scale]]
        w, h = len(rows[0]), len(rows)
    nonblack = sum(1 for row in rows for p in row if p != (0, 0, 0))
    write_png(dst, w, h, rows)
    print(f"{dst} {w}x{h} nonblack={nonblack}")


if __name__ == "__main__":
    main()
