$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$output=Join-Path $PWD 'lab-evidence/standard-user-launch/dumps'
$cache=Join-Path $env:RUNNER_TEMP 'nexus-microsoft-symbols'
$commands=Join-Path $env:RUNNER_TEMP 'nexus-dump-commands.txt'
@('.reload','~* kb','lm','q') | Set-Content -LiteralPath $commands -Encoding ascii
foreach ($dump in @(Get-ChildItem -LiteralPath $output -Filter '*.dmp' -ErrorAction SilentlyContinue)) {
 $log=$dump.FullName+'.stacks.txt'
 $helper=Start-Process -FilePath $env:LAB_CDB_EXE -ArgumentList @('-z',('"'+$dump.FullName+'"'),'-y',('"srv*'+$cache+'*https://msdl.microsoft.com/download/symbols"'),'-logo',('"'+$log+'"'),'-cf',('"'+$commands+'"')) -WindowStyle Hidden -PassThru -RedirectStandardOutput ($log+'.stdout.txt') -RedirectStandardError ($log+'.stderr.txt')
 $finished=$helper.WaitForExit(120000)
 if (-not $finished) { $helper.Kill() }
 @{dump=$dump.Name;sha256=(Get-FileHash -LiteralPath $dump.FullName -Algorithm SHA256).Hash;finished=$finished;exit_code=$(if ($finished) {$helper.ExitCode} else {$null});analysis='offline only; no live attach';symbols='Microsoft public server'} | ConvertTo-Json -Compress | Add-Content (Join-Path $output 'analysis.jsonl')
}
