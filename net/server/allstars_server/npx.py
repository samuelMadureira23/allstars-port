"""Servidor NPX: contas, tickets, presenca, sinalizacao P2P, placares e TUS.

E o substituto do PSN que as HLEs de sceNp/sceNpBasic/sceNpSignaling/sceNpScore/
sceNpTus do cliente nativo usam. Ideia parecida com a do RPCN (TCP com comandos
binarios + UDP para descobrir o endereco publico), mas protocolo e codigo proprios.
"""
from __future__ import annotations

import asyncio
import logging
import os
import struct
import time
from dataclasses import dataclass, field

from . import ticket
from .db import ONLINE_ID_RE, Database
from .vlan import Member, Room, VlanServer
from .wire import (HEADER, HEADER_SIZE, MAX_PACKET, PROTOCOL_VERSION, Cmd, Err, Kind, Malformed,
                   Reader, Writer, notify, reply)

log = logging.getLogger("npx")

UDP_MAGIC = b"NPXP"


@dataclass
class NpxConfig:
    bind_host: str = "0.0.0.0"
    port: int = 32000
    udp_port: int = 32000
    allow_create: bool = True
    everyone_is_friend: bool = True
    ticket_secret: bytes = b""
    ticket_lifetime: int = 3600
    title_ids: tuple[str, ...] = ("BCUS98472", "BCES01765", "BCJS30087", "BCAS20229", "NPUA80800")


@dataclass
class P2PInfo:
    local_ip: str = "0.0.0.0"
    local_port: int = 0
    public_ip: str = "0.0.0.0"
    public_port: int = 0
    updated: float = 0.0


@dataclass
class Session:
    server: "NpxServer"
    writer: asyncio.StreamWriter
    peer: tuple[str, int]
    user_id: int = 0
    online_id: str = ""
    title_id: str = ""
    udp_token: bytes = field(default_factory=lambda: os.urandom(8))
    presence_status: int = 0
    presence_text: str = ""
    presence_data: bytes = b""
    p2p: P2PInfo = field(default_factory=P2PInfo)

    def send(self, data: bytes) -> None:
        if not self.writer.is_closing():
            self.writer.write(data)


class _UdpPing(asyncio.DatagramProtocol):
    """UDP: o cliente manda "NPXP" + token (8) a partir da porta P2P dele; o servidor responde
    "NPXP" + token + ip(4) + porta(u16 LE) com o endereco publico visto e grava na sessao."""

    def __init__(self, server: "NpxServer"):
        self.server = server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) < 12 or data[:4] != UDP_MAGIC:
            return
        token = data[4:12]
        sess = self.server.by_token.get(token)
        if sess is None:
            return
        sess.p2p.public_ip, sess.p2p.public_port = addr[0], addr[1]
        sess.p2p.updated = time.time()
        resp = UDP_MAGIC + token + bytes(int(x) for x in addr[0].split(".")) + struct.pack("<H", addr[1])
        self.transport.sendto(resp, addr)


