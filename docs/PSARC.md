# Extrator PSARC — T-004 / astra

Implementação: `tools/psarc_extract.py`. Validada nos **48 pacotes do disco
BCUS98472 1.00**, com **33.552 entradas**, em 14/10/2026.

## Resultado observado

| Verificação | Resultado |
| --- | --- |
| Manifest de global.psarc | 2.403 bytes, 70 nomes |
| Nomes dos manifests contra MD5 das tabelas | Todos conferem |
| Leitura completa dos 48 pacotes | 33.552 entradas, 3.691.348.922 bytes decodificados, zero erros |
| Blocos de recursos criptografados/comprimidos | 82.455, tamanho e Adler-32 conferidos |
| Blocos de recursos armazenados sem compressão | 25, tamanho conferido |
| Extração real de global.psarc | 70 arquivos, 25.610.876 bytes |
| Testes automatizados | 16 passaram (13 novos + 3 do indexador anterior) |

As contagens de blocos acima excluem os manifests, decodificados e validados
separadamente. Entradas em pacotes distintos podem se referir ao mesmo nome;
33.552 não é uma contagem de recursos únicos do jogo.

## Formato e evidência

O ponto de partida foi o HLE do Claude em `src/allstars-ps3/stubs.cpp`, commit
de integração `0405f5c`. O extrator independente lê a tabela PSARC v1.4, flags=2,
entradas de 30 bytes e blocos de 65.536 bytes. O primeiro arquivo é o manifest.

Bloco comprimido observado: cabeçalho de dois bytes, seguido de AES-256-CTR.
O conteúdo decifrado contém raw deflate **e um trailer Adler-32 big-endian de
quatro bytes**. O trailer foi confirmado em todos os blocos comprimidos da
verificação completa; o extrator valida esse checksum em vez de ignorá-lo.
Ele não usa fallback de dados inválidos para bloco cru.

O nonce usa o prefixo lido da imagem SPU, tamanho armazenado do bloco em be32,
dois bytes zero e o cabeçalho. O contador final de 32 bits inicia em zero.
Quando o tamanho armazenado coincide com o tamanho esperado, o bloco é cru.
O valor zero na tabela u16 significa 65.536 bytes.

## Material criptográfico

O perfil aceita somente o ELF 1.00 com SHA-256:
`a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5`.

O leitor resolve PT_LOAD do PPU e depois PT_LOAD do ELF SPU embutido em
VA `0xB9F980`. Lê em memória os dados de LS `0x114C0` (chave), `0x114B0`
(prefixo) e `0x114A6` (flag). Não grava nem imprime esses valores.
Os endereços são metadados do perfil, não material criptográfico.
ELF 1.12 é rejeitado explicitamente: esse perfil não foi validado aqui.

Os testes usam material sintético claramente identificado, sem copiar a chave
do jogo. Não houve download, instalação, rede ou alteração de EBOOT/runtime.

## Uso

Execute na raiz `C:\Users\samue\Documents\All star port`, usando o ambiente existente:

```powershell
$usrdir = 'C:\Users\samue\Documents\[Downloadgameps3.com]PLUS\BCUS98472 - [Play Station All Stars Battle Royale]\PS3_GAME\USRDIR'

# Listar nomes e metadados; não extrai os recursos.
.\.venv\Scripts\python.exe tools\psarc_extract.py index $usrdir --elf work\eboot\EBOOT_1.00_disc.elf --report reports\psarc-index.json

# Decodificar tudo e registrar SHA-256 por arquivo, sem materializar recursos.
.\.venv\Scripts\python.exe tools\psarc_extract.py verify $usrdir --elf work\eboot\EBOOT_1.00_disc.elf --report reports\psarc-validation.json

# Extrair um pacote para uma pasta NOVA. O destino usado no teste já existe.
.\.venv\Scripts\python.exe tools\psarc_extract.py extract "$usrdir\global.psarc" --elf work\eboot\EBOOT_1.00_disc.elf --output analysis\psarc-astra\global-novo --report analysis\psarc-astra\global-novo.json

.\.venv\Scripts\python.exe -m unittest discover -s tools -p 'test_psarc*.py' -v
```

## Arquivos produzidos e garantias

- `reports/psarc-index.json`: índice atualizado com nomes, offsets, tamanhos,
  hash do pacote, hash do manifest e MD5 verificados.
- `reports/psarc-index-before-t004.json`: índice anterior preservado.
- `reports/psarc-validation.json`: verificação completa e SHA-256 dos recursos.
- `reports/psarc-tests.txt`: execução dos 16 testes.
- `analysis/psarc-astra/global/`: extração local dos 70 arquivos.
- `analysis/psarc-astra/global-extraction.json`: relatório da extração.

Os diretórios analysis/reports estão fora do versionamento. Os dados de entrada
são abertos somente para leitura. A extração recusa pasta existente, caminhos
com traversal, drives, UNC, nomes de dispositivos Windows, reparse points no
destino e colisões de nomes/arquivo-diretório. O '/' inicial dos manifests é
tratado como raiz virtual do pacote, nunca como raiz do computador.

Em caso de erro, o comando termina com código diferente de zero e o relatório
registra a falha. Uma extração interrompida pode deixar arquivos parciais na
pasta nova; ela não é reutilizada automaticamente. Os relatórios completos
de sucesso têm status `verified`.

## Limites

Esta verificação comprova decodificação, tamanhos, manifests e checksums nos
pacotes locais. Não comprova semântica/renderização de texturas, modelos,
scripts ou animações. Não altera o boot e não testa gameplay. Adler-32 detecta
erros, mas não é autenticação criptográfica; SHA-256 dos recursos é identidade
calculada localmente, sem comparação com uma referência externa.
