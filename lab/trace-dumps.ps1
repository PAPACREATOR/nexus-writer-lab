param([string]$Output,[string]$StopFile,[string]$WriterRoot,[string]$DumpExe)
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$null=New-Item -ItemType Directory -Path $Output -Force
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
    $file=Join-Path $Output ($key+'.dmp')
    $start=[DateTime]::UtcNow
    $helper=Start-Process -FilePath $DumpExe -ArgumentList @('-accepteula','-mm','-at','5',([string]$p.Id),('"'+$file+'"')) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $Output ($key+'-dump.txt')) -RedirectStandardError (Join-Path $Output ($key+'-error.txt'))
    $finished=$helper.WaitForExit(8000)
    if (-not $finished) { $helper.Kill() }
    @{utc=$start.ToString('o');pid=$p.Id;image=$path;age_seconds=$age;threshold_seconds=$threshold;finished=$finished;duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;dump_exists=(Test-Path -LiteralPath $file);exit_code=$(if ($finished) {$helper.ExitCode} else {$null});type='mini';clone=$false;runtime_changes=@()} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'capture.jsonl')
   }
  } catch { @{utc=[DateTime]::UtcNow.ToString('o');pid=$p.Id;error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content (Join-Path $Output 'errors.jsonl') }
 }
 Start-Sleep -Seconds 1
}