class NpxServer:
    def __init__(self, cfg: NpxConfig, db: Database, vlan: VlanServer | None = None):
        self.cfg = cfg
        self.db = db
        self.vlan = vlan
        if vlan is not None:
            vlan.on_membership = self._on_vlan_membership
        if not cfg.ticket_secret:
            cfg.ticket_secret = os.urandom(32)
        self.sessions: dict[int, Session] = {}      # user_id -> sessao logada
        self.by_name: dict[str, Session] = {}       # online_id minusculo -> sessao logada
        self.by_token: dict[bytes, Session] = {}
        self._server: asyncio.base_events.Server | None = None
        self._udp = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.cfg.bind_host, self.cfg.port)
        loop = asyncio.get_running_loop()
        self._udp, _ = await loop.create_datagram_endpoint(
            lambda: _UdpPing(self), local_addr=(self.cfg.bind_host, self.cfg.udp_port))
        log.info("NPX em tcp/%s:%d e udp/%d", self.cfg.bind_host, self.cfg.port, self.cfg.udp_port)

    def close(self) -> None:
        if self._server:
            self._server.close()
        if self._udp:
            self._udp.close()

    # -- conexao ----------------------------------------------------------------
    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")[:2]
        sess = Session(self, writer, peer)
        log.info("conexao de %s", peer)
        try:
            while True:
                hdr = await reader.readexactly(HEADER_SIZE)
                kind, _flags, cmd, size, req_id = HEADER.unpack(hdr)
                if size < HEADER_SIZE or size > MAX_PACKET:
                    log.warning("%s: tamanho invalido %d", peer, size)
                    break
                body = await reader.readexactly(size - HEADER_SIZE)
                if kind != Kind.REQUEST:
                    continue
                await self._dispatch(sess, cmd, req_id, body)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        except Exception:
            log.exception("erro na sessao %s", peer)
        finally:
            self._logout(sess)
            writer.close()
            log.info("desconectou %s (%s)", peer, sess.online_id or "-")

    async def _dispatch(self, sess: Session, cmd: int, req_id: int, body: bytes) -> None:
        handler = _HANDLERS.get(cmd)
        if handler is None:
            sess.send(reply(cmd, req_id, Err.UNKNOWN_COMMAND))
            return
        needs_login, fn = handler
        if needs_login and not sess.user_id:
            sess.send(reply(cmd, req_id, Err.NOT_LOGGED_IN))
            return
        r = Reader(body)
        try:
            err, out = fn(self, sess, r)
        except Malformed as e:
            log.warning("%s: comando 0x%04x malformado: %s", sess.peer, cmd, e)
            err, out = Err.MALFORMED, b""
        sess.send(reply(cmd, req_id, err, out))

    def _logout(self, sess: Session) -> None:
        if sess.user_id and self.sessions.get(sess.user_id) is sess:
            if self.vlan is not None:
                self.vlan.leave_all(sess.online_id)
            del self.sessions[sess.user_id]
            self.by_name.pop(sess.online_id.lower(), None)
            self.by_token.pop(sess.udp_token, None)
            self._broadcast_status(sess, online=False)
        sess.user_id = 0

    def _friends_of(self, sess: Session) -> list[Session]:
        if not self.cfg.everyone_is_friend:
            return []
        return [s for s in self.sessions.values() if s is not sess]

    def _broadcast_status(self, sess: Session, online: bool) -> None:
        body = Writer().str(sess.online_id).u8(1 if online else 0).u8(sess.presence_status) \
            .str(sess.presence_text).blob(sess.presence_data).bytes()
        for f in self._friends_of(sess):
            f.send(notify(Cmd.N_FRIEND_STATUS, body))

    # -- comandos -----------------------------------------------------------------
    def c_hello(self, sess: Session, r: Reader):
        version = r.u32()
        sess.title_id = r.str()
        if version != PROTOCOL_VERSION:
            return Err.BAD_VERSION, Writer().u32(PROTOCOL_VERSION).bytes()
        w = Writer().u32(PROTOCOL_VERSION).ip4(sess.peer[0]).u16(sess.peer[1]).u64(int(time.time() * 1000))
        return Err.OK, w.bytes()

    def c_login(self, sess: Session, r: Reader):
        online_id, password = r.str(), r.str()
        create = r.u8()
        if sess.user_id:
            return Err.ALREADY_LOGGED_IN, b""
        if not ONLINE_ID_RE.match(online_id):
            return Err.INVALID_ONLINE_ID, b""
        acc = self.db.get_account(online_id)
        if acc is None:
            if not (create and self.cfg.allow_create):
                return Err.NO_SUCH_USER, b""
            acc = self.db.create_account(online_id, password)
            log.info("conta criada: %s", online_id)
        elif not self.db.check_password(online_id, password):
            return Err.WRONG_PASSWORD, b""
        if acc.banned:
            return Err.WRONG_PASSWORD, b""
        old = self.sessions.get(acc.user_id)
        if old is not None:
            # Login novo derruba o antigo (o jogo pode ter reiniciado).
            self._logout(old)
            old.writer.close()
        sess.user_id, sess.online_id = acc.user_id, acc.online_id
        self.sessions[acc.user_id] = sess
        self.by_name[acc.online_id.lower()] = sess
        self.by_token[sess.udp_token] = sess
        self.db.touch_login(acc.user_id)
        self._broadcast_status(sess, online=True)
        log.info("login %s (uid %d) de %s", acc.online_id, acc.user_id, sess.peer)
        w = Writer().u64(acc.user_id).str(acc.online_id).blob(sess.udp_token).ip4(sess.peer[0])
        return Err.OK, w.bytes()

    def c_logout(self, sess: Session, r: Reader):
        self._logout(sess)
        return Err.OK, b""

    def c_ping(self, sess: Session, r: Reader):
        return Err.OK, Writer().u64(int(time.time() * 1000)).bytes()

    def c_get_ticket(self, sess: Session, r: Reader):
        service_id = r.str()
        cookie = r.blob()
        t = ticket.build_ticket(self.cfg.ticket_secret, sess.user_id, sess.online_id, service_id,
                                lifetime=self.cfg.ticket_lifetime, cookie=cookie)
        return Err.OK, Writer().blob(t).bytes()

    def c_lookup(self, sess: Session, r: Reader):
        acc = self.db.get_account(r.str())
        if acc is None:
            return Err.NOT_FOUND, b""
        return Err.OK, Writer().u64(acc.user_id).str(acc.online_id).bytes()

    def c_set_presence(self, sess: Session, r: Reader):
        sess.presence_status = r.u8()
        sess.presence_text = r.str()
        sess.presence_data = r.blob()
        self._broadcast_status(sess, online=True)
        return Err.OK, b""

    def c_get_friends(self, sess: Session, r: Reader):
        friends = self._friends_of(sess)
        w = Writer().u16(len(friends))
        for f in friends:
            w.str(f.online_id).u8(1).u8(f.presence_status).str(f.presence_text).blob(f.presence_data)
        return Err.OK, w.bytes()

    def c_send_message(self, sess: Session, r: Reader):
        to = r.str()
        main_type, sub_type = r.u16(), r.u16()
        subject, text, data = r.str(), r.str(), r.blob()
        target = self._session_by_name(to)
        if target is None:
            return Err.PEER_OFFLINE, b""
        target.send(notify(Cmd.N_MESSAGE, Writer().str(sess.online_id).u16(main_type).u16(sub_type)
                           .str(subject).str(text).blob(data).bytes()))
        return Err.OK, b""

    def _session_by_name(self, online_id: str) -> Session | None:
        return self.by_name.get(online_id.lower())

    # sinalizacao: troca de enderecos para hole punching; TURN e o fallback.
    def c_sig_register(self, sess: Session, r: Reader):
        sess.p2p.local_ip = r.ip4()
        sess.p2p.local_port = r.u16()
        return Err.OK, Writer().blob(sess.udp_token).bytes()

    def _p2p_body(self, s: Session, conn_id: int) -> bytes:
        p = s.p2p
        return Writer().u32(conn_id).str(s.online_id).ip4(p.public_ip).u16(p.public_port) \
            .ip4(p.local_ip).u16(p.local_port).bytes()

    def c_sig_connect(self, sess: Session, r: Reader):
        target_name = r.str()
        conn_id = r.u32()
        target = self._session_by_name(target_name)
        if target is None:
            return Err.PEER_OFFLINE, b""
        target.send(notify(Cmd.N_SIG_REQUEST, self._p2p_body(sess, conn_id)))
        return Err.OK, self._p2p_body(target, conn_id)

    def c_sig_get_peer(self, sess: Session, r: Reader):
        target = self._session_by_name(r.str())
        if target is None:
            return Err.PEER_OFFLINE, b""
        return Err.OK, self._p2p_body(target, 0)

    # placares
    def c_score_record(self, sess: Session, r: Reader):
        board, pcid = r.u32(), r.u32()
        score = r.i64()
        comment, game_info = r.str(), r.blob()
        higher = r.u8()
        rank, written = self.db.record_score(board, sess.user_id, pcid, score, comment, game_info, bool(higher))
        return Err.OK, Writer().u32(rank).u8(1 if written else 0).bytes()

    @staticmethod
    def _score_entry(w: Writer, e: tuple) -> None:
        rank, online_id, pcid, score, comment, game_info, updated = e
        w.u32(rank).str(online_id).u32(pcid).i64(score).str(comment).blob(game_info).u64(updated)

    def c_score_range(self, sess: Session, r: Reader):
        board, start, count = r.u32(), r.u32(), r.u16()
        total, entries = self.db.score_range(board, max(1, start), min(count, 100))
        w = Writer().u32(total).u16(len(entries))
        for e in entries:
            self._score_entry(w, e)
        return Err.OK, w.bytes()

    def c_score_by_id(self, sess: Session, r: Reader):
        board, pcid = r.u32(), r.u32()
        n = r.u16()
        names = [r.str() for _ in range(min(n, 100))]
        total = self.db.score_range(board, 1, 0)[0]
        w = Writer().u32(total).u16(len(names))
        for name in names:
            e = self.db.score_of(board, name, pcid)
            w.u8(1 if e else 0)
            if e:
                self._score_entry(w, e)
        return Err.OK, w.bytes()

    # TUS: dono e o online id (vazio = o proprio jogador)
    def _tus_owner(self, sess: Session, name: str) -> int | None:
        if not name:
            return sess.user_id
        acc = self.db.get_account(name)
        return acc.user_id if acc else None

    def c_tus_set_var(self, sess: Session, r: Reader):
        owner = self._tus_owner(sess, r.str())
        slot, value = r.i32(), r.i64()
        if owner is None:
            return Err.NOT_FOUND, b""
        self.db.tus_set_var(owner, slot, value, sess.user_id)
        return Err.OK, b""

    def c_tus_get_var(self, sess: Session, r: Reader):
        owner = self._tus_owner(sess, r.str())
        slot = r.i32()
        if owner is None:
            return Err.NOT_FOUND, b""
        row = self.db.tus_get_var(owner, slot)
        if row is None:
            return Err.OK, Writer().u8(0).bytes()
        return Err.OK, Writer().u8(1).i64(row[0]).u64(row[1]).u64(row[2]).bytes()

    def c_tus_set_data(self, sess: Session, r: Reader):
        owner = self._tus_owner(sess, r.str())
        slot = r.i32()
        data, info = r.blob(), r.blob()
        if owner is None:
            return Err.NOT_FOUND, b""
        if len(data) > 256 * 1024:
            return Err.TOO_LARGE, b""
        self.db.tus_set_data(owner, slot, data, info, sess.user_id)
        return Err.OK, b""

    def c_tus_get_data(self, sess: Session, r: Reader):
        owner = self._tus_owner(sess, r.str())
        slot = r.i32()
        if owner is None:
            return Err.NOT_FOUND, b""
        row = self.db.tus_get_data(owner, slot)
        if row is None:
            return Err.OK, Writer().u8(0).bytes()
        return Err.OK, Writer().u8(1).blob(row[0]).blob(row[1]).u64(row[2]).u64(row[3]).bytes()

    def c_tus_delete(self, sess: Session, r: Reader):
        owner = self._tus_owner(sess, r.str())
        slot = r.i32()
        if owner is None:
            return Err.NOT_FOUND, b""
        self.db.tus_delete(owner, slot)
        return Err.OK, b""

    # LAN virtual (modo "Network Versus")
    def _on_vlan_membership(self, room: Room, m: Member, joined: bool) -> None:
        body = Writer().str(room.name).str(m.online_id).ip4(m.vip).u8(1 if joined else 0).bytes()
        for other in room.members.values():
            if other is m:
                continue
            s = self._session_by_name(other.online_id)
            if s is not None:
                s.send(notify(Cmd.N_VLAN_MEMBER, body))

    def c_vlan_join(self, sess: Session, r: Reader):
        room_name = r.str()
        local_ip, local_port = r.ip4(), r.u16()
        if self.vlan is None:
            return Err.VLAN_DISABLED, b""
        if not room_name or len(room_name) > 32:
            return Err.MALFORMED, b""
        res = self.vlan.join(room_name, sess.online_id, (local_ip, local_port))
        if res is None:
            return Err.ROOM_FULL, b""
        room, m = res
        w = Writer().ip4(m.vip).ip4("255.255.255.0").ip4(room.broadcast).blob(m.token) \
            .u16(self.vlan.cfg.udp_port).u16(len(room.members) - 1)
        for other in room.members.values():
            if other is not m:
                w.str(other.online_id).ip4(other.vip)
        return Err.OK, w.bytes()

    def c_vlan_leave(self, sess: Session, r: Reader):
        if self.vlan is not None:
            self.vlan.leave_all(sess.online_id)
        return Err.OK, b""

    def c_vlan_list(self, sess: Session, r: Reader):
        if self.vlan is None:
            return Err.VLAN_DISABLED, b""
        rooms = list(self.vlan.rooms.values())
        w = Writer().u16(len(rooms))
        for room in rooms:
            w.str(room.name).u8(len(room.members)).u8(self.vlan.cfg.max_members)
        return Err.OK, w.bytes()


