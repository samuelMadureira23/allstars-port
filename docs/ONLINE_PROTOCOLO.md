# Online do PSASBR — protocolo (engenharia reversa da decompilação)

EBOOT 1.00 do disco, salvo indicação. Autor: `claude-net` (T-005), 14/10/2026.
Estado: **pausado** até o jogo ter uma luta jogável (decisão do Samuel). Strings e imports: `docs/ONLINE_ACHADOS.md`.
Contrato do cliente/servidor: `docs/net.md`.

Material local (fora do git, derivado do binário):
- `work/decomp_otg/` e `work/decomp_otg_n/` (nomes de import resolvidos): 792 funções do Ghidra
  (lib OTG 0x978000–0x9A0000 + blocos de rede do jogo).
- `work/decomp_lan/`, `work/decomp_lan_n/`: classe do lobby LAN (0x2FB000–0x2FF200) + leitores da flag.
- `online/notes/xrefs_otg*.txt`: xrefs de strings/RTTI.

Grau de certeza: **alta** = lido no código; **média** = inferido de padrão/comparação; **?** = hipótese.

## 0. Ferramentas e armadilhas
- O EBOOT tem **dois TOCs**: r2 = `0xC84768` (14.656 OPDs) e r2 = `0xC94760` (2.333 OPDs, incluindo a
  lib OTG e outros blocos acima de ~0x849600). `scripts/xref_str.py` assume um TOC só; para a lib OTG,
  rode com um functions.json cujo campo `toc` seja `0xC94760`. Hits fora do bloco do TOC certo são falso positivo.
  Para saber o TOC de uma função, procure o OPD `(func, toc)` no segmento de dados.
- Funções virtuais aparecem no `functions.json` do Ghidra como `.opd.FUN_*`; peça a decompilação pelo endereço
  do código.
- Comparação 1.00 ↔ 1.12: casar sequências de instruções mascarando o deslocamento de `b/bl/bc` e o
  deslocamento de loads em r2 (script de casamento no scratchpad da sessão; refazer se precisar).

## 1. Quem usa sockets (callers dos stubs sys_net)
| Bloco | Funções | Uso |
|---|---|---|
| OTG `SocketTcp` | 0x98E4D8 recv, 0x98E5B0 select, 0x98E7BC send, 0x98E908 connect | TCP do servidor OTG (alta) |
| OTG `sceotGetHostUtil` | 0x9930F8 (socket/bind), 0x9937F8, 0x993B20 (sendto), 0x993CB8 (recvfrom) | DNS próprio (alta) |
| OTG `ClientServerConnection` | 0x98A65C (inet_addr) | host literal (alta) |
| Jogo | 0x4C29B4 (gethostbyname), 0x4C2A30 (connect), send/recv 0x4C2850/0x4C2900 | TCP genérico: provável UPnP/HTTP (?) |
| Jogo | 0x4DFEF0…0x4E0090 (socket, bind, connect, sendto/recvfrom, getsockname, NID 0xC98A3146) | STUN/UPnP/Crossplay (?) |
| Jogo | 0x22A428/0x22A5BC e 0x47E924/0x47E568 (socket, bind, setsockopt, sendto, recvfrom) | UDP: candidatos ao P2P/LAN (`netTransportSAMLAN`), **não validado** |

## 2. OTG (Caminho B)
### 2.1 Transporte — alta
`SocketTcp::Connect` (0x98E908): `socket(AF_INET=2, SOCK_STREAM=1, IPPROTO_TCP=6)`,
`setsockopt(SOL_SOCKET=0xFFFF, SO_NBIO=0x1100, 1)`, sockaddr montado com `sin_family=2`, porta (be16) e IP
(be32) lidos de ponteiros passados pelo chamador; `connect` não bloqueante (errno 0x24 EINPROGRESS = ok).
Erros passam por 0x98E148 (traduz errno). **Sem TLS** (nenhum uso de cellSsl/cellHttps).

### 2.2 DNS próprio — alta
`sceotGetHostUtil` não usa `gethostbyname`:
- 0x9930F8: `socket(2, SOCK_DGRAM=2, 0)`, SO_NBIO, `bind` (porta 0, com retentativas), destino
  `sin_port = 0x35` (53), IP = `cellNetCtlGetInfo(0x13 PRIMARY_DNS)` convertido pelo NID 0xA9A079E0
  (comporta-se como `inet_aton`: 0 = falha).
- 0x9937F8: aloca um pedido (tabela de 0x31C bytes por pedido, flag de uso em +0x318), id sequencial
  (u16 em this+0x1C), monta a consulta (0x993FA4) e registra o horário.
