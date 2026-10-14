"""Servidor HTTP minimo para os servicos REST do OTG (ipmapping, e o que mais aparecer).

Responde por prefixo de caminho com corpos configurados e registra todo pedido
(metodo, caminho, cabecalhos, corpo) para ajudar a engenharia reversa.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

log = logging.getLogger("http")

MAX_BODY = 1 << 20


@dataclass
class Route:
    prefix: str
    status: int = 200
    content_type: str = "application/json"
    body: str = "{}"


@dataclass
class HttpConfig:
    bind_host: str = "0.0.0.0"
    port: int = 10012
    routes: list[Route] = field(default_factory=list)


REASONS = {200: "OK", 204: "No Content", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}


class HttpStub:
    def __init__(self, cfg: HttpConfig):
        self.cfg = cfg
        self._server = None
        self.requests: list[tuple[str, str, bytes]] = []

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self.cfg.bind_host, self.cfg.port)
        log.info("HTTP em tcp/%s:%d (%d rotas)", self.cfg.bind_host, self.cfg.port, len(self.cfg.routes))

    def close(self) -> None:
        if self._server:
            self._server.close()

    def _route(self, path: str) -> Route | None:
        best = None
        for r in self.cfg.routes:
            if path.startswith(r.prefix) and (best is None or len(r.prefix) > len(best.prefix)):
                best = r
        return best

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    method, target, version = line.decode("latin-1").strip().split(" ", 2)
                except ValueError:
                    break
                headers: dict[str, str] = {}
                while True:
                    h = await reader.readline()
                    if h in (b"\r\n", b"\n", b""):
                        break
                    k, _, v = h.decode("latin-1").partition(":")
                    headers[k.strip().lower()] = v.strip()
                length = min(int(headers.get("content-length", "0") or 0), MAX_BODY)
                body = await reader.readexactly(length) if length else b""
                self.requests.append((method, target, body))
                log.info("%s %s %s de %s headers=%s corpo=%r", method, target, version, peer, headers, body[:512])
                route = self._route(target.split("?", 1)[0])
                if route is None:
                    status, ctype, out = 404, "text/plain", b"not found"
                else:
                    status, ctype, out = route.status, route.content_type, route.body.encode()
                keep = version.upper() == "HTTP/1.1" and headers.get("connection", "").lower() != "close"
                resp = (f"{version} {status} {REASONS.get(status, 'OK')}\r\n"
                        f"Content-Type: {ctype}\r\nContent-Length: {len(out)}\r\n"
                        f"Connection: {'keep-alive' if keep else 'close'}\r\n\r\n").encode() + out
                writer.write(resp)
                await writer.drain()
                if not keep:
                    break
        except (asyncio.IncompleteReadError, ConnectionError, ValueError):
            pass
        finally:
            writer.close()
