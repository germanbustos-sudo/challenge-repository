param(
  [switch]$Offline,
  [switch]$SkipInstall
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$argsList = @()
if ($Offline) { $argsList += "--offline" }
if ($SkipInstall) { $argsList += "--skip-install" }
python scripts/setup_opencode_environment.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
