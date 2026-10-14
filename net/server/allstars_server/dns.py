"""DNS minimo: responde os hosts do jogo com o IP do servidor substituto.

A biblioteca OTG do jogo nao usa gethostbyname: ela monta consultas DNS e manda por
UDP para a porta 53 do DNS primario que cellNetCtlGetInfo(PRIMARY_DNS) informa
(sceotGetHostUtil, 0x9930F8 no EBOOT 1.00). A HLE do cliente aponta esse DNS para ca.

Regras (config "dns.records"): padrao glob -> IP. "*" no comeco casa qualquer prefixo.
Nomes bloqueados ("dns.blocked") recebem NXDOMAIN. O resto vai para "dns.upstream"
(se configurado) ou recebe NXDOMAIN.
"""
from __future__ import annotations

import asyncio
import fnmatch
import ipaddress
import logging
import struct
from dataclasses import dataclass, field

log = logging.getLogger("dns")

QTYPE_A = 1
QCLASS_IN = 1
RCODE_NXDOMAIN = 3
RCODE_NOTIMP = 4
TTL = 60


@dataclass
class DnsConfig:
    bind_host: str = "0.0.0.0"
    port: int = 53
    records: dict[str, str] = field(default_factory=lambda: {"*.online.scea.com": "127.0.0.1"})
    blocked: list[str] = field(default_factory=lambda: ["*.telemetry.*"])
    upstream: str = ""


def parse_query(data: bytes) -> tuple[int, int, str, int, int, int]:
    """Devolve (id, flags, nome, qtype, qclass, offset_fim_da_pergunta)."""
    if len(data) < 12:
        raise ValueError("curto")
    qid, flags, qd, _an, _ns, _ar = struct.unpack_from("!HHHHHH", data, 0)
    if qd < 1:
        raise ValueError("sem pergunta")
    off, labels = 12, []
    while True:
        if off >= len(data):
            raise ValueError("nome truncado")
        n = data[off]
        off += 1
        if n == 0:
            break
        if n & 0xC0:
            raise ValueError("compressao na pergunta")
        labels.append(data[off: off + n].decode("ascii", "replace"))
        off += n
    qtype, qclass = struct.unpack_from("!HH", data, off)
    return qid, flags, ".".join(labels).lower(), qtype, qclass, off + 4


def build_response(query: bytes, q_end: int, rcode: int, ip: str | None) -> bytes:
    qid, flags = struct.unpack_from("!HH", query, 0)
    rd = flags & 0x0100
    resp_flags = 0x8000 | 0x0400 | rd | 0x0080 | rcode  # QR, AA, RD copiado, RA
    an = 1 if ip else 0
    out = struct.pack("!HHHHHH", qid, resp_flags, 1, an, 0, 0) + query[12:q_end]
    if ip:
        out += struct.pack("!HHHIH", 0xC00C, QTYPE_A, QCLASS_IN, TTL, 4) + ipaddress.IPv4Address(ip).packed
    return out


class DnsServer(asyncio.DatagramProtocol):
    def __init__(self, cfg: DnsConfig):
        self.cfg = cfg
        self.transport = None
        self._pending: dict[tuple[int, str], tuple] = {}

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=(self.cfg.bind_host, self.cfg.port))
        log.info("DNS em udp/%s:%d (%d regras)", self.cfg.bind_host, self.cfg.port, len(self.cfg.records))

    def close(self) -> None:
        if self.transport:
            self.transport.close()

    def connection_made(self, transport):
        self.transport = transport

    def resolve(self, name: str) -> tuple[str, str | None]:
        """('a', ip) | ('nx', None) | ('up', None)"""
        for pat in self.cfg.blocked:
            if fnmatch.fnmatch(name, pat.lower()):
                return "nx", None
        for pat, ip in self.cfg.records.items():
            if fnmatch.fnmatch(name, pat.lower()) or name == pat.lower().lstrip("*.").lstrip("."):
                return "a", ip
        return ("up", None) if self.cfg.upstream else ("nx", None)

    def datagram_received(self, data, addr):
        try:
            qid, flags, name, qtype, qclass, q_end = parse_query(data)
        except (ValueError, struct.error):
            return
        if flags & 0x8000:
            return
        kind, ip = self.resolve(name)
        if kind == "up":
            asyncio.ensure_future(self._forward(data, addr, name))
            return
        if kind == "a" and qtype != QTYPE_A:
            # Nome conhecido sem registro desse tipo (ex.: AAAA): resposta vazia, sem erro.
            resp = build_response(data, q_end, 0, None)
        elif kind == "a":
            resp = build_response(data, q_end, 0, ip)
        else:
            resp = build_response(data, q_end, RCODE_NXDOMAIN, None)
        log.info("%s %s -> %s", addr[0], name, ip or kind)
        self.transport.sendto(resp, addr)

    async def _forward(self, data: bytes, addr, name: str) -> None:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()

        class _Up(asyncio.DatagramProtocol):
            def datagram_received(self, d, a):
                if not fut.done():
                    fut.set_result(d)

        t, _ = await loop.create_datagram_endpoint(_Up, remote_addr=(self.cfg.upstream, 53))
        try:
            t.sendto(data)
            resp = await asyncio.wait_for(fut, 3.0)
            self.transport.sendto(resp, addr)
            log.info("%s %s -> upstream", addr[0], name)
        except asyncio.TimeoutError:
            log.warning("upstream nao respondeu para %s", name)
        finally:
            t.close()
