"""Codec de mensagens STUN (RFC 5389) com os atributos de TURN (RFC 5766).

So o necessario para um servidor STUN/TURN pequeno: cabecalho, atributos,
XOR-MAPPED-ADDRESS / XOR-PEER-ADDRESS / XOR-RELAYED-ADDRESS,
MESSAGE-INTEGRITY (HMAC-SHA1) e FINGERPRINT (CRC32).
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import struct
import zlib
from dataclasses import dataclass, field

MAGIC_COOKIE = 0x2112A442
HEADER = struct.Struct("!HHI12s")

# Classes (bits C1 C0 espalhados no tipo).
CLASS_REQUEST = 0x0000
CLASS_INDICATION = 0x0010
CLASS_SUCCESS = 0x0100
CLASS_ERROR = 0x0110
CLASS_MASK = 0x0110

# Metodos.
BINDING = 0x0001
ALLOCATE = 0x0003
REFRESH = 0x0004
SEND = 0x0006
DATA = 0x0007
CREATE_PERMISSION = 0x0008
CHANNEL_BIND = 0x0009

# Atributos.
MAPPED_ADDRESS = 0x0001
USERNAME = 0x0006
MESSAGE_INTEGRITY = 0x0008
ERROR_CODE = 0x0009
UNKNOWN_ATTRIBUTES = 0x000A
CHANNEL_NUMBER = 0x000C
LIFETIME = 0x000D
XOR_PEER_ADDRESS = 0x0012
DATA_ATTR = 0x0013
REALM = 0x0014
NONCE = 0x0015
XOR_RELAYED_ADDRESS = 0x0016
REQUESTED_ADDRESS_FAMILY = 0x0017
EVEN_PORT = 0x0018
REQUESTED_TRANSPORT = 0x0019
DONT_FRAGMENT = 0x001A
XOR_MAPPED_ADDRESS = 0x0020
RESERVATION_TOKEN = 0x0022
SOFTWARE = 0x8022
FINGERPRINT = 0x8028
RESPONSE_ORIGIN = 0x802B

FINGERPRINT_XOR = 0x5354554E

# Atributos de compreensao obrigatoria (< 0x8000) que este servidor entende.
KNOWN_REQUIRED = {
    MAPPED_ADDRESS, USERNAME, MESSAGE_INTEGRITY, ERROR_CODE, UNKNOWN_ATTRIBUTES,
    CHANNEL_NUMBER, LIFETIME, XOR_PEER_ADDRESS, DATA_ATTR, REALM, NONCE,
    XOR_RELAYED_ADDRESS, REQUESTED_ADDRESS_FAMILY, EVEN_PORT, REQUESTED_TRANSPORT,
    DONT_FRAGMENT, XOR_MAPPED_ADDRESS, RESERVATION_TOKEN,
}

ERROR_REASONS = {
    300: "Try Alternate",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    420: "Unknown Attribute",
    437: "Allocation Mismatch",
    438: "Stale Nonce",
    440: "Address Family not Supported",
    441: "Wrong Credentials",
    442: "Unsupported Transport Protocol",
    486: "Allocation Quota Reached",
    500: "Server Error",
    508: "Insufficient Capacity",
}


class StunError(Exception):
    pass


def method_of(msg_type: int) -> int:
    return (msg_type & 0x000F) | ((msg_type & 0x00E0) >> 1) | ((msg_type & 0x3E00) >> 2)


def class_of(msg_type: int) -> int:
    return msg_type & CLASS_MASK


def make_type(method: int, cls: int) -> int:
    return (method & 0x000F) | ((method & 0x0070) << 1) | ((method & 0x0F80) << 2) | cls


def is_stun(data: bytes) -> bool:
    """Testa se um datagrama parece STUN (dois bits altos zero + magic cookie)."""
    return (
        len(data) >= 20
        and data[0] & 0xC0 == 0
        and struct.unpack_from("!I", data, 4)[0] == MAGIC_COOKIE
        and struct.unpack_from("!H", data, 2)[0] % 4 == 0
    )


def is_channel_data(data: bytes) -> bool:
    return len(data) >= 4 and 0x40 <= data[0] <= 0x7F


@dataclass
class Message:
    method: int
    cls: int
    transaction_id: bytes = field(default_factory=lambda: os.urandom(12))
    attrs: list[tuple[int, bytes]] = field(default_factory=list)
    # Bytes brutos recebidos (para conferir MESSAGE-INTEGRITY / FINGERPRINT).
    raw: bytes = b""
    # Offset do atributo MESSAGE-INTEGRITY dentro de raw, se houver.
    integrity_offset: int = -1

    # -- acesso a atributos -------------------------------------------------
    def get(self, attr_type: int) -> bytes | None:
        for t, v in self.attrs:
            if t == attr_type:
                return v
        return None

    def add(self, attr_type: int, value: bytes) -> "Message":
        self.attrs.append((attr_type, value))
        return self

    def unknown_required(self) -> list[int]:
        return [t for t, _ in self.attrs if t < 0x8000 and t not in KNOWN_REQUIRED]

    # -- endereco XOR -------------------------------------------------------
    def get_xor_address(self, attr_type: int) -> tuple[str, int] | None:
        v = self.get(attr_type)
        if v is None:
            return None
        return decode_xor_address(v, self.transaction_id)

    def add_xor_address(self, attr_type: int, addr: tuple[str, int]) -> "Message":
        return self.add(attr_type, encode_xor_address(addr, self.transaction_id))

    def add_error(self, code: int, reason: str | None = None) -> "Message":
        reason = reason if reason is not None else ERROR_REASONS.get(code, "Error")
        body = struct.pack("!HBB", 0, code // 100, code % 100) + reason.encode()
        return self.add(ERROR_CODE, body)

    def error_code(self) -> int | None:
        v = self.get(ERROR_CODE)
        if v is None or len(v) < 4:
            return None
        return (v[2] & 0x07) * 100 + v[3]

    # -- serializacao -------------------------------------------------------
    def encode(self, integrity_key: bytes | None = None, fingerprint: bool = False) -> bytes:
        body = b"".join(_pack_attr(t, v) for t, v in self.attrs)
        msg_type = make_type(self.method, self.cls)
        if integrity_key is not None:
            # O tamanho no cabecalho inclui o proprio MESSAGE-INTEGRITY (24 bytes).
            hdr = HEADER.pack(msg_type, len(body) + 24, MAGIC_COOKIE, self.transaction_id)
            mac = hmac.new(integrity_key, hdr + body, hashlib.sha1).digest()
            body += _pack_attr(MESSAGE_INTEGRITY, mac)
        if fingerprint:
            hdr = HEADER.pack(msg_type, len(body) + 8, MAGIC_COOKIE, self.transaction_id)
            crc = (zlib.crc32(hdr + body) ^ FINGERPRINT_XOR) & 0xFFFFFFFF
            body += _pack_attr(FINGERPRINT, struct.pack("!I", crc))
        return HEADER.pack(msg_type, len(body), MAGIC_COOKIE, self.transaction_id) + body

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        if len(data) < 20:
            raise StunError("curto demais")
        msg_type, length, cookie, tid = HEADER.unpack_from(data, 0)
        if cookie != MAGIC_COOKIE:
            raise StunError("magic cookie errado")
        if msg_type & 0xC000:
            raise StunError("bits altos do tipo")
        if 20 + length > len(data) or length % 4:
            raise StunError("tamanho invalido")
        msg = cls(method_of(msg_type), class_of(msg_type), tid, [], data[: 20 + length])
        off = 20
        end = 20 + length
        while off + 4 <= end:
            t, ln = struct.unpack_from("!HH", data, off)
            if off + 4 + ln > end:
                raise StunError("atributo truncado")
            if t == MESSAGE_INTEGRITY:
                msg.integrity_offset = off
            msg.attrs.append((t, bytes(data[off + 4: off + 4 + ln])))
            off += 4 + ((ln + 3) & ~3)
            if t == FINGERPRINT:
                break
        return msg

    def check_integrity(self, key: bytes) -> bool:
        if self.integrity_offset < 0:
            return False
        mac = self.get(MESSAGE_INTEGRITY)
        if mac is None or len(mac) != 20:
            return False
        # Tamanho ajustado para terminar logo depois do MESSAGE-INTEGRITY.
        adj_len = self.integrity_offset + 24 - 20
        hdr = struct.pack("!HH", make_type(self.method, self.cls), adj_len) + self.raw[4:20]
        expected = hmac.new(key, hdr + self.raw[20: self.integrity_offset], hashlib.sha1).digest()
        return hmac.compare_digest(mac, expected)


def _pack_attr(t: int, v: bytes) -> bytes:
    pad = (-len(v)) % 4
    return struct.pack("!HH", t, len(v)) + v + b"\x00" * pad


def encode_xor_address(addr: tuple[str, int], tid: bytes) -> bytes:
    host, port = addr[0], addr[1]
    ip = ipaddress.ip_address(host)
    xport = port ^ (MAGIC_COOKIE >> 16)
    if ip.version == 4:
        xip = int(ip) ^ MAGIC_COOKIE
        return struct.pack("!BBHI", 0, 0x01, xport, xip)
    key = struct.pack("!I", MAGIC_COOKIE) + tid
    xip = bytes(a ^ b for a, b in zip(ip.packed, key))
    return struct.pack("!BBH", 0, 0x02, xport) + xip


def decode_xor_address(v: bytes, tid: bytes) -> tuple[str, int]:
    if len(v) < 8:
        raise StunError("endereco curto")
    family = v[1]
    port = struct.unpack_from("!H", v, 2)[0] ^ (MAGIC_COOKIE >> 16)
    if family == 0x01:
        ip = struct.unpack_from("!I", v, 4)[0] ^ MAGIC_COOKIE
        return str(ipaddress.IPv4Address(ip)), port
    if family == 0x02 and len(v) >= 20:
        key = struct.pack("!I", MAGIC_COOKIE) + tid
        raw = bytes(a ^ b for a, b in zip(v[4:20], key))
        return str(ipaddress.IPv6Address(raw)), port
    raise StunError("familia de endereco desconhecida")


def encode_plain_address(addr: tuple[str, int]) -> bytes:
    ip = ipaddress.ip_address(addr[0])
    fam = 0x01 if ip.version == 4 else 0x02
    return struct.pack("!BBH", 0, fam, addr[1]) + ip.packed


def long_term_key(username: str, realm: str, password: str) -> bytes:
    return hashlib.md5(f"{username}:{realm}:{password}".encode()).digest()


def reply_to(req: Message, success: bool = True) -> Message:
    return Message(req.method, CLASS_SUCCESS if success else CLASS_ERROR, req.transaction_id)
