<# CPU-only local video emotion inference. 姓名: FANXUYANG; 日期: 2026-10-25 #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Video,
    [Parameter(Mandatory=$true)][string]$Output,
    [string]$Upstream = '../video-emotion',
    [string]$Runtime = 'runs/vemoclap-runtime',
    [int]$Timeout = 1200,
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
function ProjectPath([string]$PathValue) {
    return [System.IO.Path]::GetFullPath($PathValue, $projectRoot)
}
$runtimeRoot = ProjectPath $Runtime
$modelPython = Join-Path $runtimeRoot 'venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $modelPython -PathType Leaf)) {
    throw 'Prepare the independent CPU environment first; see docs/vemoclap.md.'
}
$env:PYTHONPATH = Join-Path $projectRoot 'src'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$arguments = @('-m', 'moodcut.vemoclap', '--video', (ProjectPath $Video),
               '--upstream', (ProjectPath $Upstream), '--python', $modelPython,
               '--output', (ProjectPath $Output), '--cache-dir', $runtimeRoot,
               '--source-kind', 'provided_local', '--timeout', $Timeout)
if ($Check) { $arguments += '--check' } else { $arguments += '--run' }
& $modelPython @arguments
exit $LASTEXITCODE
