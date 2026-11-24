param(
    [string]$Python = 'python',
    [string]$Output = 'out\hakios-bangkk.img',
    [string]$Payload,
    [switch]$Boot
)

$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Repo

function Require-File([string]$Path, [string]$Purpose) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Falta ${Purpose}: $Path"
    }
}

$pythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "No encuentro Python ($Python). Instala Python 3 y vuelve a ejecutar este script."
}

$deviceFiles = 'devices\moto-g84\prebuilt'
foreach ($name in @('BootShim.bin', 'SILICIUM_UEFI.fd', 'device-tree.dtb', 'ramdisk', 'mkbootimg.py')) {
    Require-File (Join-Path $deviceFiles $name) "el componente UEFI/DTB propio de bangkk ($name)"
}

$outPath = if ([System.IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $Repo $Output }
$outDir = Split-Path -Parent $outPath
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$payloadPath = $null
if ($Payload) {
    $payloadPath = (Resolve-Path -LiteralPath $Payload).Path
    Require-File $payloadPath 'el payload XNUP descargado de Actions'
} else {
    $kernel = 'prebuilt\hakios-kernel'
    $ramdisk = 'prebuilt\userland\hello'
    Require-File $kernel 'el kernel precompilado'
    Require-File $ramdisk 'el ramdisk hello precompilado'
    $payloadPath = Join-Path $outDir 'bangkk-payload.bin'

    $cmdline = & $Python 'tools\hakios-config.py' args --defconfig moto-g84_defconfig
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener la línea de arranque de defconfig.' }
    $cmdline = ($cmdline -join ' ').Trim()
    $socArgs = Get-Content -LiteralPath 'devices\moto-g84\soc.args' -Raw
    $cmdline = "$cmdline $socArgs".Trim()

    & $Python 'xnuloader\mkpayload.py' -o $payloadPath "kernel=$kernel" "ramdisk=$ramdisk" --cmdline $cmdline
    if ($LASTEXITCODE -ne 0) { throw 'Falló la creación del payload XNUP.' }
}

& $Python 'mkxnuimg.py' --device moto-g84 -p $payloadPath -o $outPath
if ($LASTEXITCODE -ne 0) { throw 'Falló el empaquetado de la imagen de arranque.' }
Write-Host "Imagen lista: $((Resolve-Path $outPath).Path)"

if ($Boot) {
    $fastboot = Get-Command fastboot -ErrorAction SilentlyContinue
    if (-not $fastboot) { throw 'No encuentro fastboot. Instala Android platform-tools y agrega su carpeta al PATH.' }
    & $fastboot.Source devices
    if ($LASTEXITCODE -ne 0) { throw 'fastboot no pudo consultar el dispositivo.' }
    Write-Warning 'Se usará fastboot boot: arranque temporal desde RAM; este script nunca flashea particiones.'
    & $fastboot.Source boot (Resolve-Path $outPath).Path
    if ($LASTEXITCODE -ne 0) { throw 'fastboot boot falló.' }
}
