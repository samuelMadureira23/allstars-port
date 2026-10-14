# docs/net.md — Contrato da frente de rede (modo online)

Dono: frente 5 "Modo online" (agente `claude-net`, tarefas T-005 e T-010).
Para mudar este contrato, outra frente escreve uma proposta em `net/propostas/` e avisa o dono.
Última atualização: 14/10/2026. Endereços são do EBOOT 1.00 salvo indicação.

## 1. O que sabemos do online do jogo

- **Servidores oficiais:** desligados em 31/01/2019 (PS3 e Vita). Havia Ranked Match, Quick Match,
  placares online e cross-play PS3↔Vita.
- **Não usa NP Matching2.** O RPCS3 com RPCN não conecta ("Requires custom server" na wiki do RPCS3).
  O matchmaking oficial é do **OTG** da SCEA: biblioteca estática no EBOOT (`sceotClientServerConnect`,
  build 1.60 de 14/09/2012, código em ~0x978000–0x9A0000) sobre `sys_net`.
- **Existe um modo LAN escondido, "Network Versus".** É o caminho que a comunidade usa hoje
  (Project-RePSASBR, "All-Stars Matchmaker", out/2026): um hook liga a flag de LAN e um `patch.psarc`
  mostra o menu; o tráfego LAN é tunelado para um servidor deles. Ranked/Quick continuam sem funcionar
  lá. O conector e o servidor deles não são públicos; o hook (CircleButton) é MIT.
- Detalhes de RE: `docs/ONLINE_ACHADOS.md` (strings/imports) e `docs/ONLINE_PROTOCOLO.md` (decompilação).

### 1.1 Fatos de RE já confirmados
| Item | Endereço / valor | Certeza |
|---|---|---|
| Transporte do OTG | TCP puro, sem TLS. `SocketTcp::Connect` 0x98E908: socket(2,1,6), `SO_NBIO` (0x1100), connect não bloqueante (aceita EINPROGRESS 0x24). Recv 0x98E4D8, Select 0x98E5B0, Send 0x98E7BC | alta |
| DNS do OTG | **não usa gethostbyname**: `sceotGetHostUtil` (0x9930F8…0x993CB8) monta consultas DNS e manda por UDP à porta 53 do DNS primário de `cellNetCtlGetInfo(0x13 PRIMARY_DNS)` | alta |
| Host literal | se o nome começa com dígito, `inet_addr` direto (0x98A65C) | alta |
| Estado da conexão | máquina de estados em this+0x5C (0..10), tabela 0x98A784; OnConnect 0x98A38C | alta |
| Porta e cabeçalho do OTG, CryptManager | pendente | — |
| HostLanLobby / JoinLanLobby | 0x2FE00C / 0x2FE36C (1.12: 0x313354 / 0x3136BC) | alta |
| g_VersusLanFlag (1 = host, 0 = join) | **0x0223FFA8** (byte, BSS; TOC 0xC7DC14). Lido em 0xC55E0 (em 0xC4E60, logo após comparar um hash com 0x75606733) e 0x8E54A8 (em 0x8E537C). Equivale ao 1.12 0x022870C4 (lido em 0xC64A8; trecho 24/24 instruções iguais). O 0x025332F8 lido por HostLanLobby é outra global (1.12: 0x0257A478) | alta |
| Transporte LAN | `Networking\netTransportSAMLAN.cpp`; sockets `DGRAM_P2P` (tipo 6), UDP 3658, vport 1000, broadcast 255.255.255.255; beacon com payload `00 00 00 00 08 45 71 29` | 1.12 público; validar no 1.00 |
| Enquadramento P2P no fio (console) | `FF 83 | src_vport BE16 | dst_vport BE16 | payload` | público (fork RPCS3) |

- **Versão:** o port roda o EBOOT 1.00; RPCS3/PS3 da comunidade usam o 1.12. Partida mista exige a
  mesma versão do protocolo de jogo. Alvo inicial: port ↔ port.

## 2. Estratégia: dois caminhos

**Caminho A — LAN virtual (primeiro a funcionar).** Ligar o "Network Versus" no port e transformar a LAN
do jogo numa LAN virtual pela internet. O jogo acha e entra na partida sozinho; nós só levamos os
pacotes. Não depende de entender o OTG.

