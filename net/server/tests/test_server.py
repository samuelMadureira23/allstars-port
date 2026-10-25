"""Testes do servidor substituto. Rodar em net/server: python -m unittest discover -s tests -v"""
from __future__ import annotations

import asyncio
import os
import socket
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from allstars_server import stun, ticket  # noqa: E402
from allstars_server.client import NpxClient, NpxError  # noqa: E402
from allstars_server.db import Database  # noqa: E402
from allstars_server.http_stub import HttpConfig, HttpStub, Route  # noqa: E402
from allstars_server.npx import NpxConfig, NpxServer  # noqa: E402
from allstars_server.otg import OtgConfig, OtgServer  # noqa: E402
from allstars_server.turn import TurnConfig, TurnServer  # noqa: E402
from allstars_server.wire import Cmd, Err, Writer  # noqa: E402
from allstars_server import vlan as vlanmod  # noqa: E402
from allstars_server.dns import DnsConfig, DnsServer  # noqa: E402


def free_port(kind=socket.SOCK_STREAM) -> int:
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class UdpEndpoint(asyncio.DatagramProtocol):
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.queue.put_nowait((data, addr))

    async def recv(self, timeout=2.0):
        return await asyncio.wait_for(self.queue.get(), timeout)


async def udp_endpoint(port=0):
    loop = asyncio.get_running_loop()
    t, p = await loop.create_datagram_endpoint(UdpEndpoint, local_addr=("127.0.0.1", port))
    return p


class StunCodecTest(unittest.TestCase):
    def test_type_roundtrip(self):
        for m in (stun.BINDING, stun.ALLOCATE, stun.CHANNEL_BIND, stun.DATA):
            for c in (stun.CLASS_REQUEST, stun.CLASS_INDICATION, stun.CLASS_SUCCESS, stun.CLASS_ERROR):
                t = stun.make_type(m, c)
                self.assertEqual((stun.method_of(t), stun.class_of(t)), (m, c))
        self.assertEqual(stun.make_type(stun.BINDING, stun.CLASS_SUCCESS), 0x0101)
        self.assertEqual(stun.make_type(stun.ALLOCATE, stun.CLASS_ERROR), 0x0113)

    def test_xor_address(self):
        tid = os.urandom(12)
        for addr in (("192.0.2.1", 32853), ("2001:db8::1", 1234)):
            self.assertEqual(stun.decode_xor_address(stun.encode_xor_address(addr, tid), tid), addr)

    def test_rfc5769_ipv4_xor_mapped(self):
        # RFC 5769 2.2: 192.0.2.1:32853 -> porta xor 0xa147, ip xor 0xe112a643
        enc = stun.encode_xor_address(("192.0.2.1", 32853), b"\x00" * 12)
        self.assertEqual(enc, bytes.fromhex("0001a147e112a643"))

    def test_integrity_and_fingerprint(self):
        key = stun.long_term_key("user", "realm", "pass")
        m = stun.Message(stun.ALLOCATE, stun.CLASS_REQUEST)
        m.add(stun.USERNAME, b"user").add(stun.REQUESTED_TRANSPORT, bytes([17, 0, 0, 0]))
        raw = m.encode(integrity_key=key, fingerprint=True)
        d = stun.Message.decode(raw)
        self.assertTrue(d.check_integrity(key))
        self.assertFalse(d.check_integrity(b"x" * 16))
        fp = struct.unpack("!I", d.get(stun.FINGERPRINT))[0]
        import zlib
        self.assertEqual(fp, (zlib.crc32(raw[:-8]) ^ stun.FINGERPRINT_XOR) & 0xFFFFFFFF)

    def test_is_stun_vs_channel(self):
        m = stun.Message(stun.BINDING, stun.CLASS_REQUEST).encode()
        self.assertTrue(stun.is_stun(m))
        self.assertFalse(stun.is_channel_data(m))
        self.assertTrue(stun.is_channel_data(b"\x40\x00\x00\x00"))


class TicketTest(unittest.TestCase):
    def test_roundtrip(self):
        secret = os.urandom(32)
        t = ticket.build_ticket(secret, 42, "Kratos_123", "UP9000-BCUS98472_00", cookie=b"abc")
        info = ticket.verify_ticket(secret, t)
        self.assertIsNotNone(info)
        self.assertEqual(info["online_id"], "Kratos_123")
        self.assertEqual(info["user_id"], 42)
        self.assertEqual(info["service_id"], "UP9000-BCUS98472_00")
        self.assertEqual(struct.unpack(">I", t[:4])[0], ticket.VERSION_2_1)
        self.assertEqual(struct.unpack(">I", t[4:8])[0], len(t) - 8)
        self.assertIsNone(ticket.verify_ticket(os.urandom(32), t))


class AsyncCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.closers = []

    async def asyncTearDown(self):
        for c in self.closers:
            c()
        await asyncio.sleep(0.05)
        self.tmp.cleanup()


class TurnTest(AsyncCase):
    async def start_turn(self, **kw):
        port = free_port(socket.SOCK_DGRAM)
        relay = free_port(socket.SOCK_DGRAM)
        cfg = TurnConfig(bind_host="127.0.0.1", port=port, relay_public_ip="127.0.0.1",
                         relay_bind_host="127.0.0.1", relay_port_min=relay, relay_port_max=relay + 3, **kw)
        srv = TurnServer(cfg)
        await srv.start()
        self.closers.append(srv.close)
        return srv, ("127.0.0.1", port)

    async def transact(self, ep, server, msg, key=None):
        ep.transport.sendto(msg.encode(integrity_key=key, fingerprint=True), server)
        while True:
            data, _ = await ep.recv()
            if stun.is_stun(data):
                r = stun.Message.decode(data)
                if r.transaction_id == msg.transaction_id:
                    return r

    async def test_binding(self):
        _, server = await self.start_turn(auth="none")
        ep = await udp_endpoint()
        r = await self.transact(ep, server, stun.Message(stun.BINDING, stun.CLASS_REQUEST))
        self.assertEqual(r.cls, stun.CLASS_SUCCESS)
        self.assertEqual(r.get_xor_address(stun.XOR_MAPPED_ADDRESS), ep.transport.get_extra_info("sockname")[:2])

    async def _allocate(self, ep, server, key=None, user=None, nonce=None, realm=None):
        m = stun.Message(stun.ALLOCATE, stun.CLASS_REQUEST)
        m.add(stun.REQUESTED_TRANSPORT, bytes([17, 0, 0, 0]))
        if user:
            m.add(stun.USERNAME, user.encode()).add(stun.REALM, realm).add(stun.NONCE, nonce)
        return await self.transact(ep, server, m, key)

    async def test_relay_send_indication_and_channel(self):
        _, server = await self.start_turn(auth="none")
        client = await udp_endpoint()
        peer = await udp_endpoint()
        peer_addr = peer.transport.get_extra_info("sockname")[:2]
        r = await self._allocate(client, server)
        self.assertEqual(r.cls, stun.CLASS_SUCCESS, r.error_code())
        relayed = r.get_xor_address(stun.XOR_RELAYED_ADDRESS)

        # Sem permissao o peer nao alcanca o cliente.
        peer.transport.sendto(b"cedo", relayed)
        await asyncio.sleep(0.1)
        self.assertTrue(client.queue.empty())

        cp = stun.Message(stun.CREATE_PERMISSION, stun.CLASS_REQUEST).add_xor_address(stun.XOR_PEER_ADDRESS, peer_addr)
        self.assertEqual((await self.transact(client, server, cp)).cls, stun.CLASS_SUCCESS)

        ind = stun.Message(stun.SEND, stun.CLASS_INDICATION).add_xor_address(stun.XOR_PEER_ADDRESS, peer_addr)
        ind.add(stun.DATA_ATTR, b"ola peer")
        client.transport.sendto(ind.encode(), server)
        data, src = await peer.recv()
        self.assertEqual(data, b"ola peer")
        self.assertEqual(src[:2], relayed)

        peer.transport.sendto(b"ola cliente", relayed)
        data, _ = await client.recv()
        d = stun.Message.decode(data)
        self.assertEqual((d.method, d.cls), (stun.DATA, stun.CLASS_INDICATION))
        self.assertEqual(d.get(stun.DATA_ATTR), b"ola cliente")
        self.assertEqual(d.get_xor_address(stun.XOR_PEER_ADDRESS), peer_addr)

        cb = stun.Message(stun.CHANNEL_BIND, stun.CLASS_REQUEST)
        cb.add(stun.CHANNEL_NUMBER, struct.pack("!HH", 0x4001, 0)).add_xor_address(stun.XOR_PEER_ADDRESS, peer_addr)
        self.assertEqual((await self.transact(client, server, cb)).cls, stun.CLASS_SUCCESS)
        client.transport.sendto(struct.pack("!HH", 0x4001, 3) + b"abc\x00", server)
        data, _ = await peer.recv()
        self.assertEqual(data, b"abc")
        peer.transport.sendto(b"xyz12", relayed)
        data, _ = await client.recv()
        self.assertEqual(data[:4], struct.pack("!HH", 0x4001, 5))
        self.assertEqual(data[4:9], b"xyz12")

        rf = stun.Message(stun.REFRESH, stun.CLASS_REQUEST).add(stun.LIFETIME, struct.pack("!I", 0))
        self.assertEqual((await self.transact(client, server, rf)).cls, stun.CLASS_SUCCESS)
        rf2 = stun.Message(stun.REFRESH, stun.CLASS_REQUEST)
        self.assertEqual((await self.transact(client, server, rf2)).error_code(), 437)

    async def test_longterm_auth(self):
        _, server = await self.start_turn(auth="longterm", users={"kratos": "segredo"})
        ep = await udp_endpoint()
        r = await self._allocate(ep, server)
        self.assertEqual(r.error_code(), 401)
        realm, nonce = r.get(stun.REALM), r.get(stun.NONCE)
        bad = stun.long_term_key("kratos", realm.decode(), "errada")
        r = await self._allocate(ep, server, bad, "kratos", nonce, realm)
        self.assertEqual(r.error_code(), 401)
        key = stun.long_term_key("kratos", realm.decode(), "segredo")
        r = await self._allocate(ep, server, key, "kratos", nonce, realm)
        self.assertEqual(r.cls, stun.CLASS_SUCCESS, r.error_code())
        self.assertTrue(r.check_integrity(key))

    async def test_any_auth_accepts_unknown_user(self):
        _, server = await self.start_turn(auth="any")
        ep = await udp_endpoint()
        r = await self._allocate(ep, server)
        realm, nonce = r.get(stun.REALM), r.get(stun.NONCE)
        key = stun.long_term_key("qualquer", realm.decode(), "x")
        r = await self._allocate(ep, server, key, "qualquer", nonce, realm)
        self.assertEqual(r.cls, stun.CLASS_SUCCESS, r.error_code())


