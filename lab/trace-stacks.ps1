param([string]$Output,[string]$StopFile,[string]$WriterRoot,[string]$Debugger)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$null=New-Item -ItemType Directory -Path $Output -Force
$symbols=Join-Path $env:RUNNER_TEMP 'nexus-empty-symbols'
$null=New-Item -ItemType Directory -Path $symbols -Force
$commands=Join-Path $Output 'commands.txt'
@('~* k','lm','q') | Set-Content -LiteralPath $commands -Encoding ascii
$seen=@{}
$deadline=[DateTime]::UtcNow.AddMinutes(20)
while (-not (Test-Path -LiteralPath $StopFile) -and [DateTime]::UtcNow -lt $deadline) {
 foreach ($p in @(Get-Process -Name soffice,soffice.bin,soffice.com -ErrorAction SilentlyContinue)) {
  try {
   $path=$p.Path
   if (-not $path -or -not $path.StartsWith($WriterRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { continue }
   $age=([DateTime]::Now-$p.StartTime).TotalSeconds
   foreach ($threshold in @(10,25)) {
    $key=([string]$p.Id)+'-'+$threshold
    if ($age -lt $threshold -or $seen.ContainsKey($key)) { continue }
    $seen[$key]=$true
    $log=Join-Path $Output ($key+'.stacks.txt')
    $start=[DateTime]::UtcNow
    # Non-invasive, non-suspending read. Stack-only text; no .dump or memory display.
    $helper=Start-Process -FilePath $Debugger -ArgumentList @('-pvr','-pd','-noshell','-nosqm','-y',('"'+$symbols+'"'),'-logo',('"'+$log+'"'),'-c','"~* k; lm; q"','-p',([string]$p.Id)) -WindowStyle Hidden -PassThru -RedirectStandardOutput ($log+'.stdout.txt') -RedirectStandardError ($log+'.stderr.txt')
    $heldHandle=$helper.Handle
    $finished=$helper.WaitForExit(8000)
    if (-not $finished) { $helper.Kill() }
    $helper.Refresh()
    @{utc=$start.ToString('o');pid=$p.Id;image=$path;age_seconds=$age;threshold_seconds=$threshold;finished=$finished;duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;exit_code=$(if ($finished) {$helper.ExitCode} else {$null});mode='non-invasive non-suspending -pvr';payload='stack frames and module list text only';memory_dump=$false;clone=$false;runtime_changes=@();non_atomic_observation=$true} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'capture.jsonl')
   }
  } catch { @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'errors.jsonl') }
 }
 Start-Sleep -Seconds 1
}
