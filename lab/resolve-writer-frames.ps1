param([string]$Metadata,[string]$Stacks,[string]$RvaEvents,[string]$Report='lab-evidence/resolved-writer-frames.json')
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner only' }
$output=Join-Path $PWD 'lab-evidence'
$null=New-Item -ItemType Directory -Path $output -Force
$python=(Get-Command python).Source
$start=[DateTime]::UtcNow
# Only an offline file reader: no PID, process attach, memory dump or Writer.
$arguments=@('-m','lab.resolve_writer_frames')
$arguments+=@('--output',('"'+$Report+'"'))
if($Metadata) { $arguments+=@('--metadata',('"'+$Metadata+'"')) }
if($Stacks) { $arguments+=@('--stacks',('"'+$Stacks+'"')) }
if($RvaEvents) { $arguments+=@('--rva-events',('"'+$RvaEvents+'"')) }
$logBase=Join-Path $output ([IO.Path]::GetFileNameWithoutExtension($Report))
$helper=Start-Process -FilePath $python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput ($logBase+'.stdout.txt') -RedirectStandardError ($logBase+'.stderr.txt')
$handle=$helper.Handle
$finished=$helper.WaitForExit(120000)
if(-not $finished) { $helper.Kill(); $helper.WaitForExit() }
$helper.Refresh()
@{finished=$finished;exit_code=$(if($finished){$helper.ExitCode}else{$null});duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;timeout_seconds=120;writer_execution=$false;process_attach=$false;memory_dump=$false;report=$Report;rva_events=$RvaEvents;inputs='Installed PE, public PDB and persisted stack text only'} | ConvertTo-Json | Set-Content ($logBase+'-reader.json')
if(-not $finished) { throw 'Offline symbols reader timed out; preserve diagnostic evidence' }
if($helper.ExitCode -ne 0) { throw 'Offline symbol binding or resolution failed; preserve diagnostic evidence' }
