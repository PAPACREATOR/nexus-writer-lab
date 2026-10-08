$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable runner only' }
$output=Join-Path $PWD 'lab-evidence/stack-reader-check'
$null=New-Item -ItemType Directory -Path $output -Force
& $env:LAB_CDB_EXE -version > (Join-Path $output 'version.txt')
$versionExit=$LASTEXITCODE
$symbols=Join-Path $env:RUNNER_TEMP 'nexus-empty-symbols'
$null=New-Item -ItemType Directory -Path $symbols -Force
$commands=Join-Path $output 'commands.txt'
@('~* k','lm','q') | Set-Content -LiteralPath $commands -Encoding ascii
$fixture=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -ArgumentList @('-NoProfile','-Command','Start-Sleep -Seconds 60') -WindowStyle Hidden -PassThru
$fixtureHandle=$fixture.Handle
try {
 $debugger=Start-Process -FilePath $env:LAB_CDB_EXE -ArgumentList @('-pvr','-pd','-noshell','-nosqm','-y',('"'+$symbols+'"'),'-logo',('"'+(Join-Path $output 'fixture-stacks.txt')+'"'),'-c','"~* k; lm; q"','-p',([string]$fixture.Id)) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $output 'stdout.txt') -RedirectStandardError (Join-Path $output 'stderr.txt')
 $debuggerHandle=$debugger.Handle
 $finished=$debugger.WaitForExit(15000)
 if (-not $finished) { $debugger.Kill() }
 $debugger.Refresh()
 $frames=$false
 if (Test-Path (Join-Path $output 'fixture-stacks.txt')) { $frames=(Get-Content (Join-Path $output 'fixture-stacks.txt') -Raw) -match '(?mi)^\s*00\s+[0-9a-f`]+\s+[0-9a-f`]+\s+' }
 @{version_exit_code=$versionExit;fixture='Synthetic sleeping PowerShell helper, not Writer';finished=$finished;exit_code=$(if ($finished) {$debugger.ExitCode} else {$null});stack_frames_present=$frames;dump=$false;mode='non-invasive non-suspending';writer_executed=$false} | ConvertTo-Json | Set-Content (Join-Path $output 'result.json')
 if (-not $finished -or $debugger.ExitCode -ne 0 -or -not $frames) { throw 'Stack reader self-check failed; Writer is NOT RUN' }
} finally { if (-not $fixture.HasExited) { $fixture.Kill() } }
