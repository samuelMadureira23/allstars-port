# Servidor substituto do online (PlayStation All-Stars Battle Royale, port nativo)

Python 3.10+ sem dependências. Contrato e protocolo: `docs/net.md`.

    cd net/server
    copy config.example.json config.json      (opcional)
    python -m allstars_server                  (ou: python -m allstars_server --config config.json -v)
    python -m unittest discover -s tests       (testes)

Serviços: NPX tcp/udp 32000 (contas, ticket, amigos, sinalização, placares, TUS, salas), LAN virtual udp 32001,
DNS udp 53, STUN/TURN udp 3478 (relay udp 49160-49400), HTTP tcp 10012 (ipmapping) e captura OTG