**Caminho B — OTG completo (Ranked/Quick Match).** Reimplementar o servidor de lobby OTG a partir da RE.
Mais longo; segue em paralelo.

```
 jogo recompilado                                    servidor substituto (net/server, Python stdlib)
 ├─ sys_net HLE (Winsock real)
 │   ├─ DGRAM_P2P / broadcast / 10.77.x.x ═ túnel UDP ═▶ vlan.py   LAN virtual   udp/32001   (A)
 │   ├─ TCP OTG ─────────────────────────────────────▶ otg.py    lobby OTG     tcp/TBD     (B)
 │   ├─ UDP :53 do DNS primário ─────────────────────▶ dns.py    *.online.scea.com → servidor
 │   ├─ STUN/TURN ───────────────────────────────────▶ turn.py   udp/3478 + relay 49160-49400
 │   └─ HTTP ipmapping ──────────────────────────────▶ http_stub tcp/10012
 ├─ sceNp*/Basic/Signaling/Score/Tus ── NPX ─────────▶ npx.py    tcp+udp/32000
 └─ cellNetCtl (conectado; IP/DNS conforme o modo)
           jogador A ◀══ UDP direto (hole punching) ou relay pelo servidor ══▶ jogador B
```

## 3. Lado do cliente (HLE no ps3recomp, worktree `agents/claude-net/ps3recomp`)

Estado atual: `sys_net` registrado em `runtime/ppu/ppu_sysprx.cpp` é um modelo offline (connect, accept,
listen, send, getsockname, getsockopt, inet_addr, shutdown, abort_* e 2 NIDs sem nome sem HLE);
`libs/network/sysNet.c` (Winsock real) existe mas não está ligado a NID nenhum; cellNetCtl reporta
desconectado; sceNp é falso/offline. Os imports faltando estão em `docs/jogo.md`.

### 3.1 sys_net (prioridade 1)
- Tabela de descritores guest → `SOCKET` do host; ids guest pequenos (0..1023).
- `sockaddr_in` do PS3: `u8 sin_len, u8 sin_family(2), be16 port, be32 addr, u8 zero[8]`. Converter nos
  dois sentidos; ponteiros guest via `vm_base` (`GUEST_PTR`).
- Funções: socket, bind, connect, listen, accept, send, sendto, recv, recvfrom, recvmsg, sendmsg,
  shutdown, socketclose, getsockname, getpeername, getsockopt, setsockopt (`SO_NBIO` 0x1100,
  `SO_REUSEADDR`, `SO_BROADCAST` 0x20, `SO_USECRYPTO` 0x1000 / `SO_USESIGNATURE` 0x2000 aceitos e
  ignorados), poll, select (fd_set guest = bitmap em palavras be32), inet_addr/aton/ntoa/ntop/pton
  (o NID sem nome 0xA9A079E0 se comporta como inet_aton), gethostbyname/gethostbyaddr,
  sys_net_abort_resolver/socket, `_sys_net_errno_loc` (errno por thread guest).
- errno: `WSAE*` → valores BSD do PS3 (EWOULDBLOCK 35, EINPROGRESS 36, EALREADY 37, ENOTCONN 57,
  ECONNREFUSED 61, ECONNRESET 54, ETIMEDOUT 60, EADDRINUSE 48, EHOSTUNREACH 65...).
- Chamada bloqueante bloqueia a thread do host da thread PPU; `abort_socket` fecha o socket do host.
- **DNS:** `cellNetCtlGetInfo(PRIMARY_DNS)` devolve o IP do servidor substituto, e o `sendto` para
  `<dns>:53` é desviado para `server:dns_port`. Para quem não puder abrir a porta 53, `dns_port` muda.
  `gethostbyname` aplica as mesmas regras localmente.
- **Sockets DGRAM_P2P (tipo 6) e STREAM_P2P (10):** sockets virtuais. Um socket UDP real por porta P2P
  (3658) multiplexa os vports. Fora do modo LAN virtual, o fio usa o enquadramento de console
  `FF 83 | src_vport BE16 | dst_vport BE16 | payload`, o mesmo de PS3/Vita/fork do RPCS3.