# comando -> (exige login, metodo)
_HANDLERS = {
    Cmd.HELLO: (False, NpxServer.c_hello),
    Cmd.LOGIN: (False, NpxServer.c_login),
    Cmd.LOGOUT: (True, NpxServer.c_logout),
    Cmd.PING: (False, NpxServer.c_ping),
    Cmd.GET_TICKET: (True, NpxServer.c_get_ticket),
    Cmd.LOOKUP_ONLINE_ID: (True, NpxServer.c_lookup),
    Cmd.SET_PRESENCE: (True, NpxServer.c_set_presence),
    Cmd.GET_FRIENDS: (True, NpxServer.c_get_friends),
    Cmd.SEND_MESSAGE: (True, NpxServer.c_send_message),
    Cmd.SIG_REGISTER: (True, NpxServer.c_sig_register),
    Cmd.SIG_CONNECT: (True, NpxServer.c_sig_connect),
    Cmd.SIG_GET_PEER: (True, NpxServer.c_sig_get_peer),
    Cmd.SCORE_RECORD: (True, NpxServer.c_score_record),
    Cmd.SCORE_GET_RANGE: (True, NpxServer.c_score_range),
    Cmd.SCORE_GET_BY_ID: (True, NpxServer.c_score_by_id),
    Cmd.TUS_SET_VAR: (True, NpxServer.c_tus_set_var),
    Cmd.TUS_GET_VAR: (True, NpxServer.c_tus_get_var),
    Cmd.TUS_SET_DATA: (True, NpxServer.c_tus_set_data),
    Cmd.TUS_GET_DATA: (True, NpxServer.c_tus_get_data),
    Cmd.TUS_DELETE: (True, NpxServer.c_tus_delete),
    Cmd.VLAN_JOIN: (True, NpxServer.c_vlan_join),
    Cmd.VLAN_LEAVE: (True, NpxServer.c_vlan_leave),
    Cmd.VLAN_LIST: (True, NpxServer.c_vlan_list),
}
