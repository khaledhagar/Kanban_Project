# Build and run the Project Management MVP container (Windows / PowerShell).
$ErrorActionPreference = "Stop"
# Make native command (docker) failures terminate the script (PowerShell 7+).
$PSNativeCommandUseErrorActionPreference = $true

$Image = "pm-mvp"
$Container = "pm-mvp"
$Port = if ($env:PORT) { $env:PORT } else { "8000" }
$Root = Split-Path -Parent $PSScriptRoot

docker build -t $Image $Root
try { docker rm -f $Container 2>$null | Out-Null } catch {}
docker run -d --name $Container -p "${Port}:8000" $Image

Write-Host "Running at http://localhost:$Port (health: http://localhost:$Port/api/health)"
