"""Formato de fio do protocolo NPX (substituto do PSN para o cliente nativo).

Pacote = cabecalho de 12 bytes + corpo. Tudo little-endian (o cliente roda em x86-64).

    u8  kind        1 = pedido, 2 = resposta, 3 = notificacao
    u8  flags       reservado (0)
    u16 command     ver Cmd
    u32 size        tamanho total, cabecalho incluso
    u32 req_id      id do pedido (repetido na resposta; 0 em notificacoes)

Toda resposta comeca com u8 error (ver Err). Strings: u16 tamanho + UTF-8.
Blobs: u32 tamanho + bytes. Listas: u16 quantidade + itens.
A especificacao completa fica em docs/net.md.
"""
from __future__ import annotations

import enum
import struct

HEADER = struct.Struct("<BBHII")
HEADER_SIZE = HEADER.size
MAX_PACKET = 1 << 20
PROTOCOL_VERSION = 1


class Kind(enum.IntEnum):
    REQUEST = 1
    REPLY = 2
    NOTIFY = 3


class Cmd(enum.IntEnum):
    HELLO = 0x0001
    LOGIN = 0x0002
    LOGOUT = 0x0003
    PING = 0x0004
    GET_TICKET = 0x0010
    LOOKUP_ONLINE_ID = 0x0011
    SET_PRESENCE = 0x0020
    GET_FRIENDS = 0x0021
    SEND_MESSAGE = 0x0022
    SIG_REGISTER = 0x0030
    SIG_CONNECT = 0x0031
    SIG_GET_PEER = 0x0032
    SCORE_RECORD = 0x0040
    SCORE_GET_RANGE = 0x0041
    SCORE_GET_BY_ID = 0x0042
    TUS_SET_VAR = 0x0050
    TUS_GET_VAR = 0x0051
    TUS_SET_DATA = 0x0052
    TUS_GET_DATA = 0x0053
    TUS_DELETE = 0x0054
    VLAN_JOIN = 0x0060
    VLAN_LEAVE = 0x0061
    VLAN_LIST = 0x0062
    # Notificacoes servidor -> cliente
    N_FRIEND_STATUS = 0x0100
    N_SIG_REQUEST = 0x0101
    N_MESSAGE = 0x0102
    N_SIG_PEER_UPDATE = 0x0103
    N_VLAN_MEMBER = 0x0104


class Err(enum.IntEnum):
    OK = 0
    MALFORMED = 1
    UNKNOWN_COMMAND = 2
    NOT_LOGGED_IN = 3
    ALREADY_LOGGED_IN = 4
    BAD_VERSION = 5
    NO_SUCH_USER = 6
    WRONG_PASSWORD = 7
    INVALID_ONLINE_ID = 8
    NOT_FOUND = 9
    PEER_OFFLINE = 10
    SERVER_ERROR = 11
    LOGGED_IN_ELSEWHERE = 12
    TOO_LARGE = 13
    ROOM_FULL = 14
    VLAN_DISABLED = 15


class Malformed(Exception):
    pass


class Writer:
    def __init__(self) -> None:
        self.buf = bytearray()

    def u8(self, v: int) -> "Writer":
        self.buf += struct.pack("<B", v)
        return self

    def u16(self, v: int) -> "Writer":
        self.buf += struct.pack("<H", v)
        return self

    def u32(self, v: int) -> "Writer":
        self.buf += struct.pack("<I", v & 0xFFFFFFFF)
        return self

    def i32(self, v: int) -> "Writer":
        self.buf += struct.pack("<i", v)
        return self

    def u64(self, v: int) -> "Writer":
        self.buf += struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)
        return self

    def i64(self, v: int) -> "Writer":
        self.buf += struct.pack("<q", v)
        return self

    def str(self, s: str) -> "Writer":
        b = s.encode("utf-8")
        self.buf += struct.pack("<H", len(b)) + b
        return self

    def blob(self, b: bytes) -> "Writer":
        self.buf += struct.pack("<I", len(b)) + b
        return self

    def ip4(self, ip: str) -> "Writer":
        # IPv4 em ordem de rede (4 bytes), como sockaddr_in.sin_addr.
        self.buf += bytes(int(x) for x in ip.split("."))
        return self

    def bytes(self) -> bytes:
        return bytes(self.buf)


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.off = 0

    def _take(self, n: int) -> bytes:
        if self.off + n > len(self.data):
            raise Malformed(f"faltam {self.off + n - len(self.data)} bytes")
        b = self.data[self.off: self.off + n]
        self.off += n
        return b

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self._take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self._take(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self._take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self._take(8))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self._take(8))[0]

    def str(self) -> str:
        n = self.u16()
        try:
            return self._take(n).decode("utf-8")
        except UnicodeDecodeError as e:
            raise Malformed("utf-8 invalido") from e

    def blob(self) -> bytes:
        n = self.u32()
        if n > MAX_PACKET:
            raise Malformed("blob grande demais")
        return self._take(n)

    def ip4(self) -> str:
        return ".".join(str(b) for b in self._take(4))

    def done(self) -> bool:
        return self.off == len(self.data)


def pack(kind: Kind, cmd: int, req_id: int, body: bytes) -> bytes:
    return HEADER.pack(kind, 0, cmd, HEADER_SIZE + len(body), req_id) + body


def reply(cmd: int, req_id: int, err: Err, body: bytes = b"") -> bytes:
    return pack(Kind.REPLY, cmd, req_id, bytes([err]) + body)


def notify(cmd: int, body: bytes) -> bytes:
    return pack(Kind.NOTIFY, cmd, 0, body)
