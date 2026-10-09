param([string]$Metadata,[string]$Stacks)
$ErrorActionPreference='Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub runner only' }
$output=Join-Path $PWD 'lab-evidence'
$null=New-Item -ItemType Directory -Path $output -Force
$python=(Get-Command python).Source
$start=[DateTime]::UtcNow
# Only an offline file reader: no PID, process attach, memory dump or Writer.
$arguments=@('-m','lab.resolve_writer_frames')
if($Metadata) { $arguments+=@('--metadata',('"'+$Metadata+'"')) }
if($Stacks) { $arguments+=@('--stacks',('"'+$Stacks+'"')) }
$helper=Start-Process -FilePath $python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $output 'resolved-writer-frames.stdout.txt') -RedirectStandardError (Join-Path $output 'resolved-writer-frames.stderr.txt')
$handle=$helper.Handle
$finished=$helper.WaitForExit(120000)
if(-not $finished) { $helper.Kill(); $helper.WaitForExit() }
$helper.Refresh()
@{finished=$finished;exit_code=$(if($finished){$helper.ExitCode}else{$null});duration_seconds=([DateTime]::UtcNow-$start).TotalSeconds;timeout_seconds=120;writer_execution=$false;process_attach=$false;memory_dump=$false;inputs='Installed PE, public PDB and persisted stack text only'} | ConvertTo-Json | Set-Content (Join-Path $output 'resolved-writer-frames-reader.json')
if(-not $finished) { throw 'Offline symbols reader timed out; preserve diagnostic evidence' }
if($helper.ExitCode -ne 0) {
    $stdout=Join-Path $output 'resolved-writer-frames.stdout.txt'
    $stderr=Join-Path $output 'resolved-writer-frames.stderr.txt'
    if(Test-Path -LiteralPath $stdout) {
        Write-Host '=== offline resolver stdout (tail) ==='
        Get-Content -LiteralPath $stdout -Tail 80
    }
    if(Test-Path -LiteralPath $stderr) {
        Write-Host '=== offline resolver stderr (tail) ==='
        Get-Content -LiteralPath $stderr -Tail 80
    }
    throw 'Offline symbol binding or resolution failed; preserve diagnostic evidence'
}
