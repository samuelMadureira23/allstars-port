"""Cliente NPX de referencia (asyncio). Usado nos testes e como modelo para a HLE em C++."""
from __future__ import annotations

import asyncio
import itertools

from .wire import HEADER, HEADER_SIZE, PROTOCOL_VERSION, Cmd, Err, Kind, Reader, Writer, pack


class NpxError(Exception):
    def __init__(self, cmd: int, err: int):
        super().__init__(f"comando 0x{cmd:04x} falhou: {Err(err).name if err in Err._value2member_map_ else err}")
        self.cmd, self.err = cmd, err


class NpxClient:
    def __init__(self) -> None:
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self.notifications: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.user_id = 0
        self.online_id = ""
        self.udp_token = b""

    async def connect(self, host: str, port: int) -> None:
        self.reader, self.writer = await asyncio.open_connection(host, port)
        self._task = asyncio.create_task(self._read_loop())

    async def close(self) -> None:
        if self.writer:
            self.writer.close()
        if self._task:
            self._task.cancel()

    async def _read_loop(self) -> None:
        try:
            while True:
                hdr = await self.reader.readexactly(HEADER_SIZE)
                kind, _f, cmd, size, req_id = HEADER.unpack(hdr)
                body = await self.reader.readexactly(size - HEADER_SIZE)
                if kind == Kind.REPLY:
                    fut = self._pending.pop(req_id, None)
                    if fut and not fut.done():
                        fut.set_result((cmd, body))
                elif kind == Kind.NOTIFY:
                    await self.notifications.put((cmd, Reader(body)))
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("conexao fechada"))

    async def request(self, cmd: int, body: bytes = b"", check: bool = True) -> tuple[int, Reader]:
        req_id = next(self._ids)
        fut = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        self.writer.write(pack(Kind.REQUEST, cmd, req_id, body))
        await self.writer.drain()
        _cmd, data = await fut
        r = Reader(data)
        err = r.u8()
        if check and err != Err.OK:
            raise NpxError(cmd, err)
        return err, r

    # -- atalhos ------------------------------------------------------------------
    async def hello(self, title_id: str = "BCUS98472") -> tuple[str, int]:
        _, r = await self.request(Cmd.HELLO, Writer().u32(PROTOCOL_VERSION).str(title_id).bytes())
        r.u32()
        return r.ip4(), r.u16()

    async def login(self, online_id: str, password: str, create: bool = True) -> None:
        _, r = await self.request(Cmd.LOGIN, Writer().str(online_id).str(password).u8(int(create)).bytes())
        self.user_id = r.u64()
        self.online_id = r.str()
        self.udp_token = r.blob()

    async def get_ticket(self, service_id: str, cookie: bytes = b"") -> bytes:
        _, r = await self.request(Cmd.GET_TICKET, Writer().str(service_id).blob(cookie).bytes())
        return r.blob()

    async def next_notification(self, timeout: float = 2.0) -> tuple[int, Reader]:
        return await asyncio.wait_for(self.notifications.get(), timeout)
