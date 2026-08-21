# Windows Task Scheduler kurulum scripti
# PowerShell'de calistir: .\scripts\setup_task.ps1

$PythonPath  = (Get-Command python).Source
$ClaudePath  = (Get-Command claude -ErrorAction SilentlyContinue).Source
$ProjectDir  = (Resolve-Path "$PSScriptRoot\..").Path
$ScriptPath  = Join-Path $ProjectDir "main.py"
$TaskName    = "Ulak_Haberlesme_Haftalik_Rapor"
$TriggerGun  = "Monday"
$TriggerSaat = "08:00"

if (-not $ClaudePath) {
    Write-Host "HATA: 'claude' komutu bulunamadi. Claude Code CLI kurulu mu?" -ForegroundColor Red
    exit 1
}

# claude.exe'nin bulundugu klasoru PATH'e ekleyen wrapper script
$WrapperPath = Join-Path $ProjectDir "scripts\run_report.ps1"
@"
`$env:PATH = "$([System.IO.Path]::GetDirectoryName($ClaudePath));`$env:PATH"
Set-Location "$ProjectDir"
& "$PythonPath" "$ScriptPath"
"@ | Set-Content -Path $WrapperPath -Encoding UTF8

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$WrapperPath`"" `
    -WorkingDirectory $ProjectDir

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek $TriggerGun `
    -At $TriggerSaat

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Gorevi mevcut kullanici olarak kaydet (PATH dogru olsun diye)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Ulak Haberlesme haftalik haber raporu - her Pazartesi 08:00" `
    -Force | Out-Null

Write-Host "Gorev olusturuldu : $TaskName" -ForegroundColor Green
Write-Host "Zamanlama         : Her Pazartesi $TriggerSaat" -ForegroundColor Cyan
Write-Host "Python            : $PythonPath" -ForegroundColor Gray
Write-Host "Claude CLI        : $ClaudePath" -ForegroundColor Gray
Write-Host "Proje klasoru     : $ProjectDir" -ForegroundColor Gray
