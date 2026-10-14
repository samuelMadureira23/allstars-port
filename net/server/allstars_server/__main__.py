"""Ponto de entrada: python -m allstars_server [--config arquivo.json]."""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from .config import load_config
from .db import Database
from .dns import DnsServer
from .http_stub import HttpStub
from .npx import NpxServer
from .otg import OtgServer
from .turn import TurnServer
from .vlan import VlanServer


async def run(cfg) -> None:
    db = Database(cfg.db_path)
    services = []
    vlan = VlanServer(cfg.vlan, cfg.npx.bind_host) if cfg.vlan_enabled else None
    if vlan is not None:
        services.append(vlan)
    if cfg.npx_enabled:
        services.append(NpxServer(cfg.npx, db, vlan))
    if cfg.dns_enabled:
        services.append(DnsServer(cfg.dns))
    if cfg.turn_enabled:
        services.append(TurnServer(cfg.turn))
    if cfg.http_enabled:
        services.append(HttpStub(cfg.http))
    if cfg.otg_enabled:
        services.append(OtgServer(cfg.otg))
    for s in services:
        try:
            await s.start()
        except OSError as e:
            logging.getLogger("main").error("%s nao abriu a porta: %s", type(s).__name__, e)
    logging.getLogger("main").info("servidor pronto (%d servicos); Ctrl+C para sair", len(services))
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):
            pass  # Windows: Ctrl+C chega como KeyboardInterrupt
    try:
        await stop.wait()
    finally:
        for s in services:
            s.close()
        db.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="allstars_server", description=__doc__)
    ap.add_argument("--config", default=None, help="arquivo JSON (padrao: config.json se existir)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(name)-5s %(levelname)-7s %(message)s")
    cfg = load_config(args.config)
    try:
        asyncio.run(run(cfg))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
