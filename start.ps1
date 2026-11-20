$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv-win\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Environment .venv-win is missing. Run: py -3.12 -m venv .venv-win"
}

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -in @("python.exe", "pythonw.exe") -and
        $_.CommandLine -match [regex]::Escape($PSScriptRoot) -and
        $_.CommandLine -match "(realtime_simulation\.py|realtime_terminal\.py|scientific_ui\.py)"
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    }

New-Item -ItemType Directory -Force "live", "logs", "output" | Out-Null
Remove-Item "live\simulation.csv", "live\simulation.json", "logs\scenario-terminal.log" `
    -Force -ErrorAction SilentlyContinue

$Simulation = Start-Process -FilePath $Python -ArgumentList "`"$PSScriptRoot\realtime_simulation.py`"" `
    -WorkingDirectory $PSScriptRoot -PassThru

$Deadline = (Get-Date).AddSeconds(20)
while (-not (Test-Path "$PSScriptRoot\live\simulation.csv") -and (Get-Date) -lt $Deadline) {
    Start-Sleep -Milliseconds 250
}
if (-not (Test-Path "$PSScriptRoot\live\simulation.csv")) {
    Stop-Process -Id $Simulation.Id -ErrorAction SilentlyContinue
    throw "The simulation did not create live\simulation.csv within 20 seconds."
}

$Terminal = Start-Process -FilePath $Python -ArgumentList "`"$PSScriptRoot\realtime_terminal.py`"" `
    -WorkingDirectory $PSScriptRoot -PassThru
$Dashboard = Start-Process -FilePath $Python -ArgumentList "`"$PSScriptRoot\scientific_ui.py`"" `
    -WorkingDirectory $PSScriptRoot -PassThru -Wait

Stop-Process -Id $Simulation.Id -ErrorAction SilentlyContinue
Stop-Process -Id $Terminal.Id -ErrorAction SilentlyContinue
