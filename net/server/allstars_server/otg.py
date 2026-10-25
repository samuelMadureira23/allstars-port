"""Servidor de jogo OTG (substituto de battleroyale-final.ps3.online.scea.com).

O protocolo do sceotClientServerConnect ainda esta sendo levantado por engenharia
reversa (docs/ONLINE_PROTOCOLO.md). Enquanto isso este modulo roda em modo de
captura: aceita conexoes TCP/UDP nas portas configuradas, grava tudo que chega
(hexdump por sessao em capture_dir) e, se houver, responde com bytes de um
roteiro fixo. Quando o handshake e o formato forem conhecidos, o tratamento
real entra em OtgSession.on_message.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field

log = logging.getLogger("otg")


@dataclass
class OtgConfig:
    bind_host: str = "0.0.0.0"
    tcp_ports: list[int] = field(default_factory=list)
    udp_ports: list[int] = field(default_factory=list)
    capture_dir: str = "captures"
    # Respostas fixas por porta: lista de hex enviada em ordem, uma por mensagem recebida.
    scripted_replies: dict[int, list[str]] = field(default_factory=dict)


def hexdump(data: bytes, base: int = 0) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i: i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{base + i:08x}  {hx:<47}  {asc}")
    return "\n".join(lines)


class _Capture:
    def __init__(self, cfg: OtgConfig, name: str):
        os.makedirs(cfg.capture_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(cfg.capture_dir, f"{stamp}-{name}.log")
        self.f = open(self.path, "a", encoding="utf-8")
        self.t0 = time.monotonic()

    def write(self, direction: str, data: bytes) -> None:
        self.f.write(f"[{time.monotonic() - self.t0:9.3f}] {direction} {len(data)} bytes\n{hexdump(data)}\n")
        self.f.flush()

    def close(self) -> None:
        self.f.close()


class _UdpCapture(asyncio.DatagramProtocol):
    def __init__(self, server: "OtgServer", port: int):
        self.server, self.port = server, port
        self.caps: dict[tuple, _Capture] = {}
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        cap = self.caps.get(addr)
        if cap is None:
            cap = self.caps[addr] = _Capture(self.server.cfg, f"udp{self.port}-{addr[0]}_{addr[1]}")
            log.info("udp/%d: primeiro pacote de %s (captura em %s)", self.port, addr, cap.path)
        cap.write("<-", data)


class OtgServer:
    def __init__(self, cfg: OtgConfig):
        self.cfg = cfg
        self._servers = []
        self._udp = []

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        for port in self.cfg.tcp_ports:
            srv = await asyncio.start_server(
                lambda r, w, p=port: self._handle_tcp(r, w, p), self.cfg.bind_host, port)
            self._servers.append(srv)
            log.info("OTG (captura) em tcp/%s:%d", self.cfg.bind_host, port)
        for port in self.cfg.udp_ports:
            t, _ = await loop.create_datagram_endpoint(
                lambda p=port: _UdpCapture(self, p), local_addr=(self.cfg.bind_host, port))
            self._udp.append(t)
            log.info("OTG (captura) em udp/%s:%d", self.cfg.bind_host, port)

    def close(self) -> None:
        for s in self._servers:
            s.close()
        for t in self._udp:
            t.close()

    async def _handle_tcp(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int) -> None:
        peer = writer.get_extra_info("peername")
        cap = _Capture(self.cfg, f"tcp{port}-{peer[0]}_{peer[1]}")
        log.info("tcp/%d: conexao de %s (captura em %s)", port, peer, cap.path)
        script = list(self.cfg.scripted_replies.get(port, []))
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                cap.write("<-", data)
                if script:
                    out = bytes.fromhex(script.pop(0))
                    cap.write("->", out)
                    writer.write(out)
                    await writer.drain()
        except ConnectionError:
            pass
        finally:
            cap.close()
            writer.close()
            log.info("tcp/%d: %s desconectou", port, peer)
