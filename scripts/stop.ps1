# Stop and remove the Project Management MVP container (Windows / PowerShell).
$ErrorActionPreference = "Stop"

$Container = "pm-mvp"

docker rm -f $Container 2>$null | Out-Null
Write-Host "Stopped and removed $Container"
