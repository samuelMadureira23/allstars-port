# Online do PSASBR — achados da análise estática (EBOOT 1.00, disco)

Fonte: `work/eboot/EBOOT_1.00_disc.elf` (SHA-256 `a9de806a…09b5`). Offsets = endereço virtual das strings no ELF.
Tudo abaixo é **observação estática** (strings + tabela de imports); o comportamento ainda precisa ser confirmado no código (Ghidra/REA) e em execução (RPCS3).

## 1. O jogo NÃO usa o matchmaking padrão da PSN
- Não importa `sceNpMatching2` (o que o RPCN emula). Por isso o RPCN sozinho não faz o online funcionar.
- Imports de rede (ver `imports_1.00.md`):
  - `sys_net`: socket, connect, bind, listen, accept, send/recv, sendto/recvfrom, gethostbyname (TCP **e** UDP)
  - `cellHttp` (14), `cellNetCtl` (10), `cellVoice` (15)
  - `sceNpSignaling*` (conexão P2P/NAT), `sceNpBasic*` (presença, convites, amigos)
  - `sceNpScore*` (ranking), `sceNpTus*` (armazenamento por usuário), `sceNpLookup*`, `sceNpManagerGetTicket`/`RequestTicket2` (ticket de autenticação PSN)

## 2. Servidores da Sony (OTG = Online Technology Group) — todos desligados
| Host | Papel provável |
|---|---|
| `battleroyale-final.ps3.online.scea.com` (prod) / `battleroyale-p4.ps3.online.scea.com` (teste) | servidor principal: lobby/matchmaking |
| `battleroyale-final.turn1/turn2.online.scea.com` | relays TURN (NAT traversal / relay de tráfego) |
| `battleroyale-final.telemetry.online.scea.com` | telemetria (dispensável) |
| `http://ipmapping-prod.online.scea.com:10012/ipmapping-rest/otgc/IPMapping/battleroyale/location` | geolocalização por IP (REST) |

Biblioteca cliente embutida: `sceotClientServerConnectService` (build `tags/1.60/NIGHTLY/20120914_1222`), classes `otg::ClientServerConnect`, `ClientServerConnection`, `SocketTcp`, `CryptManager` (→ tráfego provavelmente **criptografado**), `InetSendBuffer/InetRecvBuffer`, `sceotGetHostLookup*`.

## 3. Partidas: peer-hosted
- `MatchStyle_None / Server / Client / ClientWithWait / Auto / WaitPartyGame` → um console vira "Server" (host) e os outros "Client".
- Strings de lobby: `Lobby Entry[%d] %d/%d:%s%s : %d.%d.%d.%d:%d`, `Create Server` (vaddr 0xb1c7d0; xrefs em 0xe55e0, 0x8f6e84, 0x8f70bc), `Wait For Server`, `Waiting For Session`.
  → Possível tela de lobby de debug com IP direto — investigar.
- ~~`-s[ServerName]`~~: **não é online**. É uma opção de linha de comando da engine (`Same connection server name`, a conexão com o editor "Same" da SuperBot). A ajuda completa fica em `FUN_0001b188`: `-f`, `-w`, `-h`, `-r`, `-nv`, `-u`, `-s`, `-i [InitialWorld]`, `-vf`/`-vc [lua vars]`, `-aw [HWND]` (viewport do Maya), `-g [guid]`.
  → `-i [InitialWorld]` e `-vc [ScriptVars]` podem ser úteis para pular menus e carregar uma fase direto no port.
- Seleção de host prod/teste (`battleroyale-final/p4.ps3.online.scea.com`): código em `0x300898` / `0x3008e0` (`FUN_0030085c`).
- Endereços: as strings da seção 2 foram listadas por offset do arquivo; vaddr = offset + 0x10000.
- Netcode: `SequenceRelay`, `RelayBank`, `Send Sequence`/`Receive Sequence`, "frame resume failed, client and server are too out of sync".
- UPnP próprio (`AddPortMapping`/`DeletePortMapping`, SSDP `239.255.255.250:1900`) e `Crossplay STUN` (cross-play com Vita).

## 4. Estratégia proposta
1. **Ghidra/REA:** achar os xrefs de `MatchStyle_*`, `Lobby Entry`, `-s[ServerName]`, `Create Server` → entender o fluxo do host e do cliente e ver se existe caminho de conexão direta.
2. **Protocolo OTG:** decompilar `otg::ClientServerConnection` + `CryptManager` → documentar o formato das mensagens TCP.
3. **Servidor substituto:** escrever um servidor de lobby/matchmaking (+ TURN padrão, ex.: coturn) que fale esse protocolo.
4. **Testar primeiro no RPCS3:** nas configurações de rede do RPCS3, em "IP/Hosts switches", apontar `battleroyale-final.ps3.online.scea.com` para o nosso servidor. Assim o online pode funcionar **antes** do port nativo ficar pronto, e o mesmo servidor serve depois para o port.