class NpxTest(AsyncCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.db = Database(os.path.join(self.tmp.name, "t.db"))
        port = free_port()
        udp = free_port(socket.SOCK_DGRAM)
        self.srv = NpxServer(NpxConfig(bind_host="127.0.0.1", port=port, udp_port=udp), self.db)
        await self.srv.start()
        self.port, self.udp = port, udp
        self.closers += [self.srv.close, self.db.close]

    async def client(self, name=None, password="pw"):
        c = NpxClient()
        await c.connect("127.0.0.1", self.port)
        self.closers.insert(0, lambda c=c: c.writer.close())
        await c.hello()
        if name:
            await c.login(name, password)
        return c

    async def test_login_create_and_password(self):
        c = await self.client()
        with self.assertRaises(NpxError) as e:
            await c.request(Cmd.GET_TICKET, Writer().str("x").blob(b"").bytes())
        self.assertEqual(e.exception.err, Err.NOT_LOGGED_IN)
        await c.login("Kratos", "pw")
        self.assertGreater(c.user_id, 0)
        c2 = await self.client()
        with self.assertRaises(NpxError) as e:
            await c2.login("kratos", "errada")
        self.assertEqual(e.exception.err, Err.WRONG_PASSWORD)
        with self.assertRaises(NpxError) as e:
            await c2.login("1nvalid!", "pw")
        self.assertEqual(e.exception.err, Err.INVALID_ONLINE_ID)

    async def test_ticket(self):
        c = await self.client("Sackboy")
        t = await c.get_ticket("UP9000-BCUS98472_00")
        info = ticket.verify_ticket(self.srv.cfg.ticket_secret, t)
        self.assertEqual(info["online_id"], "Sackboy")

    async def test_friends_presence_and_messages(self):
        a = await self.client("Nathan")
        b = await self.client("Sly_Cooper")
        cmd, r = await a.next_notification()
        self.assertEqual(cmd, Cmd.N_FRIEND_STATUS)
        self.assertEqual((r.str(), r.u8()), ("Sly_Cooper", 1))
        _, r = await b.request(Cmd.GET_FRIENDS)
        self.assertEqual(r.u16(), 1)
        self.assertEqual(r.str(), "Nathan")
        await b.request(Cmd.SEND_MESSAGE, Writer().str("Nathan").u16(1).u16(0).str("oi").str("bora").blob(b"\x01").bytes())
        cmd, r = await a.next_notification()
        self.assertEqual(cmd, Cmd.N_MESSAGE)
        self.assertEqual(r.str(), "Sly_Cooper")

    async def test_signaling_with_udp_ping(self):
        a = await self.client("Ratchet")
        b = await self.client("Clank")
        await a.next_notification()  # Clank entrou
        for c, port in ((a, 0), (b, 0)):
            ep = await udp_endpoint()
            lp = ep.transport.get_extra_info("sockname")[1]
            await c.request(Cmd.SIG_REGISTER, Writer().ip4("192.168.0.10").u16(lp).bytes())
            ep.transport.sendto(b"NPXP" + c.udp_token, ("127.0.0.1", self.udp))
            data, _ = await ep.recv()
            self.assertEqual(data[:12], b"NPXP" + c.udp_token)
            self.assertEqual(struct.unpack("<H", data[16:18])[0], lp)
            c.p2p_port = lp
        _, r = await a.request(Cmd.SIG_CONNECT, Writer().str("Clank").u32(7).bytes())
        self.assertEqual((r.u32(), r.str(), r.ip4(), r.u16()), (7, "Clank", "127.0.0.1", b.p2p_port))
        cmd, r = await b.next_notification()
        self.assertEqual(cmd, Cmd.N_SIG_REQUEST)
        self.assertEqual((r.u32(), r.str(), r.ip4(), r.u16(), r.ip4()), (7, "Ratchet", "127.0.0.1", a.p2p_port, "192.168.0.10"))
        err, _ = await a.request(Cmd.SIG_CONNECT, Writer().str("Ninguem").u32(1).bytes(), check=False)
        self.assertEqual(err, Err.PEER_OFFLINE)

    async def test_scores(self):
        a = await self.client("Parappa")
        b = await self.client("Dante")
        rec = lambda s: Writer().u32(1).u32(0).i64(s).str("gg").blob(b"").u8(1).bytes()
        _, r = await a.request(Cmd.SCORE_RECORD, rec(100))
        self.assertEqual((r.u32(), r.u8()), (1, 1))
        _, r = await b.request(Cmd.SCORE_RECORD, rec(200))
        self.assertEqual(r.u32(), 1)
        _, r = await a.request(Cmd.SCORE_RECORD, rec(50))
        self.assertEqual((r.u32(), r.u8()), (2, 0))
        _, r = await a.request(Cmd.SCORE_GET_RANGE, Writer().u32(1).u32(1).u16(10).bytes())
        self.assertEqual((r.u32(), r.u16()), (2, 2))
        self.assertEqual((r.u32(), r.str()), (1, "Dante"))
        _, r = await a.request(Cmd.SCORE_GET_BY_ID, Writer().u32(1).u32(0).u16(2).str("Parappa").str("x").bytes())
        self.assertEqual((r.u32(), r.u16(), r.u8(), r.u32(), r.str()), (2, 2, 1, 2, "Parappa"))
        self.assertEqual((r.u32(), r.i64()), (0, 100))  # pcid, score
        r.str(); r.blob(); r.u64()
        self.assertEqual(r.u8(), 0)

    async def test_tus(self):
        a = await self.client("Cole")
        await a.request(Cmd.TUS_SET_VAR, Writer().str("").i32(3).i64(-5).bytes())
        _, r = await a.request(Cmd.TUS_GET_VAR, Writer().str("Cole").i32(3).bytes())
        self.assertEqual((r.u8(), r.i64()), (1, -5))
        await a.request(Cmd.TUS_SET_DATA, Writer().str("").i32(1).blob(b"save").blob(b"i").bytes())
        _, r = await a.request(Cmd.TUS_GET_DATA, Writer().str("").i32(1).bytes())
        self.assertEqual((r.u8(), r.blob(), r.blob()), (1, b"save", b"i"))
        await a.request(Cmd.TUS_DELETE, Writer().str("").i32(1).bytes())
        _, r = await a.request(Cmd.TUS_GET_DATA, Writer().str("").i32(1).bytes())
        self.assertEqual(r.u8(), 0)

    async def test_relogin_kicks_old_session(self):
        a = await self.client("Raiden")
        b = await self.client("Raiden")
        self.assertEqual(self.srv.sessions[b.user_id].online_id, "Raiden")
        await asyncio.sleep(0.1)
        self.assertTrue(a.reader.at_eof())


class HttpAndOtgTest(AsyncCase):
    async def test_http_route(self):
        port = free_port()
        srv = HttpStub(HttpConfig("127.0.0.1", port, [Route("/ipmapping-rest/", body='{"ok":1}')]))
        await srv.start()
        self.closers.append(srv.close)
        r, w = await asyncio.open_connection("127.0.0.1", port)
        w.write(b"GET /ipmapping-rest/otgc/IPMapping/battleroyale/location HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        data = await r.read()
        self.assertTrue(data.startswith(b"HTTP/1.1 200"))
        self.assertTrue(data.endswith(b'{"ok":1}'))
        w.close()

    async def test_otg_capture(self):
        port = free_port()
        cap = os.path.join(self.tmp.name, "cap")
        srv = OtgServer(OtgConfig("127.0.0.1", [port], [], cap, {port: ["cafe"]}))
        await srv.start()
        self.closers.append(srv.close)
        r, w = await asyncio.open_connection("127.0.0.1", port)
        w.write(b"\x00\x01hello")
        self.assertEqual(await r.readexactly(2), b"\xca\xfe")
        w.close()
        await asyncio.sleep(0.1)
        logs = os.listdir(cap)
        self.assertEqual(len(logs), 1)
        with open(os.path.join(cap, logs[0])) as f:
            text = f.read()
        self.assertIn("00 01 68 65 6c 6c 6f", text)
        self.assertIn("-> 2 bytes", text)


def dns_query(name: str, qtype: int = 1, qid: int = 0x1234) -> bytes:
    q = struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    for label in name.split("."):
        q += bytes([len(label)]) + label.encode()
    return q + b"\x00" + struct.pack("!HH", qtype, 1)


class DnsTest(AsyncCase):
    async def test_records_blocked_and_nx(self):
        port = free_port(socket.SOCK_DGRAM)
        srv = DnsServer(DnsConfig("127.0.0.1", port, {"*.online.scea.com": "10.0.0.5"}, ["*.telemetry.*"], ""))
        await srv.start()
        self.closers.append(srv.close)
        ep = await udp_endpoint()

        async def ask(name, qtype=1):
            ep.transport.sendto(dns_query(name, qtype), ("127.0.0.1", port))
            data, _ = await ep.recv()
            return data

        r = await ask("battleroyale-final.ps3.online.scea.com")
        qid, flags, qd, an = struct.unpack_from("!HHHH", r)
        self.assertEqual((qid, flags & 0xF, qd, an), (0x1234, 0, 1, 1))
        self.assertEqual(r[-4:], bytes([10, 0, 0, 5]))
        r = await ask("battleroyale-final.telemetry.online.scea.com")
        self.assertEqual(struct.unpack_from("!H", r, 2)[0] & 0xF, 3)
        r = await ask("example.com")
        self.assertEqual(struct.unpack_from("!H", r, 2)[0] & 0xF, 3)
        r = await ask("battleroyale-final.turn1.online.scea.com", qtype=28)
        self.assertEqual(struct.unpack_from("!HH", r, 2), (0x8580, 1))
        self.assertEqual(struct.unpack_from("!H", r, 6)[0], 0)


class VlanFlowTest(AsyncCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.db = Database(os.path.join(self.tmp.name, "v.db"))
        vport = free_port(socket.SOCK_DGRAM)
        self.vlan = vlanmod.VlanServer(vlanmod.VlanConfig(udp_port=vport, max_members=3), "127.0.0.1")
        await self.vlan.start()
        port = free_port()
        self.srv = NpxServer(NpxConfig(bind_host="127.0.0.1", port=port, udp_port=free_port(socket.SOCK_DGRAM)),
                             self.db, self.vlan)
        await self.srv.start()
        self.port, self.vport = port, vport
        self.closers += [self.srv.close, self.vlan.close, self.db.close]

    async def player(self, name, room="sala1"):
        c = NpxClient()
        await c.connect("127.0.0.1", self.port)
        self.closers.insert(0, lambda c=c: c.writer.close())
        await c.hello()
        await c.login(name, "pw")
        ep = await udp_endpoint()
        lp = ep.transport.get_extra_info("sockname")[1]
        _, r = await c.request(Cmd.VLAN_JOIN, Writer().str(room).ip4("192.168.1.2").u16(lp).bytes())
        c.vip, mask, c.bcast, c.vtoken, tport = r.ip4(), r.ip4(), r.ip4(), r.blob(), r.u16()
        self.assertEqual((mask, tport), ("255.255.255.0", self.vport))
        c.others = [(r.str(), r.ip4()) for _ in range(r.u16())]
        c.ep = ep
        ep.transport.sendto(vlanmod.HDR.pack(b"AV", vlanmod.T_KEEPALIVE, 0, c.vtoken), ("127.0.0.1", self.vport))
        data, _ = await ep.recv()
        c.peer_count = data[12 + 6]
        return c

    def data_pkt(self, c, dst, payload, src="6.6.6.6"):
        hdr = vlanmod.HDR.pack(b"AV", vlanmod.T_DATA, 0, c.vtoken)
        body = vlanmod.DATA_HDR.pack(socket.inet_aton(src), socket.inet_aton(dst), 1, 3658, 3658, 1000, 1000)
        return hdr + body + payload

    async def test_broadcast_unicast_and_membership(self):
        a = await self.player("Kratos")
        b = await self.player("Sackboy")
        self.assertEqual(a.vip, "10.77.0.1")
        self.assertEqual(b.vip, "10.77.0.2")
        self.assertEqual(b.others, [("Kratos", "10.77.0.1")])
        self.assertEqual(b.peer_count, 1)
        cmd, r = await a.next_notification()
        self.assertEqual(cmd, Cmd.N_FRIEND_STATUS)
        cmd, r = await a.next_notification()
        self.assertEqual(cmd, Cmd.N_VLAN_MEMBER)
        self.assertEqual((r.str(), r.str(), r.ip4(), r.u8()), ("sala1", "Sackboy", "10.77.0.2", 1))

        # broadcast do jogo (beacon do lobby LAN): chega no outro membro com origem reescrita
        a.ep.transport.sendto(self.data_pkt(a, "255.255.255.255", b"\x00\x00\x00\x00\x08\x45\x71\x29"),
                              ("127.0.0.1", self.vport))
        data, _ = await b.ep.recv()
        src, dst, proto, sp, dp, svp, dvp = vlanmod.DATA_HDR.unpack_from(data, 12)
        self.assertEqual((socket.inet_ntoa(src), proto, dvp), ("10.77.0.1", 1, 1000))
        self.assertEqual(data[12 + vlanmod.DATA_HDR.size:], b"\x00\x00\x00\x00\x08\x45\x71\x29")
        self.assertTrue(a.ep.queue.empty())

        b.ep.transport.sendto(self.data_pkt(b, "10.77.0.1", b"join?"), ("127.0.0.1", self.vport))
        data, _ = await a.ep.recv()
        self.assertEqual(data[-5:], b"join?")

        # sala cheia (max 3) e sala separada
        c = await self.player("Dante")
        with self.assertRaises(NpxError) as e:
            await self.player("Raiden")
        self.assertEqual(e.exception.err, Err.ROOM_FULL)
        d = await self.player("Nariko", room="outra")
        self.assertEqual(d.vip, "10.77.1.1")
        _, r = await a.request(Cmd.VLAN_LIST)
        self.assertEqual(r.u16(), 2)

        # logout tira da sala
        await c.request(Cmd.LOGOUT)
        self.assertEqual(len(self.vlan.rooms["sala1"].members), 2)

    async def test_rejoin_same_room_alone(self):
        a = await self.player("Jak")
        _, r = await a.request(Cmd.VLAN_JOIN, Writer().str("sala1").ip4("192.168.1.2").u16(1).bytes())
        self.assertEqual(r.ip4(), "10.77.0.1")
        self.assertIn("sala1", self.vlan.rooms)
        self.assertEqual(len(self.vlan.rooms["sala1"].members), 1)

    async def test_unknown_token_ignored(self):
        a = await self.player("Cole")
        ep = await udp_endpoint()
        bad = vlanmod.HDR.pack(b"AV", vlanmod.T_KEEPALIVE, 0, b"\x01" * 8)
        ep.transport.sendto(bad, ("127.0.0.1", self.vport))
        await asyncio.sleep(0.1)
        self.assertTrue(ep.queue.empty())


if __name__ == "__main__":
    unittest.main()
