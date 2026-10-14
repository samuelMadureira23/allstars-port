"""LAN virtual para o modo escondido "Network Versus" do jogo.

O modo LAN do jogo acha partidas por broadcast UDP (sockets DGRAM_P2P, porta 3658,
vport 1000). O cliente nativo entra numa sala (comando NPX VLAN_JOIN), recebe um IP
virtual 10.77.x.y e passa a mandar todo pacote destinado a esse /24 ou a
255.255.255.255 pelo tunel UDP deste modulo. O servidor repassa broadcast para a sala
inteira e unicast para o membro dono do IP virtual. Os clientes tentam tambem o
caminho direto entre si (hole punching) com a tabela de pares que o servidor envia;
o servidor fica como relay de fallback.

Pacote do tunel (little-endian), cabecalho de 12 bytes:
    "AV" | u8 type | u8 flags | token[8]   (token = zeros no sentido servidor->cliente e entre pares)
    type 1 KEEPALIVE  cliente->servidor: so o cabecalho. Resposta: cabecalho + ip4 publico + u16 porta
                      + u8 n + n x (ip4 vip, ip4 ip_pub, u16 porta_pub, ip4 ip_local, u16 porta_local)
    type 2 DATA       cabecalho + ip4 src_vip + ip4 dst_vip + u8 proto (0 udp, 1 p2p)
                      + u16 src_port + u16 dst_port + u16 src_vport + u16 dst_vport + payload
    type 3 PUNCH / 4 PUNCH_ACK (so entre pares): cabecalho + ip4 vip de quem manda
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import struct
import time
from dataclasses import dataclass, field

log = logging.getLogger("vlan")

MAGIC = b"AV"
HDR = struct.Struct("<2sBB8s")
DATA_HDR = struct.Struct("<4s4sBHHHH")
T_KEEPALIVE, T_DATA, T_PUNCH, T_PUNCH_ACK = 1, 2, 3, 4
ZERO_TOKEN = b"\x00" * 8
MEMBER_TIMEOUT = 60.0


@dataclass
class VlanConfig:
    udp_port: int = 32001
    subnet: str = "10.77.0.0/16"
    max_members: int = 8


def _ip4(s: str) -> bytes:
    return ipaddress.IPv4Address(s).packed


@dataclass
class Member:
    online_id: str
    vip: str
    token: bytes
    local: tuple[str, int]
    endpoint: tuple[str, int] | None = None
    last_seen: float = field(default_factory=time.monotonic)
    relayed_bytes: int = 0


@dataclass
class Room:
    name: str
    index: int
    base: int  # endereco de rede do /24 da sala
    members: dict[str, Member] = field(default_factory=dict)  # vip -> membro

    @property
    def broadcast(self) -> str:
        return str(ipaddress.IPv4Address(self.base + 255))


class VlanServer(asyncio.DatagramProtocol):
    def __init__(self, cfg: VlanConfig, bind_host: str = "0.0.0.0"):
        self.cfg = cfg
        self.bind_host = bind_host
        self.net = ipaddress.IPv4Network(cfg.subnet)
        self.rooms: dict[str, Room] = {}
        self.by_token: dict[bytes, tuple[Room, Member]] = {}
        self.transport: asyncio.DatagramTransport | None = None
        self._gc: asyncio.Task | None = None
        # callback(room, member, joined) para o NPX notificar os outros membros
        self.on_membership = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=(self.bind_host, self.cfg.udp_port))
        self._gc = asyncio.create_task(self._gc_loop())
        log.info("LAN virtual em udp/%s:%d (sub-rede %s)", self.bind_host, self.cfg.udp_port, self.cfg.subnet)

    def close(self) -> None:
        if self._gc:
            self._gc.cancel()
        if self.transport:
            self.transport.close()

    def connection_made(self, transport):
        self.transport = transport

    # -- salas ----------------------------------------------------------------
    def _room_base(self, index: int) -> int:
        # Cada sala ganha um /24 dentro da sub-rede: 10.77.<index>.0/24
        return int(self.net.network_address) + (index << 8)

    def join(self, room_name: str, online_id: str, local: tuple[str, int]) -> tuple[Room, Member] | None:
        # Um jogador fica em uma sala so; sair antes evita reaproveitar uma sala ja descartada.
        self.leave_all(online_id)
        room = self.rooms.get(room_name)
        if room is None:
            used = {r.index for r in self.rooms.values()}
            limit = max(1, self.net.num_addresses >> 8)
            index = next((i for i in range(limit) if i not in used), None)
            if index is None:
                return None
            room = self.rooms[room_name] = Room(room_name, index, self._room_base(index))
        if len(room.members) >= self.cfg.max_members:
            return None
        host = next(h for h in range(1, 255) if str(ipaddress.IPv4Address(room.base + h)) not in room.members)
        vip = str(ipaddress.IPv4Address(room.base + host))
        m = Member(online_id, vip, os.urandom(8), local)
        room.members[vip] = m
        self.by_token[m.token] = (room, m)
        log.info("%s entrou na sala %r como %s", online_id, room_name, vip)
        if self.on_membership:
            self.on_membership(room, m, True)
        return room, m

    def leave(self, room: Room, m: Member) -> None:
        if room.members.get(m.vip) is not m:
            return
        del room.members[m.vip]
        self.by_token.pop(m.token, None)
        log.info("%s saiu da sala %r", m.online_id, room.name)
        if self.on_membership:
            self.on_membership(room, m, False)
        if not room.members:
            self.rooms.pop(room.name, None)

    def leave_all(self, online_id: str) -> None:
        for room in list(self.rooms.values()):
            for m in list(room.members.values()):
                if m.online_id == online_id:
                    self.leave(room, m)

    async def _gc_loop(self) -> None:
        while True:
            await asyncio.sleep(10)
            now = time.monotonic()
            for room in list(self.rooms.values()):
                for m in list(room.members.values()):
                    if now - m.last_seen > MEMBER_TIMEOUT:
                        log.info("%s sem keepalive, removido de %r", m.online_id, room.name)
                        self.leave(room, m)

    # -- tunel ----------------------------------------------------------------
    def peer_table(self, room: Room, exclude: Member | None) -> bytes:
        rows = [m for m in room.members.values() if m is not exclude]
        out = bytearray([len(rows)])
        for m in rows:
            ep = m.endpoint or ("0.0.0.0", 0)
            out += _ip4(m.vip) + _ip4(ep[0]) + struct.pack("<H", ep[1]) + _ip4(m.local[0]) + struct.pack("<H", m.local[1])
        return bytes(out)

    def datagram_received(self, data, addr):
        if len(data) < HDR.size:
            return
        magic, ptype, _flags, token = HDR.unpack_from(data)
        if magic != MAGIC:
            return
        entry = self.by_token.get(token)
        if entry is None:
            return
        room, m = entry
        m.endpoint = (addr[0], addr[1])
        m.last_seen = time.monotonic()
        if ptype == T_KEEPALIVE:
            body = _ip4(addr[0]) + struct.pack("<H", addr[1]) + self.peer_table(room, m)
            self.transport.sendto(HDR.pack(MAGIC, T_KEEPALIVE, 0, ZERO_TOKEN) + body, addr)
        elif ptype == T_DATA and len(data) >= HDR.size + DATA_HDR.size:
            self._relay(room, m, data)

    def _relay(self, room: Room, src: Member, data: bytes) -> None:
        _src_vip, dst_vip, proto, sp, dp, svp, dvp = DATA_HDR.unpack_from(data, HDR.size)
        payload = data[HDR.size + DATA_HDR.size:]
        # O servidor reescreve o IP de origem: ninguem se passa por outro membro.
        out = HDR.pack(MAGIC, T_DATA, 0, ZERO_TOKEN) + DATA_HDR.pack(
            _ip4(src.vip), dst_vip, proto, sp, dp, svp, dvp) + payload
        dst = str(ipaddress.IPv4Address(dst_vip))
        if dst == "255.255.255.255" or dst == room.broadcast:
            targets = [m for m in room.members.values() if m is not src]
        else:
            t = room.members.get(dst)
            targets = [t] if t is not None and t is not src else []
        for t in targets:
            if t.endpoint is not None:
                self.transport.sendto(out, t.endpoint)
                src.relayed_bytes += len(payload)
