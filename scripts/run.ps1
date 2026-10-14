# Roda o port por N segundos e grava os logs em work\runs\<Tag>.{out,err}.log
# Uso: powershell -ExecutionPolicy Bypass -File scripts\run.ps1 [-Seconds 60] [-Tag claude-run1] [-Agent claude]
#   -Agent vazio usa build\ (integracao); com agente usa build-<agente>\
# Variaveis uteis: PORT_GSTACK="20,40" (pilhas guest), PS3_NO_SAIL=1, SPU_DUMP_MISS=<dir>
param([int]$Seconds = 60, [string]$Tag = "run", [string]$Agent = "")
$root = Split-Path $PSScriptRoot -Parent
$build = if ($Agent) { "$root\build-$Agent" } else { "$root\build" }
$logs = "$root\work\runs"
New-Item -ItemType Directory -Force $logs | Out-Null
$env:PS3_VFS_ROOT = "C:\Users\samue\Documents\[Downloadgameps3.com]PLUS\BCUS98472 - [Play Station All Stars Battle Royale]"
$p = Start-Process -FilePath "$build\MyGameRecomp.exe" `
    -ArgumentList "`"$root\work\eboot\EBOOT_1.00_disc.elf`"" `
    -WorkingDirectory "$root\work" `
    -RedirectStandardOutput "$logs\$Tag.out.log" -RedirectStandardError "$logs\$Tag.err.log" -PassThru
$null = $p.Handle  # cache the handle so ExitCode is readable after exit
$exited = $p.WaitForExit($Seconds * 1000)
if (-not $exited) { Stop-Process -Id $p.Id -Force; "killed after ${Seconds}s" } else { "exited code 0x{0:X8}" -f $p.ExitCode }
"logs: $logs\$Tag.out.log / .err.log"
