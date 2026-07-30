[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$Source,
    [string]$PetsRoot,
    [string]$BackupRoot,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $PSScriptRoot "install.py"
if (-not $Source) {
    $Source = Join-Path $projectRoot "pet"
}

$arguments = @($installer, "--source", $Source)
if ($PetsRoot) {
    $arguments += @("--pets-root", $PetsRoot)
}
if ($BackupRoot) {
    $arguments += @("--backup-root", $BackupRoot)
}
if ($Json) {
    $arguments += "--json"
}

& $Python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "RobotExpressive installation failed with exit code $LASTEXITCODE."
}
