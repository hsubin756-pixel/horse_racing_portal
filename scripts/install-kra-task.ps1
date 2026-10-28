# Run in Windows PowerShell. Starts WSL under the current Windows account.
param(
  [string]$Distribution = "Ubuntu",
  [string]$ProjectPath,
  [string]$At = "20:00",
  [int]$MaxCalls = 25,
  [switch]$Remove
)
$ErrorActionPreference = "Stop"
$TaskName = "KEIBA-KRA-Daily"
if ($Remove) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; exit }
if ($ProjectPath -notmatch '^/[a-zA-Z0-9_./ -]+$' -or $Distribution -notmatch '^[a-zA-Z0-9_.-]+$') { throw "WSL distribution/path contains unsupported characters." }
if ($MaxCalls -lt 1 -or $MaxCalls -gt 1000) { throw "MaxCalls must be 1..1000." }
$Time = [datetime]::ParseExact($At, "HH:mm", [System.Globalization.CultureInfo]::InvariantCulture)
$Arguments = "--distribution `"$Distribution`" --cd `"$ProjectPath`" --exec python3 scripts/kra_daily.py --max-calls $MaxCalls --apply"
$Action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $Arguments
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$Principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "KRA incremental sync; Docker Desktop must be running. No model promotion."
Write-Output "Installed: $TaskName at $At (Windows local time). Logs/status: .runtime/kra/sync/daily-YYYYMMDD.json"
