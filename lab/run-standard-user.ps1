param([string]$Suite='routes',[int]$Shard=0,[ValidateSet('separate','python-read-root')][string]$OfficeLayout='separate')
$ErrorActionPreference='Stop'
if (-not $env:GITHUB_ACTIONS) { throw 'Disposable GitHub runner only; never create this account on the user PC' }
$source=(Get-Location).Path
$pythonRoot=& python -c 'import sys; print(sys.prefix)'
$officeRoot=Split-Path (Split-Path $env:LIBREOFFICE_EXE -Parent) -Parent
$name='NexusWriterLab'
$secret=[guid]::NewGuid().ToString('N')+'aA!9'
$secure=ConvertTo-SecureString $secret -AsPlainText -Force
$null=New-LocalUser -Name $name -Password $secure -Description 'Disposable Writer laboratory user'
$users=Get-LocalGroup -SID 'S-1-5-32-545'
Add-LocalGroupMember -Group $users -Member $name
$credential=New-Object System.Management.Automation.PSCredential("$env:COMPUTERNAME\$name",$secure)
$output=Join-Path $source 'lab-evidence/standard-user-launch'
$null=New-Item -ItemType Directory -Path $output -Force
$arguments=@('-NoProfile','-File',('"'+(Join-Path $source 'lab/user-bootstrap.ps1')+'"'),'-SourceRoot',('"'+$source+'"'),'-PythonRoot',('"'+$pythonRoot+'"'),'-OfficeRoot',('"'+$officeRoot+'"'),'-Suite',$Suite,'-Shard',$Shard,'-OfficeLayout',$OfficeLayout)
$traceWriterRoot='C:\Users\'+$name+'\NexusWriterLab\office'
if ($OfficeLayout -eq 'python-read-root') { $traceWriterRoot='C:\Users\'+$name+'\NexusWriterLab\python\Lib\NexusWriterLabOffice' }
$suiteStarted=[DateTime]::UtcNow
try {
    $waitObserver=$null
    $stackObserver=$null
    if ($env:LAB_TRACE_STACKS -eq '1') {
        $stackArgs=@('-NoProfile','-File',('"'+(Join-Path $source 'lab/trace-stacks.ps1')+'"'),'-Output',('"'+(Join-Path $output 'stacks')+'"'),'-StopFile',('"'+(Join-Path $output 'stop-stacks')+'"'),'-WriterRoot',('"'+$traceWriterRoot+'"'),'-Debugger',('"'+$env:LAB_CDB_EXE+'"'))
        $stackObserver=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -ArgumentList $stackArgs -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $output 'stack-observer-error.txt')
    }
    if ($env:LAB_TRACE_WAITS -eq '1') {
        $waitArgs=@('-NoProfile','-File',('"'+(Join-Path $source 'lab/trace-waits.ps1')+'"'),'-Output',('"'+(Join-Path $output 'waits.jsonl')+'"'),'-StopFile',('"'+(Join-Path $output 'stop-waits')+'"'),'-WriterRoot',('"'+$traceWriterRoot+'"'))
        $waitObserver=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -ArgumentList $waitArgs -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $output 'wait-observer-error.txt')
    }
    $process=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -Credential $credential -LoadUserProfile -WindowStyle Hidden -ArgumentList $arguments -RedirectStandardOutput (Join-Path $output 'stdout.txt') -RedirectStandardError (Join-Path $output 'stderr.txt') -Wait -PassThru
    $labProfile=Get-CimInstance Win32_UserProfile | Where-Object {$_.SID -eq (Get-LocalUser -Name $name).SID.Value} | Select-Object -First 1
    if ($labProfile) {
        $evidence=Join-Path $labProfile.LocalPath 'NexusWriterLab/repo/lab-evidence'
        if (Test-Path -LiteralPath $evidence) { Copy-Item -LiteralPath $evidence -Destination (Join-Path $source 'lab-evidence/standard-user') -Recurse }
    }
    @{suite=$Suite;shard=$Shard;office_layout=$OfficeLayout;exit_code=$process.ExitCode;new_admin_membership=$false;production_changes=@()} | ConvertTo-Json | Set-Content (Join-Path $output 'result.json')
    if ($process.ExitCode -ne 0) { Get-Content (Join-Path $output 'stderr.txt'); throw 'Standard-user validation failed; preserve evidence' }
} finally {
    try { ./lab/collect-crash-events.ps1 -Since $suiteStarted -Output (Join-Path $output 'crash-events.json') }
    catch { @{status='reader_error';error=$_.Exception.Message;memory_dump=$false} | ConvertTo-Json | Set-Content (Join-Path $output 'crash-events.json') }
    if ($stackObserver) {
        $null=New-Item -ItemType File -Path (Join-Path $output 'stop-stacks') -Force
        if (-not $stackObserver.WaitForExit(15000)) { $stackObserver.Kill() }
    }
    if ($waitObserver) {
        $null=New-Item -ItemType File -Path (Join-Path $output 'stop-waits') -Force
        if (-not $waitObserver.WaitForExit(15000)) { $waitObserver.Kill() }
    }
    Remove-LocalUser -Name $name
    $secret=$null; $credential=$null; $secure=$null
}