- **Modo LAN virtual (caminho A):** destino em `10.77.0.0/16` ou broadcast vai pelo túnel (§6); o resto
  vai para a rede real. Ver §3.4.
- `port_offset`: soma um deslocamento às portas locais (duas instâncias no mesmo PC).
- `NET_TRACE=1`: uma linha por chamada (fd, endereço, bytes, erro). `NET_PCAP=<arquivo>`: pcap do
  tráfego do jogo para a RE.

### 3.2 cellNetCtl
Online ligado: estado `IPObtained` (3); `IP_ADDRESS` (16) = IP virtual da sala no modo LAN virtual,
senão o IP da interface que chega ao servidor; `NETMASK` (17) 255.255.255.0 no modo LAN virtual;
`PRIMARY_DNS` (19 no RPCS3; o OTG pede 0x13) = servidor; `MTU` 1500; NAT via STUN do `turn.py`.
Online desligado: comportamento offline atual.

### 3.3 NP → NPX
As HLEs falam com `npx.py` (§5) numa thread de rede do host; respostas e notificações viram callbacks
do NP na thread do jogo.

| API do jogo | NPX |
|---|---|
| `sceNpManagerGetStatus`/`GetOnlineId`/`GetNpId`/callback de status | HELLO + LOGIN; ONLINE quando logado |
| `sceNpManagerRequestTicket2`/`GetTicket`/`GetTicketParam` | GET_TICKET; GetTicketParam lê o formato de `ticket.py` |
| `sceNpManagerGetNetworkTime` | PING |
| `sceNpBasic*` | GET_FRIENDS, SET_PRESENCE, SEND_MESSAGE, N_FRIEND_STATUS, N_MESSAGE |
| `sceNpSignaling*` | SIG_REGISTER + ping UDP, SIG_CONNECT, N_SIG_REQUEST; fallback TURN |
| `sceNpScore*` | SCORE_RECORD, SCORE_GET_RANGE, SCORE_GET_BY_ID |
| `sceNpTus*` | TUS_SET/GET_VAR, TUS_SET/GET_DATA, TUS_DELETE |
| `sceNpLookup*` | LOOKUP_ONLINE_ID |

### 3.4 Ligar o Network Versus no port
O port controla o código, então não precisa de SPRX: um HLE/patch no código recompilado faz o que o
hook da comunidade faz (escrever a flag em HostLanLobby/JoinLanLobby). Falta descobrir pela RE qual tela
chama essas funções e o que o `patch.psarc` da comunidade muda na UI (não baixamos o mod; vamos achar
o equivalente nos psarc do próprio jogo). Configurável por `lan_mode = host | join | auto`.

### 3.5 Configuração do cliente
`online.ini` ao lado do executável (ou `ASBR_ONLINE_CONFIG`); variável de ambiente com o mesmo nome em
maiúsculas tem prioridade.

```ini
enabled = 1                    ; 0 = comportamento offline atual
server = 127.0.0.1             ; IP ou nome do servidor substituto
npx_port = 32000
dns_port = 53
online_id = Kratos_BR          ; 3-16 caracteres, começa com letra
password = troque-isto
create_account = 1
vlan_room = sala-do-samuel     ; vazio = sem LAN virtual
lan_mode = auto                ; host | join | auto
telemetry = off
port_offset = 0                ; 1, 2... para a 2a/3a instância no mesmo PC
```

## 4. Servidor substituto (`net/server`)

Python 3.10+ só com biblioteca padrão. Dentro de `net/server`: `python -m allstars_server
[--config config.json] [-v]`. Testes: `python -m unittest discover -s tests` (23 testes).

| Serviço | Porta padrão | Estado |
|---|---|---|
| NPX: contas, ticket, amigos, sinalização, placares, TUS, salas da LAN virtual | tcp+udp 32000 | pronto, testado |
| LAN virtual (túnel do Network Versus) | udp 32001 | pronto, testado |
| DNS (`*.online.scea.com` → `public_ip`, telemetria NXDOMAIN) | udp 53 | pronto, testado |
| STUN/TURN | udp 3478, relay udp 49160-49400 | pronto, testado |
| HTTP ipmapping | tcp 10012 | pronto; corpo a confirmar pela RE |
| OTG lobby | TBD | modo captura (hexdump por conexão em `captures/`) |

