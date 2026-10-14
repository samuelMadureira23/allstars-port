"""Servidor STUN + TURN (RFC 5389 / RFC 5766) sobre UDP, so com asyncio.

Substitui battleroyale-final.turn1/turn2 e o "Crossplay STUN". Cobre o que um
cliente TURN normal usa: Binding, Allocate, Refresh, CreatePermission,
ChannelBind, Send/Data indication e ChannelData. TCP/TLS para o cliente e
alocacoes TCP (RFC 6062) ficam de fora ate a engenharia reversa mostrar que o
jogo precisa.

Autenticacao (config "turn.auth"):
  - "none": aceita tudo sem MESSAGE-INTEGRITY (cliente que nao manda credencial).
  - "any": desafia com 401 + REALM/NONCE e aceita qualquer usuario; se o usuario
    estiver em "turn.users" confere a senha, senao responde sem integridade.
  - "longterm": so usuarios de "turn.users", com senha conferida.
"""
from __future__ import annotations

import asyncio
import logging
import os
import struct
import time
from dataclasses import dataclass, field

from . import stun
from .stun import Message

log = logging.getLogger("turn")

DEFAULT_LIFETIME = 600
MAX_LIFETIME = 3600
PERMISSION_LIFETIME = 300
CHANNEL_LIFETIME = 600
NONCE_LIFETIME = 3600
SOFTWARE = b"allstars-server turn"


@dataclass
class TurnConfig:
    bind_host: str = "0.0.0.0"
    port: int = 3478
    # Endereco que os clientes enxergam para as portas de relay (IP publico do servidor).
    relay_public_ip: str = "127.0.0.1"
    relay_bind_host: str = "0.0.0.0"
    relay_port_min: int = 49160
    relay_port_max: int = 49400
    realm: str = "allstars"
    auth: str = "any"
    users: dict[str, str] = field(default_factory=dict)
    max_allocations_per_ip: int = 16


class _RelayProtocol(asyncio.DatagramProtocol):
    def __init__(self, alloc: "Allocation"):
        self.alloc = alloc
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.alloc.on_peer_data(data, (addr[0], addr[1]))


@dataclass
class Allocation:
    server: "TurnServer"
    client: tuple[str, int]
    username: str
    key: bytes | None
    expires: float
    relay_port: int = 0
    relay: _RelayProtocol | None = None
    permissions: dict[str, float] = field(default_factory=dict)
    # canal -> (peer, expira) e peer -> canal
    channels: dict[int, tuple[tuple[str, int], float]] = field(default_factory=dict)
    peer_channels: dict[tuple[str, int], int] = field(default_factory=dict)
    bytes_up: int = 0
    bytes_down: int = 0

    def has_permission(self, ip: str) -> bool:
        exp = self.permissions.get(ip)
        return exp is not None and exp > time.monotonic()

    def send_to_peer(self, peer: tuple[str, int], data: bytes) -> None:
        if not self.has_permission(peer[0]) or self.relay is None or self.relay.transport is None:
            return
        self.bytes_up += len(data)
        self.relay.transport.sendto(data, peer)

    def on_peer_data(self, data: bytes, peer: tuple[str, int]) -> None:
        if not self.has_permission(peer[0]):
            return
        self.bytes_down += len(data)
        ch = self.peer_channels.get(peer)
        now = time.monotonic()
        if ch is not None and self.channels.get(ch, (None, 0))[1] > now:
            pad = (-len(data)) % 4
            pkt = struct.pack("!HH", ch, len(data)) + data + b"\x00" * pad
        else:
            ind = Message(stun.DATA, stun.CLASS_INDICATION)
            ind.add_xor_address(stun.XOR_PEER_ADDRESS, peer)
            ind.add(stun.DATA_ATTR, data)
            pkt = ind.encode()
        self.server.sendto(pkt, self.client)

    def close(self) -> None:
        if self.relay and self.relay.transport:
            self.relay.transport.close()
        self.relay = None


