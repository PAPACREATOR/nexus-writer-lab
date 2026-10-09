param([string]$Output,[string]$StopFile,[string]$PythonRoot,[string]$Debugger)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$null=New-Item -ItemType Directory -Path $Output -Force
$symbols=Join-Path $env:RUNNER_TEMP 'nexus-empty-symbols-lok'
$null=New-Item -ItemType Directory -Path $symbols -Force
@('~* k','lm','q') | Set-Content -LiteralPath (Join-Path $Output 'commands.txt') -Encoding ascii
$seen=@{}
$deadline=[DateTime]::UtcNow.AddMinutes(20)
while (-not (Test-Path -LiteralPath $StopFile) -and [DateTime]::UtcNow -lt $deadline) {
  foreach ($p in @(Get-Process -Name python -ErrorAction SilentlyContinue)) {
    try {
      $path=$p.Path
      if (-not $path -or -not $path.StartsWith($PythonRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { continue }
      $row=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id) -ErrorAction Stop
      $command=[string]$row.CommandLine
      if ($command -notmatch 'writer_lok_probe\.py') { continue }
      $age=([DateTime]::Now-$p.StartTime).TotalSeconds
      foreach ($threshold in @(10,25)) {
        $key=([string]$p.Id)+'-'+$threshold
        if ($age -lt $threshold -or $seen.ContainsKey($key)) { continue }
        $seen[$key]=$true
        $log=Join-Path $Output ($key+'.stacks.txt')
        $start=[DateTime]::UtcNow
        $args=@('-pvr','-noshell','-nosqm','-y',('"'+$symbols+'"'),'-logo',('"'+$log+'"'),'-c','"~* k; lm; q"','-p',([string]$p.Id))
        $helper=Start-Process -FilePath $Debugger -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput ($log+'.stdout.txt') -RedirectStandardError ($log+'.stderr.txt')
        $heldHandle=$helper.Handle
        $finished=$helper.WaitForExit(8000)
        if (-not $finished) { $helper.Kill(); $helper.WaitForExit() }
        $helper.Refresh()
        @{utc=$start.ToString('o');pid=$p.Id;image=$path;command_line=$command;threshold_seconds=$threshold;finished=$finished;duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;exit_code=$(if($finished){$helper.ExitCode}else{$null});mode='non-invasive non-suspending -pvr';payload='stack frames and module list text only';memory_dump=$false;clone=$false;runtime_changes=@()} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'capture.jsonl')
      }
    } catch {
      @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'errors.jsonl')
    }
  }
  Start-Sleep -Seconds 1
}