`public_ip` no config.json = IP pelo qual os jogadores chegam ao servidor (LAN ou público); vira o
padrão das respostas do DNS e do relay TURN. Para hospedar na internet, abrir no roteador: tcp/udp 32000,
udp 32001, udp 53 (ou o `dns_port` escolhido), udp 3478, udp 49160-49400, tcp 10012.
Banco SQLite `allstars.db`: contas (senha PBKDF2), placares e TUS.

## 5. Protocolo NPX (versão 1)

Ideia parecida com a do RPCN (TCP com comandos binários + UDP para descobrir o endereço público), mas
protocolo e código próprios. Referência: `allstars_server/wire.py`, `npx.py`, `client.py`.

**Pacote:** cabeçalho de 12 bytes little-endian `u8 kind (1 pedido, 2 resposta, 3 notificação) | u8 flags=0
| u16 command | u32 size (total) | u32 req_id`, depois o corpo (máx. 1 MiB). Toda resposta começa com
`u8 err`. `str` = u16 len + UTF-8; `blob` = u32 len + bytes; `ip4` = 4 bytes em ordem de rede;
listas = u16 count + itens.

| Cmd | Nome | Pedido | Resposta (após err) |
|---|---|---|---|
| 0x0001 | HELLO | u32 version(=1), str title_id | u32 version, ip4 seu_ip, u16 sua_porta, u64 hora_ms |
| 0x0002 | LOGIN | str online_id, str password, u8 create | u64 user_id, str online_id, blob udp_token(8), ip4 seu_ip |
| 0x0003 | LOGOUT | — | — |
| 0x0004 | PING | — | u64 hora_ms |
| 0x0010 | GET_TICKET | str service_id, blob cookie | blob ticket |
| 0x0011 | LOOKUP_ONLINE_ID | str online_id | u64 user_id, str online_id |
| 0x0020 | SET_PRESENCE | u8 status, str texto, blob dados | — |
| 0x0021 | GET_FRIENDS | — | lista {str id, u8 online, u8 status, str texto, blob dados} |
| 0x0022 | SEND_MESSAGE | str para, u16 main, u16 sub, str assunto, str texto, blob anexo | — |
| 0x0030 | SIG_REGISTER | ip4 ip_local, u16 porta_p2p_local | blob udp_token |
| 0x0031 | SIG_CONNECT | str alvo, u32 conn_id | P2P do alvo* |
| 0x0032 | SIG_GET_PEER | str alvo | P2P do alvo* |
| 0x0040 | SCORE_RECORD | u32 board, u32 pcid, i64 score, str comentário, blob game_info, u8 maior_melhor | u32 rank, u8 gravou |
| 0x0041 | SCORE_GET_RANGE | u32 board, u32 rank_inicial(1..), u16 qtd(≤100) | u32 total, lista de entradas** |
| 0x0042 | SCORE_GET_BY_ID | u32 board, u32 pcid, u16 n, n× str id | u32 total, u16 n, n× {u8 achou, [entrada**]} |
| 0x0050 | TUS_SET_VAR | str dono (vazio = eu), i32 slot, i64 valor | — |
| 0x0051 | TUS_GET_VAR | str dono, i32 slot | u8 existe, [i64 valor, u64 quem, u64 quando] |
| 0x0052 | TUS_SET_DATA | str dono, i32 slot, blob dados(≤256 KiB), blob info | — |
| 0x0053 | TUS_GET_DATA | str dono, i32 slot | u8 existe, [blob dados, blob info, u64 quem, u64 quando] |
| 0x0054 | TUS_DELETE | str dono, i32 slot | — |
| 0x0060 | VLAN_JOIN | str sala(≤32), ip4 ip_local, u16 porta_local_do_túnel | ip4 vip, ip4 máscara, ip4 broadcast, blob token(8), u16 porta_udp_do_túnel, lista {str id, ip4 vip} dos outros |
| 0x0061 | VLAN_LEAVE | — | — |
| 0x0062 | VLAN_LIST | — | lista {str sala, u8 membros, u8 máximo} |

\* P2P = `u32 conn_id, str online_id, ip4 ip_publico, u16 porta_publica, ip4 ip_local, u16 porta_local`.
\*\* entrada = `u32 rank, str online_id, u32 pcid, i64 score, str comentário, blob game_info, u64 quando`.

