"""Carrega a configuracao JSON do servidor (todas as chaves sao opcionais)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .dns import DnsConfig
from .http_stub import HttpConfig, Route
from .npx import NpxConfig
from .otg import OtgConfig
from .turn import TurnConfig
from .vlan import VlanConfig

# Resposta padrao do ipmapping: formato real ainda desconhecido (ver docs/ONLINE_PROTOCOLO.md).
DEFAULT_IPMAPPING = Route("/ipmapping-rest/otgc/IPMapping/battleroyale/location",
                          body='{"country":"BR","region":"SA","continent":"SA"}')


@dataclass
class ServerConfig:
    # IP pelo qual os jogadores alcancam este servidor (LAN ou publico). Vira o padrao de
    # turn.relay_public_ip e das respostas do DNS.
    public_ip: str = "127.0.0.1"
    db_path: str = "allstars.db"
    npx_enabled: bool = True
    turn_enabled: bool = True
    http_enabled: bool = True
    otg_enabled: bool = True
    vlan_enabled: bool = True
    dns_enabled: bool = True
    npx: NpxConfig = field(default_factory=NpxConfig)
    turn: TurnConfig = field(default_factory=TurnConfig)
    http: HttpConfig = field(default_factory=lambda: HttpConfig(routes=[DEFAULT_IPMAPPING]))
    otg: OtgConfig = field(default_factory=OtgConfig)
    vlan: VlanConfig = field(default_factory=VlanConfig)
    dns: DnsConfig = field(default_factory=DnsConfig)


def _apply(obj, data: dict, section: str) -> None:
    for k, v in data.items():
        if not hasattr(obj, k):
            raise ValueError(f"chave desconhecida em '{section}': {k}")
        setattr(obj, k, v)


def load_config(path: str | None) -> ServerConfig:
    cfg = ServerConfig()
    data: dict = {}
    if path is None and os.path.exists("config.json"):
        path = "config.json"
    if path is not None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    for key in ("public_ip", "db_path", "npx_enabled", "turn_enabled", "http_enabled", "otg_enabled",
                "vlan_enabled", "dns_enabled"):
        if key in data:
            setattr(cfg, key, data.pop(key))
    turn_has_ip = "relay_public_ip" in data.get("turn", {})
    dns_has_records = "records" in data.get("dns", {})
    if "npx" in data:
        npx = dict(data.pop("npx"))
        if "ticket_secret" in npx:
            npx["ticket_secret"] = bytes.fromhex(npx["ticket_secret"])
        if "title_ids" in npx:
            npx["title_ids"] = tuple(npx["title_ids"])
        _apply(cfg.npx, npx, "npx")
    if "turn" in data:
        _apply(cfg.turn, data.pop("turn"), "turn")
    if "http" in data:
        http = dict(data.pop("http"))
        if "routes" in http:
            http["routes"] = [Route(**r) for r in http["routes"]]
        _apply(cfg.http, http, "http")
    if "otg" in data:
        otg = dict(data.pop("otg"))
        if "scripted_replies" in otg:
            otg["scripted_replies"] = {int(k): v for k, v in otg["scripted_replies"].items()}
        _apply(cfg.otg, otg, "otg")
    if "vlan" in data:
        _apply(cfg.vlan, data.pop("vlan"), "vlan")
    if "dns" in data:
        _apply(cfg.dns, data.pop("dns"), "dns")
    if not turn_has_ip:
        cfg.turn.relay_public_ip = cfg.public_ip
    if not dns_has_records:
        cfg.dns.records = {"*.online.scea.com": cfg.public_ip}
    data.pop("_comentario", None)
    if data:
        raise ValueError(f"chaves desconhecidas: {', '.join(data)}")
    return cfg
