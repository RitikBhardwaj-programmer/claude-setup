# Installs this Claude Code setup into ~/.claude on Windows (shared + personal parts, hooks, settings hooks).
# Safe to re-run: anything it replaces is backed up to ~/.claude/backups first.
# Usage:  powershell -ExecutionPolicy Bypass -File install.ps1 [-DryRun] [-SharedOnly]
param([switch]$DryRun, [switch]$SharedOnly)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error 'Python launcher "py" not found. Install Python 3 from python.org first.'
}
$argsList = @("$repo\scripts\install_windows.py")
if ($DryRun) { $argsList += '--dry-run' }
if ($SharedOnly) { $argsList += '--shared-only' }
$env:PYTHONIOENCODING = 'utf-8'
& py -3 @argsList
exit $LASTEXITCODE
