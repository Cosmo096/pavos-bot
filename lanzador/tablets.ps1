# Abre la app en el perfil secundario (--user 999).
param(
    [Parameter(Mandatory = $true)][string]$Device,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$DeviceName,
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$DisplaySize,
    [Parameter(Mandatory = $true)][int]$WindowWidth,
    [Parameter(Mandatory = $true)][int]$WindowHeight,
    [Parameter(Mandatory = $true)][int]$WindowX,
    [Parameter(Mandatory = $true)][int]$WindowY,
    [string]$Package  = "com.ankama.dofustouch",
    [string]$Activity = "com.ankama.dofustouch.MainActivity",
    [string]$User     = "999",
    [int]$TimeoutSec  = 30
)

if ([string]::IsNullOrWhiteSpace($env:SCRCPY_DIR)) {
    throw "SCRCPY_DIR no esta definido. Configuralo en .env antes de lanzar."
}
$scrcpyDir = $env:SCRCPY_DIR
$scrcpyExe = Join-Path $scrcpyDir "scrcpy.exe"
if (-not (Test-Path -LiteralPath $scrcpyExe -PathType Leaf)) {
    throw "No se encontro scrcpy.exe dentro de SCRCPY_DIR."
}
$title = $Title

# Logs locales al lanzador, compartidos con el .bat.
$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log    = Join-Path $logDir "scrcpy_${DeviceName}_${title}.log"
$logErr = Join-Path $logDir "scrcpy_${DeviceName}_${title}_err.log"
Remove-Item $log, $logErr -ErrorAction SilentlyContinue

# Cerrar la app en ese perfil si estaba abierta (equivalente al force-stop del .bat)
adb -s $Device shell am force-stop --user $User $Package
Start-Sleep -Seconds 1

Start-Process -FilePath $scrcpyExe -WorkingDirectory $scrcpyDir -ArgumentList @(
    "-s", $Device,
    "--new-display=$DisplaySize", "--no-vd-system-decorations",
    "--window-width=$WindowWidth", "--window-height=$WindowHeight", "--window-title=$title",
    "--window-x=$WindowX", "--window-y=$WindowY", "--video-codec=h265",
    "--video-codec-options=color-range=1", "-b16M", "--max-fps=100",
    "--no-audio", "--turn-screen-off","--render-driver=opengl", "-K"
) -RedirectStandardOutput $log -RedirectStandardError $logErr -NoNewWindow

# Esperar a que scrcpy reporte el ID del display (con timeout)
$displayId = $null
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while (-not $displayId -and $sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    Start-Sleep -Milliseconds 300
    $match = Select-String -Path $log, $logErr -Pattern "New display:.*\(id=(\d+)\)" -ErrorAction SilentlyContinue
    if ($match) { $displayId = $match.Matches[0].Groups[1].Value }
}

if (-not $displayId) {
    Write-Error "[$title] No se detectó el display tras $TimeoutSec s. Revisa $log / $logErr"
    exit 1
}

adb -s $Device shell am start --user $User --display $displayId -n "$Package/$Activity"