Notificações: `0x0100 N_FRIEND_STATUS` {str id, u8 online, u8 status, str texto, blob dados};
`0x0101 N_SIG_REQUEST` {P2P de quem pediu}; `0x0102 N_MESSAGE` {str de, u16 main, u16 sub, str assunto,
str texto, blob anexo}; `0x0104 N_VLAN_MEMBER` {str sala, str id, ip4 vip, u8 entrou}.

Erros: 0 OK, 1 MALFORMED, 2 UNKNOWN_COMMAND, 3 NOT_LOGGED_IN, 4 ALREADY_LOGGED_IN, 5 BAD_VERSION,
6 NO_SUCH_USER, 7 WRONG_PASSWORD, 8 INVALID_ONLINE_ID, 9 NOT_FOUND, 10 PEER_OFFLINE, 11 SERVER_ERROR,
12 LOGGED_IN_ELSEWHERE, 13 TOO_LARGE, 14 ROOM_FULL, 15 VLAN_DISABLED.

**UDP de descoberta (udp/32000):** da porta P2P local, `"NPXP" + udp_token(8)`; resposta
`"NPXP" + token + ip4 + u16 porta (LE)` com o endereço público visto. Repetir a cada 20 s.

**Ticket:** formato 2.1 do PS3 (big-endian, campos `u16 tipo | u16 tam`), corpo 0x3000 (serial, issuer
0x100, emissão, validade, user_id, online_id(32), região, domínio, service_id(24), status), rodapé 0x3002
com cipher_id `ASBR` e HMAC-SHA1 do servidor. Ver `ticket.py`.

## 6. LAN virtual (túnel, udp/32001)

Cada sala ganha um /24 em `10.77.0.0/16` (sala 0 = 10.77.0.0/24, sala 1 = 10.77.1.0/24...), até 8
membros (`vlan.max_members`). Cabeçalho de 12 bytes: `"AV" | u8 tipo | u8 flags | token[8]` (token do
VLAN_JOIN no sentido cliente→servidor; zeros no sentido servidor→cliente e entre pares).

| Tipo | Corpo |
|---|---|
| 1 KEEPALIVE (a cada 5 s) | cliente→servidor: vazio. Resposta: ip4 público visto, u16 porta (LE), u8 n, n× {ip4 vip, ip4 ip_pub, u16 porta_pub, ip4 ip_local, u16 porta_local} |
| 2 DATA | ip4 src_vip, ip4 dst_vip, u8 proto (0 UDP comum, 1 P2P), u16 src_port, u16 dst_port, u16 src_vport, u16 dst_vport (LE), payload |
| 3 PUNCH / 4 PUNCH_ACK | só entre pares: ip4 vip de quem manda |

O servidor reescreve `src_vip` (ninguém se passa por outro membro), manda broadcast (`255.255.255.255`
ou `.255` da sala) para todos os outros membros e unicast para o dono do `dst_vip`. Sem keepalive por
60 s, o membro sai da sala. O cliente usa a tabela de pares do KEEPALIVE para tentar o caminho direto
(PUNCH/PUNCH_ACK, mesmo IP público → endereço local) e, enquanto não houver PUNCH_ACK, manda DATA pelo
servidor. Pacotes DATA recebidos viram datagramas do socket guest certo (porta + vport de destino) com
origem `src_vip:src_port`.

## 7. Plano e estado

| Etapa | Estado |
|---|---|
| Servidor: NPX, LAN virtual, DNS, STUN/TURN, ipmapping, captura OTG (23 testes) | pronto |
| RE LAN: validar flag, quem chama HostLanLobby/JoinLanLobby, socket tipo 6, beacon, UI | em andamento |
| sys_net real + DNS desviado + DGRAM_P2P + túnel da LAN virtual + `NET_TRACE` | próximo |
| cellNetCtl online, sceNp* → NPX | depois do sys_net |
| Partida LAN virtual entre duas instâncias no mesmo PC, depois entre dois PCs | depende do jogo chegar ao combate offline |
| RE OTG: porta, cabeçalho, CryptManager, ticket, mensagens de lobby, TURN | parcial |
| Lobby OTG no servidor (Ranked/Quick Match) | depois da RE |