class TurnServer(asyncio.DatagramProtocol):
    def __init__(self, cfg: TurnConfig):
        self.cfg = cfg
        self.transport: asyncio.DatagramTransport | None = None
        self.allocations: dict[tuple[str, int], Allocation] = {}
        self._nonce_secret = os.urandom(16)
        self._next_port = cfg.relay_port_min
        self._used_ports: set[int] = set()
        self._gc_task: asyncio.Task | None = None

    # -- ciclo de vida ------------------------------------------------------
    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=(self.cfg.bind_host, self.cfg.port))
        self._gc_task = asyncio.create_task(self._gc_loop())
        log.info("STUN/TURN em udp/%s:%d (relay %s:%d-%d, auth=%s)", self.cfg.bind_host, self.cfg.port,
                 self.cfg.relay_public_ip, self.cfg.relay_port_min, self.cfg.relay_port_max, self.cfg.auth)

    def close(self) -> None:
        if self._gc_task:
            self._gc_task.cancel()
        for a in list(self.allocations.values()):
            a.close()
        self.allocations.clear()
        if self.transport:
            self.transport.close()

    def connection_made(self, transport):
        self.transport = transport

    def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.transport:
            self.transport.sendto(data, addr)

    async def _gc_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            now = time.monotonic()
            for client, alloc in list(self.allocations.items()):
                if alloc.expires <= now:
                    log.info("alocacao de %s expirou (up=%d down=%d)", client, alloc.bytes_up, alloc.bytes_down)
                    self._free(alloc)
                    continue
                alloc.permissions = {ip: e for ip, e in alloc.permissions.items() if e > now}
                for ch, (peer, e) in list(alloc.channels.items()):
                    if e <= now:
                        del alloc.channels[ch]
                        alloc.peer_channels.pop(peer, None)

    # -- recebimento --------------------------------------------------------
    def datagram_received(self, data, addr):
        addr = (addr[0], addr[1])
        try:
            if stun.is_channel_data(data):
                self._on_channel_data(data, addr)
            elif stun.is_stun(data):
                self._on_stun(Message.decode(data), addr)
        except stun.StunError as e:
            log.debug("pacote invalido de %s: %s", addr, e)
        except Exception:
            log.exception("erro tratando pacote de %s", addr)

    def _on_channel_data(self, data: bytes, addr) -> None:
        alloc = self.allocations.get(addr)
        if alloc is None:
            return
        ch, ln = struct.unpack_from("!HH", data, 0)
        entry = alloc.channels.get(ch)
        if entry is None or len(data) < 4 + ln:
            return
        alloc.send_to_peer(entry[0], data[4: 4 + ln])

    def _on_stun(self, msg: Message, addr) -> None:
        if msg.cls == stun.CLASS_INDICATION:
            if msg.method == stun.SEND:
                self._on_send_indication(msg, addr)
            return
        if msg.cls != stun.CLASS_REQUEST:
            return
        unknown = msg.unknown_required()
        if unknown:
            resp = stun.reply_to(msg, False).add_error(420)
            resp.add(stun.UNKNOWN_ATTRIBUTES, b"".join(struct.pack("!H", u) for u in unknown))
            self._send(resp, addr, None)
            return
        if msg.method == stun.BINDING:
            resp = stun.reply_to(msg)
            resp.add_xor_address(stun.XOR_MAPPED_ADDRESS, addr)
            resp.add(stun.MAPPED_ADDRESS, stun.encode_plain_address(addr))
            self._send(resp, addr, None)
            return
        handler = {
            stun.ALLOCATE: self._on_allocate,
            stun.REFRESH: self._on_refresh,
            stun.CREATE_PERMISSION: self._on_create_permission,
            stun.CHANNEL_BIND: self._on_channel_bind,
        }.get(msg.method)
        if handler is None:
            self._send(stun.reply_to(msg, False).add_error(400), addr, None)
            return
        ok, key, username = self._authenticate(msg, addr)
        if not ok:
            return
        handler(msg, addr, key, username)

    # -- autenticacao -------------------------------------------------------
    def _nonce(self) -> bytes:
        ts = int(time.time())
        mac = stun.hmac.new(self._nonce_secret, str(ts).encode(), stun.hashlib.sha1).hexdigest()[:16]
        return f"{ts:x}-{mac}".encode()

    def _nonce_valid(self, nonce: bytes) -> bool:
        try:
            ts_hex, mac = nonce.decode().split("-", 1)
            ts = int(ts_hex, 16)
        except ValueError:
            return False
        good = stun.hmac.new(self._nonce_secret, str(ts).encode(), stun.hashlib.sha1).hexdigest()[:16]
        return stun.hmac.compare_digest(good, mac) and time.time() - ts < NONCE_LIFETIME

    def _challenge(self, msg: Message, addr, code: int) -> None:
        resp = stun.reply_to(msg, False).add_error(code)
        resp.add(stun.REALM, self.cfg.realm.encode())
        resp.add(stun.NONCE, self._nonce())
        self._send(resp, addr, None)

    def _authenticate(self, msg: Message, addr) -> tuple[bool, bytes | None, str]:
        mode = self.cfg.auth
        if mode == "none":
            return True, None, ""
        username_b = msg.get(stun.USERNAME)
        if msg.get(stun.MESSAGE_INTEGRITY) is None or username_b is None:
            self._challenge(msg, addr, 401)
            return False, None, ""
        nonce = msg.get(stun.NONCE) or b""
        if not self._nonce_valid(nonce):
            self._challenge(msg, addr, 438)
            return False, None, ""
        username = username_b.decode(errors="replace")
        realm = (msg.get(stun.REALM) or self.cfg.realm.encode()).decode(errors="replace")
        password = self.cfg.users.get(username)
        if password is None:
            if mode == "any":
                # Nao temos a senha: aceita e responde sem MESSAGE-INTEGRITY.
                return True, None, username
            self._challenge(msg, addr, 401)
            return False, None, ""
        key = stun.long_term_key(username, realm, password)
        if not msg.check_integrity(key):
            self._challenge(msg, addr, 401)
            return False, None, ""
        return True, key, username

    def _send(self, msg: Message, addr, key: bytes | None) -> None:
        msg.add(stun.SOFTWARE, SOFTWARE)
        self.sendto(msg.encode(integrity_key=key, fingerprint=True), addr)

    # -- metodos TURN -------------------------------------------------------
    def _lifetime(self, msg: Message) -> int:
        v = msg.get(stun.LIFETIME)
        if v is None or len(v) != 4:
            return DEFAULT_LIFETIME
        return min(struct.unpack("!I", v)[0], MAX_LIFETIME)

    def _alloc_port(self) -> int | None:
        span = self.cfg.relay_port_max - self.cfg.relay_port_min + 1
        for _ in range(span):
            p = self._next_port
            self._next_port = self.cfg.relay_port_min + ((p + 1 - self.cfg.relay_port_min) % span)
            if p not in self._used_ports:
                return p
        return None

    def _free(self, alloc: Allocation) -> None:
        alloc.close()
        self._used_ports.discard(alloc.relay_port)
        self.allocations.pop(alloc.client, None)

    def _on_allocate(self, msg: Message, addr, key, username) -> None:
        existing = self.allocations.get(addr)
        if existing is not None:
            # Retransmissao da mesma requisicao: devolve a mesma alocacao.
            resp = stun.reply_to(msg)
            resp.add_xor_address(stun.XOR_RELAYED_ADDRESS, (self.cfg.relay_public_ip, existing.relay_port))
            resp.add_xor_address(stun.XOR_MAPPED_ADDRESS, addr)
            resp.add(stun.LIFETIME, struct.pack("!I", max(0, int(existing.expires - time.monotonic()))))
            if existing.username != username:
                resp = stun.reply_to(msg, False).add_error(437)
            self._send(resp, addr, key)
            return
        transport = msg.get(stun.REQUESTED_TRANSPORT)
        if transport is None:
            self._send(stun.reply_to(msg, False).add_error(400), addr, key)
            return
        if transport[0] != 17:
            self._send(stun.reply_to(msg, False).add_error(442), addr, key)
            return
        fam = msg.get(stun.REQUESTED_ADDRESS_FAMILY)
        if fam is not None and fam[0] != 0x01:
            self._send(stun.reply_to(msg, False).add_error(440), addr, key)
            return
        per_ip = sum(1 for c in self.allocations if c[0] == addr[0])
        if per_ip >= self.cfg.max_allocations_per_ip:
            self._send(stun.reply_to(msg, False).add_error(486), addr, key)
            return
        lifetime = self._lifetime(msg) or DEFAULT_LIFETIME
        alloc = Allocation(self, addr, username, key, time.monotonic() + lifetime)
        # Reserva sincrona da porta; o socket de relay abre em seguida.
        port = self._alloc_port()
        if port is None:
            self._send(stun.reply_to(msg, False).add_error(508), addr, key)
            return
        self._used_ports.add(port)
        alloc.relay_port = port
        self.allocations[addr] = alloc
        asyncio.ensure_future(self._open_relay(alloc, msg, addr, key, lifetime))

    async def _open_relay(self, alloc: Allocation, msg: Message, addr, key, lifetime: int) -> None:
        loop = asyncio.get_running_loop()
        try:
            _, proto = await loop.create_datagram_endpoint(
                lambda: _RelayProtocol(alloc), local_addr=(self.cfg.relay_bind_host, alloc.relay_port))
        except OSError as e:
            log.warning("porta de relay %d indisponivel: %s", alloc.relay_port, e)
            self._free(alloc)
            self._send(stun.reply_to(msg, False).add_error(508), addr, key)
            return
        alloc.relay = proto
        log.info("alocacao %s -> relay %s:%d (%ds, usuario=%r)", addr, self.cfg.relay_public_ip,
                 alloc.relay_port, lifetime, alloc.username)
        resp = stun.reply_to(msg)
        resp.add_xor_address(stun.XOR_RELAYED_ADDRESS, (self.cfg.relay_public_ip, alloc.relay_port))
        resp.add_xor_address(stun.XOR_MAPPED_ADDRESS, addr)
        resp.add(stun.LIFETIME, struct.pack("!I", lifetime))
        self._send(resp, addr, key)

    def _get_alloc(self, msg: Message, addr, key) -> Allocation | None:
        alloc = self.allocations.get(addr)
        if alloc is None:
            self._send(stun.reply_to(msg, False).add_error(437), addr, key)
        return alloc

    def _on_refresh(self, msg: Message, addr, key, username) -> None:
        alloc = self._get_alloc(msg, addr, key)
        if alloc is None:
            return
        lifetime = self._lifetime(msg)
        if lifetime == 0:
            self._free(alloc)
        else:
            alloc.expires = time.monotonic() + lifetime
        resp = stun.reply_to(msg).add(stun.LIFETIME, struct.pack("!I", lifetime))
        self._send(resp, addr, key)

    def _on_create_permission(self, msg: Message, addr, key, username) -> None:
        alloc = self._get_alloc(msg, addr, key)
        if alloc is None:
            return
        peers = [v for t, v in msg.attrs if t == stun.XOR_PEER_ADDRESS]
        if not peers:
            self._send(stun.reply_to(msg, False).add_error(400), addr, key)
            return
        exp = time.monotonic() + PERMISSION_LIFETIME
        for v in peers:
            ip, _ = stun.decode_xor_address(v, msg.transaction_id)
            alloc.permissions[ip] = exp
        self._send(stun.reply_to(msg), addr, key)

    def _on_channel_bind(self, msg: Message, addr, key, username) -> None:
        alloc = self._get_alloc(msg, addr, key)
        if alloc is None:
            return
        chv = msg.get(stun.CHANNEL_NUMBER)
        peer = msg.get_xor_address(stun.XOR_PEER_ADDRESS)
        if chv is None or len(chv) < 2 or peer is None:
            self._send(stun.reply_to(msg, False).add_error(400), addr, key)
            return
        ch = struct.unpack_from("!H", chv)[0]
        if not 0x4000 <= ch <= 0x7FFE:
            self._send(stun.reply_to(msg, False).add_error(400), addr, key)
            return
        bound = alloc.channels.get(ch)
        other = alloc.peer_channels.get(peer)
        if (bound is not None and bound[0] != peer) or (other is not None and other != ch):
            self._send(stun.reply_to(msg, False).add_error(400), addr, key)
            return
        now = time.monotonic()
        alloc.channels[ch] = (peer, now + CHANNEL_LIFETIME)
        alloc.peer_channels[peer] = ch
        alloc.permissions[peer[0]] = now + PERMISSION_LIFETIME
        self._send(stun.reply_to(msg), addr, key)

    def _on_send_indication(self, msg: Message, addr) -> None:
        alloc = self.allocations.get(addr)
        if alloc is None:
            return
        peer = msg.get_xor_address(stun.XOR_PEER_ADDRESS)
        data = msg.get(stun.DATA_ATTR)
        if peer is None or data is None:
            return
        alloc.send_to_peer(peer, data)