- 0x993B20: `sendto(sock, pedido+4, 0x200, 0, &dns, 16)` com retransmissão por tempo; 0x993CB8: `recvfrom`.
Consequência: o port precisa devolver um DNS válido em PRIMARY_DNS e responder às consultas (mini-DNS do
`net/server`, ou desviar `sendto :53`).

### 2.3 ClientServerConnection — alta (parcial)
- Host (string) em this+0x34. Se começa com dígito → `inet_addr`, IP em this+0x3C, estado 4.
  Senão resolve pelo `sceotGetHostUtil` (estado 8) ou falha (estado 10).
- Máquina de estados em this+0x5C (0..10); despacho 0x98A748 via tabela 0x98A784
  (handlers 0x98A7B0, 0x98A7CC, 0x98A7DC, 0x98A7F8, 0x98A808, 0x98A818, 0x98A828, 0x98A878).
- OnConnect (0x98A38C): escolhe um dos IPs resolvidos (round-robin pelo resto da divisão) e vai ao estado 4;
  erro: "Hostname resolution for %s failed".
- Seletor de host prod/teste: 0x30085C (lê `battleroyale-p4/final.ps3.online.scea.com`, TOC 0xC813F8/0xC813FC);
  TURN em 0x300928 (0xC81408/0xC81410). Hosts em 0xB21F00–0xB21FD0.

### 2.4 Pendente
- **Porta TCP** do servidor principal (procurar quem preenche o ponteiro de porta passado a 0x98E908).
- **Cabeçalho das mensagens** (InetSendBuffer/InetRecvBuffer, RTTI 0xB478A0/0xB47698; xref de
  "SymmetricDecrypt failed" em 0x98D178).
- **CryptManager** (RTTI 0xB47680; string `setCryptKeys` 0xB12308): algoritmo e origem da chave.
  Primeira varredura de constantes achou candidatos em 0x9903A0, 0x9907E0, 0x990848, 0x9915FC (não lidos).
- Ticket NP no handshake; mensagens de lobby/MatchStyle; STUN/TURN (magic 0x2112A442); ipmapping.
- Telemetria usa o mesmo `ClientServerConnect` (strings coladas; ?). Pode ser bloqueada (NXDOMAIN).

## 3. LAN "Network Versus" (Caminho A)
### 3.1 Funções — alta
| 1.12 (CircleButton) | 1.00 | Evidência |
|---|---|---|
| HostLanLobby 0x313354 | **0x2FE00C** | 33/48 instruções iguais (mascarando branch/TOC) |
| JoinLanLobby 0x3136BC | **0x2FE36C** | 48/48 |
| g_VersusLanFlag 0x022870C4 (BSS) | **0x0223FFA8** (BSS, byte; TOC 0xC7DC14) | trecho do leitor 24/24 |

- As duas funções só são referenciadas pelos OPDs 0xC62968/0xC62970, que estão numa **vtable** em
  0xC3D808… (slots 0xC3D8E0 = Join, 0xC3D8E8 = Host; vizinhos 0x2FB6F0…0x2FE36C = métodos da mesma classe).
  A classe não tem RTTI. O código do lobby fica em `Networking\netTransportSAMLAN.cpp` (string 0xB21C28).
- Leitores da flag no 1.00: 0xC55E0 (função 0xC4E60; antes compara um hash com `0x75606733` e, se a flag
  for 0, desvia para 0xC5D5C) e 0x8E54A8 (função 0x8E537C). No 1.12 o leitor equivalente é 0xC64A8.
- **Correção:** a global 0x025332F8 (TOC 0xC813D0) que HostLanLobby testa logo no início **não é** a flag
  (no 1.12 ela corresponde a 0x0257A478). A estimativa anterior estava errada.
- A classe do lobby chama `cellNetCtlGetInfo` (3×), `cellNetCtlGetState`, `cellSysutilGetSystemParamString`
  e `sceNpBasicSendMessage` (2×).

### 3.2 Pendente
- Quem chama os slots 0xC3D8E0/0xC3D8E8 da vtable (tela/menu do "Network Versus"); o que 0xC4E60 e 0x8E537C
  fazem com a flag.
- Validar no 1.00: `socket(…, type 6 DGRAM_P2P)`, porta UDP 3658, vport 1000, broadcast, beacon
  `00 00 00 00 08 45 71 29`, formato das mensagens de lobby LAN.
- O que o `patch.psarc` da comunidade muda na UI (procurar o equivalente nos psarc do jogo com
  `tools/psarc_extract.py`, local).
