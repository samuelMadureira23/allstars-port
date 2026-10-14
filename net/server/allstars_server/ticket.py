"""Gera tickets NP no formato 2.1 do PS3 (big-endian, campos tipados).

O jogo pode repassar o ticket ao servidor de jogo (OTG) e ler campos com
sceNpManagerGetTicketParam. Como os dois lados (HLE do cliente e este servidor)
sao nossos, a assinatura e um HMAC-SHA1 com segredo do servidor, nao ECDSA da Sony.

Layout:
    u32 versao (0x21010000) | u32 tamanho do resto
    blob 0x3000 corpo:
        binary  serial_id (20)      u32 issuer_id      time issued      time expires
        u64     user_id             bstring online_id (32)
        binary  region (4)          bstring domain (4)  binary service_id (24)
        u32     status              empty               empty
    blob 0x3002 assinatura: binary cipher_id (4) | binary sig (20)
Campo = u16 tipo | u16 tamanho | dados.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import struct
import time

T_EMPTY, T_U32, T_U64, T_BSTRING, T_TIME, T_BINARY = 0, 1, 2, 4, 7, 8
BLOB_BODY, BLOB_FOOTER = 0x3000, 0x3002
VERSION_2_1 = 0x21010000
ISSUER_ID = 0x00000100
CIPHER_ID = b"ASBR"


def _field(t: int, data: bytes) -> bytes:
    return struct.pack(">HH", t, len(data)) + data


def _fixed(s: bytes, n: int) -> bytes:
    return s[:n].ljust(n, b"\x00")


def build_ticket(secret: bytes, user_id: int, online_id: str, service_id: str,
                 region: bytes = b"us", domain: bytes = b"un", lifetime: int = 3600,
                 cookie: bytes = b"") -> bytes:
    now_ms = int(time.time() * 1000)
    body = b"".join([
        _field(T_BINARY, _fixed(os.urandom(10).hex().encode(), 20)),
        _field(T_U32, struct.pack(">I", ISSUER_ID)),
        _field(T_TIME, struct.pack(">Q", now_ms)),
        _field(T_TIME, struct.pack(">Q", now_ms + lifetime * 1000)),
        _field(T_U64, struct.pack(">Q", user_id)),
        _field(T_BSTRING, _fixed(online_id.encode(), 32)),
        _field(T_BINARY, _fixed(region, 4)),
        _field(T_BSTRING, _fixed(domain, 4)),
        _field(T_BINARY, _fixed(service_id.encode(), 24)),
        _field(T_U32, struct.pack(">I", 0)),
        _field(T_EMPTY, b""),
        _field(T_EMPTY, b""),
    ])
    if cookie:
        body += _field(T_BINARY, cookie[:1024])
    body_blob = _field(BLOB_BODY, body)
    sig = hmac.new(secret, body_blob, hashlib.sha1).digest()
    footer = _field(BLOB_FOOTER, _field(T_BINARY, CIPHER_ID) + _field(T_BINARY, sig))
    rest = body_blob + footer
    return struct.pack(">II", VERSION_2_1, len(rest)) + rest


def parse_ticket(data: bytes) -> dict:
    """Le um ticket gerado por build_ticket (usado em testes e pelo servidor de jogo)."""
    version, size = struct.unpack_from(">II", data, 0)
    off = 8
    t, ln = struct.unpack_from(">HH", data, off)
    if t != BLOB_BODY:
        raise ValueError("ticket sem corpo")
    body = data[off + 4: off + 4 + ln]
    body_blob = data[off: off + 4 + ln]
    off += 4 + ln
    fields = []
    p = 0
    while p < len(body):
        ft, fl = struct.unpack_from(">HH", body, p)
        fields.append((ft, body[p + 4: p + 4 + fl]))
        p += 4 + fl
    t, ln = struct.unpack_from(">HH", data, off)
    footer = data[off + 4: off + 4 + ln]
    sig = footer[4 + 4 + 4:]
    return {
        "version": version,
        "serial": fields[0][1].rstrip(b"\x00").decode(),
        "issuer": struct.unpack(">I", fields[1][1])[0],
        "issued_ms": struct.unpack(">Q", fields[2][1])[0],
        "expires_ms": struct.unpack(">Q", fields[3][1])[0],
        "user_id": struct.unpack(">Q", fields[4][1])[0],
        "online_id": fields[5][1].rstrip(b"\x00").decode(),
        "region": fields[6][1].rstrip(b"\x00"),
        "domain": fields[7][1].rstrip(b"\x00"),
        "service_id": fields[8][1].rstrip(b"\x00").decode(),
        "body_blob": body_blob,
        "signature": sig,
    }


def verify_ticket(secret: bytes, data: bytes) -> dict | None:
    try:
        info = parse_ticket(data)
    except (struct.error, ValueError, IndexError, UnicodeDecodeError):
        return None
    good = hmac.new(secret, info["body_blob"], hashlib.sha1).digest()
    if not hmac.compare_digest(good, info["signature"]):
        return None
    if info["expires_ms"] < time.time() * 1000:
        return None
    return info
